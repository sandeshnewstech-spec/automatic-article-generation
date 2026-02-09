"""
Example usage patterns for the multi-domain scraper.

This file demonstrates different ways to use the scraper with various configurations.
"""

from scraper_config import DomainConfig, register_domain, get_config_by_name
from main import extract_article


# ============================================================================
# Example 1: Auto-detection (Simplest)
# ============================================================================
def example_auto_detection():
    """
    The simplest way to use the scraper - just pass a URL.
    The scraper will automatically detect the domain and use the appropriate config.
    """
    print("=" * 60)
    print("Example 1: Auto-detection")
    print("=" * 60)
    
    url = "https://sandesh.com/gujarat/news/maru-saher-maru-gaam/gujarat-latest-news-live--gujarati-news-updates-politics-crime-business-20-jan-2026"
    
    try:
        content = extract_article(url)
        if content:
            print(f"✅ Successfully extracted {len(content)} characters")
            print("\nFirst 200 characters:")
            print(content[:200] + "...")
        else:
            print("❌ No content extracted")
    except ValueError as e:
        print(f"❌ Error: {e}")


# ============================================================================
# Example 2: Using explicit domain name
# ============================================================================
def example_explicit_domain():
    """
    Specify the domain name explicitly.
    Useful when you want to force a specific configuration.
    """
    print("\n" + "=" * 60)
    print("Example 2: Explicit domain name")
    print("=" * 60)
    
    url = "https://sandesh.com/gujarat/news/maru-saher-maru-gaam/gujarat-latest-news-live--gujarati-news-updates-politics-crime-business-20-jan-2026"
    
    try:
        content = extract_article(url, domain_name="sandesh")
        if content:
            print(f"✅ Successfully extracted {len(content)} characters using 'sandesh' config")
        else:
            print("❌ No content extracted")
    except ValueError as e:
        print(f"❌ Error: {e}")


# ============================================================================
# Example 3: Using custom configuration
# ============================================================================
def example_custom_config():
    """
    Create and use a custom configuration object.
    This gives you full control over all scraping parameters.
    """
    print("\n" + "=" * 60)
    print("Example 3: Custom configuration")
    print("=" * 60)
    
    # Create a custom config (example: modified sandesh config)
    custom_config = DomainConfig(
        domain_name="sandesh_custom",
        article_container_selector="div.story[class*='article-']",
        article_id_pattern="article-",
        load_more_selector="//*[contains(@class,'py-4') and contains(@class,'font-normal')]",
        allowed_tags={"h1", "h2", "p"},  # Only extract headings and paragraphs
        noise_keywords=("advertisement", "also read", "આ પણ વાંચો"),
        elements_to_remove=[".inner_ar", ".related-content-alsoread"],
        min_text_length=50,  # Longer minimum text
        wait_timeout=20000,
        click_timeout=5000
    )
    
    url = "https://sandesh.com/gujarat/news/maru-saher-maru-gaam/gujarat-latest-news-live--gujarati-news-updates-politics-crime-business-20-jan-2026"
    
    try:
        content = extract_article(url, config=custom_config)
        if content:
            print(f"✅ Successfully extracted {len(content)} characters using custom config")
            print("   (Only h1, h2, p tags with min 50 chars)")
        else:
            print("❌ No content extracted")
    except ValueError as e:
        print(f"❌ Error: {e}")


# ============================================================================
# Example 4: Registering a new domain
# ============================================================================
def example_register_new_domain():
    """
    Register a new domain configuration for future use.
    This is how you would add support for a new news site.
    """
    print("\n" + "=" * 60)
    print("Example 4: Registering a new domain")
    print("=" * 60)
    
    # Create configuration for a hypothetical new domain
    bbc_config = DomainConfig(
        domain_name="bbc_gujarati",
        article_container_selector="article.main-content",  # Example selector
        article_id_pattern=None,  # No article ID pattern
        load_more_selector=None,  # No load more button
        allowed_tags={"h1", "h2", "h3", "p", "li"},
        noise_keywords=("advertisement", "related stories", "share this"),
        elements_to_remove=[".related-articles", ".social-share"],
        min_text_length=30,
        wait_timeout=10000,
        click_timeout=3000
    )
    
    # Register the configuration
    register_domain(bbc_config, domains=["bbc.com", "www.bbc.com"])
    
    print("✅ Registered 'bbc_gujarati' configuration")
    print("   Domains: bbc.com, www.bbc.com")
    
    # Verify registration
    config = get_config_by_name("bbc_gujarati")
    if config:
        print(f"✅ Configuration verified: {config.domain_name}")
        print(f"   Article selector: {config.article_container_selector}")
    else:
        print("❌ Configuration not found")


# ============================================================================
# Example 5: Error handling
# ============================================================================
def example_error_handling():
    """
    Demonstrate proper error handling for unknown domains.
    """
    print("\n" + "=" * 60)
    print("Example 5: Error handling for unknown domain")
    print("=" * 60)
    
    url = "https://unknown-domain.com/article/123"
    
    try:
        content = extract_article(url)
        if content:
            print(f"✅ Successfully extracted content")
        else:
            print("❌ No content extracted")
    except ValueError as e:
        print(f"✅ Caught expected error: {e}")
        print("   Solution: Register a configuration for this domain first")


# ============================================================================
# Run all examples
# ============================================================================
if __name__ == "__main__":
    print("\n" + "🚀 Multi-Domain Scraper - Usage Examples" + "\n")
    
    example_auto_detection()
    example_explicit_domain()
    example_custom_config()
    example_register_new_domain()
    example_error_handling()
    
    print("\n" + "=" * 60)
    print("✅ All examples completed!")
    print("=" * 60)
