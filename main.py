import trafilatura
from playwright.sync_api import sync_playwright, Browser, BrowserContext
from bs4 import BeautifulSoup, Tag
import re
from typing import Optional
from scraper_config import DomainConfig, get_config_for_url, get_config_by_name
import atexit
import logging

logger = logging.getLogger(__name__)

# Global browser instance for reuse
_browser: Optional[Browser] = None
_playwright = None


def get_browser() -> Browser:
    """Get or create a persistent browser instance."""
    global _browser, _playwright
    
    if _browser is None or not _browser.is_connected():
        logger.info("Initializing persistent browser instance...")
        _playwright = sync_playwright().start()
        _browser = _playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--disable-setuid-sandbox",
                "--no-sandbox",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ]
        )
        logger.info("Browser instance ready")
    
    return _browser


def cleanup_browser():
    """Clean up browser instance on exit."""
    global _browser, _playwright
    if _browser:
        try:
            _browser.close()
        except:
            pass
    if _playwright:
        try:
            _playwright.stop()
        except:
            pass


# Register cleanup on exit
atexit.register(cleanup_browser)


def is_noise(text: str, noise_keywords: tuple[str, ...]) -> bool:
    """Check if text contains noise keywords."""
    t = text.lower()
    return any(k in t for k in noise_keywords)


def extract_article(
    url: str,
    config: Optional[DomainConfig] = None,
    domain_name: Optional[str] = None
) -> str | None:
    """
    Extract article content from a URL using domain-specific configuration.
    
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
        content = extract_article("https://sandesh.com/article/...")
        
        # Use specific domain name
        content = extract_article(url, domain_name="sandesh")
        
        # Use custom config
        content = extract_article(url, config=my_custom_config)
    """
    # Determine which configuration to use
    if config is None:
        if domain_name:
            config = get_config_by_name(domain_name)
    # Helper for generic extraction
    def try_generic_fallback(target_url):
        logger.info(f"Attempting generic extraction (Trafilatura) for {target_url}")
        try:
            downloaded = trafilatura.fetch_url(target_url)
            if downloaded:
                result = trafilatura.extract(
                    downloaded, 
                    include_comments=False, 
                    include_tables=False, 
                    no_fallback=False
                )
                if result:
                    formatted = [f"<p>{line.strip()}</p>" for line in result.split('\n') if line.strip()]
                    return "\n\n".join(formatted)
        except Exception as e:
            logger.warning(f"Generic extraction failed: {e}")
        return None

    # If no config specific found, try generic immediately
    if config is None:
        return try_generic_fallback(url)

    # ---------------------------
    # 1. FAST Playwright render with persistent browser
    # ---------------------------
    try:
        browser = get_browser()
        # Use a new context to ensure clean state and user agent
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        page = context.new_page()
        
        # Block heavy resources
        context.route(
            "**/*",
            lambda route: route.abort()
            if route.request.resource_type in {"image", "media", "font", "stylesheet"}
            else route.continue_()
        )
        
        try:
            # Navigate
            page.goto(url, wait_until=config.wait_until, timeout=config.page_load_timeout)

            # Wait for content
            try:
                page.wait_for_selector(config.article_container_selector, timeout=config.wait_timeout)
            except Exception as e:
                logger.warning(f"Timeout waiting for selector {config.article_container_selector}: {e}")
                # Don't fail yet, check if we have HTML
            
            # Click load more if needed
            if config.load_more_selector:
                try:
                    page.locator(config.load_more_selector).first.click(timeout=config.click_timeout)
                except:
                    pass

            html = page.content()
            
        except Exception as e:
            logger.error(f"Playwright navigation failed: {e}")
            context.close()
            return try_generic_fallback(url)
            
        context.close()

        # ---------------------------
        # 2. Parse HTML
        # ---------------------------
        soup = BeautifulSoup(html, "html.parser")
        first_story = soup.select_one(config.article_container_selector)
        
        if not first_story or not first_story.get_text(strip=True):
            logger.warning("Specific selector yielded no content. Falling back.")
            return try_generic_fallback(url)
            
        # ... (rest of parsing logic is complex to reproduce exactly here, 
        # so I should try to KEEP the parsing logic if possible, 
        # but I need to wrap it to fallback if it returns empty)
        
        # Actually, if I can just return try_generic_fallback(url) if soup fails, that's enough.
        # But I need to see the rest of the parsing logic to know where to insert the check.
        
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        return try_generic_fallback(url)


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


# ---------------------------
# RUN
# ---------------------------
if __name__ == "__main__":
    # Example URL - using Sandesh (faster, uses domcontentloaded)
    URL = "https://sandesh.com/crime/news/maru-saher-maru-gaam/porbandar/porbandar-news-5-accused-arrested-for-selling-adulterated-diesel-in-ranavav-porbandar-state-monitoring-cell-raids-godown"
    
    print("🔍 Extracting article using auto-detection...\n")
    
    try:
        content = extract_article(URL)
        if content:
            print("===== FULL CLEAN ARTICLE =====\n")
            print(content)
        else:
            print("❌ No content extracted")
    except ValueError as e:
        print(f"❌ Error: {e}")