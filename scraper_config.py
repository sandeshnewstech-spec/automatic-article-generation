"""
Domain-specific configuration for web scraping.

This module provides a flexible configuration system for scraping different news domains.
Each domain can have its own selectors, filters, and processing rules.
"""

from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse


@dataclass
class DomainConfig:
    """Configuration for scraping a specific domain."""
    
    domain_name: str
    """Unique identifier for this domain (e.g., 'sandesh', 'bbc')"""
    
    article_container_selector: str
    """CSS selector for the main article container"""
    
    article_id_pattern: Optional[str] = None
    """Prefix pattern for article ID classes (e.g., 'article-')"""
    
    load_more_selector: Optional[str] = None
    """XPath or CSS selector for 'load more' button"""
    
    allowed_tags: set[str] = field(default_factory=lambda: {"h1", "h2", "h3", "h4", "h5", "h6", "p", "b", "strong", "li"})
    """HTML tags to extract text from"""
    
    noise_keywords: tuple[str, ...] = field(default_factory=tuple)
    """Keywords that indicate noise/unwanted content"""
    
    elements_to_remove: list[str] = field(default_factory=list)
    """CSS selectors for elements to remove before processing"""
    
    min_text_length: int = 25
    """Minimum text length to include in output"""
    
    wait_timeout: int = 15000
    """Timeout (ms) for waiting for article container"""
    
    click_timeout: int = 3000
    """Timeout (ms) for click actions"""
    
    page_load_timeout: int = 60000
    """Timeout (ms) for page load"""
    
    wait_until: str = "domcontentloaded"
    """Page load strategy: 'domcontentloaded', 'networkidle', 'load', or 'commit'"""


class DomainRegistry:
    """Registry for managing domain configurations."""
    
    def __init__(self):
        self._configs: dict[str, DomainConfig] = {}
        self._domain_map: dict[str, str] = {}  # Maps actual domain to config name
    
    def register(self, config: DomainConfig, domains: list[str] | None = None):
        """
        Register a domain configuration.
        
        Args:
            config: The domain configuration to register
            domains: List of actual domain names (e.g., ['sandesh.com', 'www.sandesh.com'])
                    If None, uses config.domain_name as the domain
        """
        self._configs[config.domain_name] = config
        
        if domains:
            for domain in domains:
                self._domain_map[domain.lower()] = config.domain_name
        else:
            self._domain_map[config.domain_name.lower()] = config.domain_name
    
    def get_config(self, url: str) -> Optional[DomainConfig]:
        """
        Get configuration for a URL.
        
        Args:
            url: The URL to get configuration for
            
        Returns:
            DomainConfig if found, None otherwise
        """
        domain = self._extract_domain(url)
        config_name = self._domain_map.get(domain.lower())
        
        if config_name:
            return self._configs.get(config_name)
        
        return None
    
    def get_config_by_name(self, name: str) -> Optional[DomainConfig]:
        """
        Get configuration by domain name.
        
        Args:
            name: The domain name (e.g., 'sandesh')
            
        Returns:
            DomainConfig if found, None otherwise
        """
        return self._configs.get(name)
    
    def list_domains(self) -> list[str]:
        """List all registered domain names."""
        return list(self._configs.keys())
    
    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract domain from URL."""
        parsed = urlparse(url)
        return parsed.netloc


# ============================================================================
# Pre-configured Domains
# ============================================================================

SANDESH_CONFIG = DomainConfig(
    domain_name="sandesh",
    article_container_selector="div.story[class*='article-']",
    article_id_pattern="article-",
    load_more_selector="//*[contains(@class,'py-4') and contains(@class,'font-normal')]",
    allowed_tags={"h1", "h2", "h3", "h4", "h5", "h6", "p", "b", "strong", "li"},
    noise_keywords=(
        "advertisement", "also read", "related articles",
        "share", "follow us", "post a comment",
        "descriptions off", "subtitles", "alternate audio",
        "this is a modal window", "beginning of dialog window",
        "end of dialog window", "આ પણ વાંચો"
    ),
    elements_to_remove=[
        ".inner_ar",
        ".related-content-alsoread"
    ],
    min_text_length=25,
    wait_timeout=3000,  # Fast site with domcontentloaded
    click_timeout=2000,
    page_load_timeout=15000  # Reduced from 60s
)

TV9_GUJARATI_CONFIG = DomainConfig(
    domain_name="tv9gujarati",
    article_container_selector="div.detailBody",  # Parent container for all article elements
    article_id_pattern=None,  # No article ID pattern for TV9
    load_more_selector=None,  # No load more button
    allowed_tags={"h1", "h2", "h3", "h4", "h5", "h6", "p", "b", "strong", "li", "div"},
    noise_keywords=(
        "advertisement", "also read", "related articles",
        "share", "follow us", "post a comment",
        "આ પણ વાંચો", "વધુ વાંચો"
    ),
    elements_to_remove=[
        ".trc_rbox_container",  # Related content widget
        ".ad-container",
        ".social-share"
    ],
    min_text_length=25,
    wait_timeout=5000,  # Optimized for dynamic content
    click_timeout=2000,
    page_load_timeout=15000,  # Reduced from 60s
    wait_until="domcontentloaded"
)

GUJARAT_SAMACHAR_CONFIG = DomainConfig(
    domain_name="gujaratsamachar",
    article_container_selector=".detail-news.article-detail-news",  # Main article container
    article_id_pattern=None,  # No article ID pattern
    load_more_selector=None,  # No load more button
    allowed_tags={"h1", "h2", "h3", "h4", "h5", "h6", "p", "b", "strong", "li", "div"},
    noise_keywords=(
        "advertisement", "also read", "related articles",
        "share", "follow us", "post a comment",
        "આ પણ વાંચો", "વધુ વાંચો"
    ),
    elements_to_remove=[
        ".multiple.card",  # Related news cards/sidebar
        ".ad-container",
        ".social-share"
    ],
    min_text_length=25,
    wait_timeout=5000,  # Optimized for dynamic content
    click_timeout=2000,
    page_load_timeout=15000,  # Reduced from 60s
    wait_until="domcontentloaded"
)

AAJTAK_CONFIG = DomainConfig(
    domain_name="aajtak",
    article_container_selector=".content-area",  # Main article container
    article_id_pattern=None,  # No article ID pattern
    load_more_selector=".readmoreAction",  # "और पढ़ें" (Read More) button
    allowed_tags={"h1", "h2", "h3", "h4", "h5", "h6", "p", "b", "strong", "li", "div"},
    noise_keywords=(
        "advertisement", "also read", "related articles",
        "share", "follow us", "post a comment",
        "આ પણ વાંચો", "વધુ વાંચો"
    ),
    elements_to_remove=[
        ".ad-container",
        ".social-share",
        ".tbl-feed-card"  # Recommended articles cards
    ],
    min_text_length=25,
    wait_timeout=5000,  # Optimized for dynamic content
    click_timeout=2000,
    page_load_timeout=15000,  # Reduced from 60s
    wait_until="domcontentloaded"
)


# ============================================================================
# Global Registry
# ============================================================================

# Create global registry and register default domains
registry = DomainRegistry()
registry.register(SANDESH_CONFIG, domains=["sandesh.com", "www.sandesh.com"])
registry.register(TV9_GUJARATI_CONFIG, domains=["tv9gujarati.com", "www.tv9gujarati.com"])
registry.register(GUJARAT_SAMACHAR_CONFIG, domains=["gujaratsamachar.com", "www.gujaratsamachar.com"])
registry.register(AAJTAK_CONFIG, domains=["aajtak.in", "www.aajtak.in"])


# ============================================================================
# Convenience Functions
# ============================================================================

def get_config_for_url(url: str) -> Optional[DomainConfig]:
    """Get configuration for a URL using the global registry."""
    return registry.get_config(url)


def get_config_by_name(name: str) -> Optional[DomainConfig]:
    """Get configuration by domain name using the global registry."""
    return registry.get_config_by_name(name)


def register_domain(config: DomainConfig, domains: list[str] | None = None):
    """Register a new domain configuration in the global registry."""
    registry.register(config, domains)
