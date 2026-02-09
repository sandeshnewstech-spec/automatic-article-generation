from playwright.async_api import async_playwright
from bs4 import BeautifulSoup, Tag
import re
from typing import Optional
from scraper_config import DomainConfig, get_config_for_url, get_config_by_name


def is_noise(text: str, noise_keywords: tuple[str, ...]) -> bool:
    """Check if text contains noise keywords."""
    t = text.lower()
    return any(k in t for k in noise_keywords)


async def extract_article_async(
    url: str,
    config: Optional[DomainConfig] = None,
    domain_name: Optional[str] = None
) -> str | None:
    """
    Extract article content from a URL using domain-specific configuration (async version).
    
    Args:
        url: The URL to scrape
        config: Optional DomainConfig object. If provided, uses this configuration.
        domain_name: Optional domain name to look up configuration. 
                    If provided, looks up config by name.
        
    Returns:
        Extracted article content as formatted HTML string, or None if extraction fails.
        
    Raises:
        ValueError: If no configuration is found for the URL.
        
    Examples:
        # Auto-detect domain from URL
        content = await extract_article_async("https://sandesh.com/article/...")
        
        # Use specific domain name
        content = await extract_article_async(url, domain_name="sandesh")
        
        # Use custom config
        content = await extract_article_async(url, config=my_custom_config)
    """
    # Determine which configuration to use
    if config is None:
        if domain_name:
            config = get_config_by_name(domain_name)
            if not config:
                raise ValueError(f"No configuration found for domain: {domain_name}")
        else:
            config = get_config_for_url(url)
            if not config:
                raise ValueError(f"No configuration found for URL: {url}")
    
    # ---------------------------
    # 1. FAST Playwright render
    # ---------------------------
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-gpu", "--disable-dev-shm-usage"]
        )
        context = await browser.new_context()
        # 🚀 Block heavy resources
        await context.route(
            "**/*",
            lambda route: route.abort()
            if route.request.resource_type in {"image", "media", "font"}
            else route.continue_()
        )
        page = await context.new_page()
        await page.goto(url, wait_until=config.wait_until, timeout=config.page_load_timeout)

        # Wait ONLY for article container
        await page.wait_for_selector(config.article_container_selector, timeout=config.wait_timeout)

        # Click load-more only if present and configured
        if config.load_more_selector:
            try:
                await page.locator(config.load_more_selector).first.click(timeout=config.click_timeout)
            except:
                pass

        html = await page.content()
        await browser.close()

    # ---------------------------
    # 2. Parse HTML
    # ---------------------------
    soup = BeautifulSoup(html, "lxml")
    first_story = soup.select_one(config.article_container_selector)

    if not first_story:
        return None

    # Extract article ID if pattern is configured
    article_id = None
    if config.article_id_pattern:
        article_id = next(
            (cls for cls in first_story.get("class", []) if cls.startswith(config.article_id_pattern)),
            None
        )

    # Collect all article blocks
    if article_id:
        story_blocks = soup.select(f"div.story.{article_id}")
    else:
        story_blocks = [first_story]

    # 🔥 REMOVE unwanted elements BEFORE processing
    for selector in config.elements_to_remove:
        for elem in soup.select(selector):
            elem.decompose()
    
    # Remove any element containing noise keywords from the text
    # Only remove specific small elements, not entire article containers
    if config.noise_keywords:
        pattern = "|".join(re.escape(kw) for kw in config.noise_keywords)
        for elem in soup.find_all(string=re.compile(pattern, re.IGNORECASE)):
            # Get the parent element, handling NavigableString objects
            try:
                parent = elem.parent
                if parent and isinstance(parent, Tag):
                    # Only remove if it's a small container element (div, span, aside, etc.)
                    # Don't remove main structural elements
                    if parent.name in {"div", "span", "aside", "footer", "nav"} and len(parent.get_text(strip=True)) < 200:
                        parent.decompose()
            except (AttributeError, TypeError):
                # Skip if we can't get the parent
                continue

    output = []
    seen = set()

    for block in story_blocks:
        for tag in block.find_all(config.allowed_tags, recursive=True):
            if not isinstance(tag, Tag):
                continue

            text = tag.get_text(strip=True)

            # Filters
            if len(text) < config.min_text_length:
                continue
            if is_noise(text, config.noise_keywords):
                continue

            # Skip if it's a heading/link from related articles section
            if tag.name in {"h3", "h4"} and tag.find_parent(class_=re.compile(r"related|also")):
                continue

            # Remove duplicates
            if text in seen:
                continue
            seen.add(text)

            output.append(f"<{tag.name}>{text}</{tag.name}>")

    return "\n\n".join(output)
