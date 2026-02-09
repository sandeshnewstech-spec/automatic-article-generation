# Multi-Domain Web Scraper

A flexible, configuration-driven web scraper that supports multiple news domains with different layouts.

## Features

- **Configuration-based architecture**: Each domain has its own configuration object
- **Auto-detection**: Automatically detects domain from URL
- **Flexible**: Supports custom configurations for fine-tuned control
- **Extensible**: Easy to add new domains by creating configuration objects
- **Fast**: Uses Playwright with resource blocking for optimal performance

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

## Quick Start

### Basic Usage (Auto-detection)

```python
from main import extract_article

url = "https://sandesh.com/article/..."
content = extract_article(url)
print(content)
```

The scraper automatically detects the domain and uses the appropriate configuration.

### Using Explicit Domain Name

```python
content = extract_article(url, domain_name="sandesh")
```

### Using Custom Configuration

```python
from scraper_config import DomainConfig
from main import extract_article

custom_config = DomainConfig(
    domain_name="my_domain",
    article_container_selector="article.main",
    allowed_tags={"h1", "h2", "p"},
    noise_keywords=("advertisement", "share"),
    min_text_length=30
)

content = extract_article(url, config=custom_config)
```

## Adding a New Domain

To add support for a new domain, create a `DomainConfig` and register it:

```python
from scraper_config import DomainConfig, register_domain

# 1. Create configuration
my_news_config = DomainConfig(
    domain_name="mynews",
    article_container_selector="div.article-body",
    article_id_pattern="post-",  # Optional
    load_more_selector="button.load-more",  # Optional
    allowed_tags={"h1", "h2", "h3", "p", "li"},
    noise_keywords=("advertisement", "related articles"),
    elements_to_remove=[".ads", ".social-share"],
    min_text_length=25,
    wait_timeout=15000,
    click_timeout=3000
)

# 2. Register configuration
register_domain(my_news_config, domains=["mynews.com", "www.mynews.com"])

# 3. Use it
content = extract_article("https://mynews.com/article/123")
```

## Configuration Options

### DomainConfig Parameters

| Parameter | Type | Description | Required |
|-----------|------|-------------|----------|
| `domain_name` | str | Unique identifier for the domain | ✅ |
| `article_container_selector` | str | CSS selector for article container | ✅ |
| `article_id_pattern` | str | Prefix pattern for article ID classes | ❌ |
| `load_more_selector` | str | XPath/CSS selector for load more button | ❌ |
| `allowed_tags` | set[str] | HTML tags to extract text from | ❌ |
| `noise_keywords` | tuple[str] | Keywords indicating unwanted content | ❌ |
| `elements_to_remove` | list[str] | CSS selectors for elements to remove | ❌ |
| `min_text_length` | int | Minimum text length to include | ❌ |
| `wait_timeout` | int | Timeout (ms) for article container | ❌ |
| `click_timeout` | int | Timeout (ms) for click actions | ❌ |
| `page_load_timeout` | int | Timeout (ms) for page load | ❌ |

## Project Structure

```
microservice/
├── main.py                 # Main scraper with extract_article()
├── scraper_config.py       # Configuration system and registry
├── example_usage.py        # Usage examples
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## Examples

Run the example file to see all usage patterns:

```bash
python example_usage.py
```

This demonstrates:
1. Auto-detection
2. Explicit domain name
3. Custom configuration
4. Registering new domains
5. Error handling

## Currently Supported Domains

- **Sandesh** (`sandesh.com`) - Gujarati news portal

## API Reference

### `extract_article(url, config=None, domain_name=None)`

Extract article content from a URL.

**Parameters:**
- `url` (str): The URL to scrape
- `config` (DomainConfig, optional): Custom configuration object
- `domain_name` (str, optional): Domain name to look up configuration

**Returns:**
- `str | None`: Extracted article content as formatted HTML string, or None if extraction fails

**Raises:**
- `ValueError`: If no configuration is found for the URL

**Examples:**

```python
# Auto-detect
content = extract_article("https://sandesh.com/article/...")

# Use domain name
content = extract_article(url, domain_name="sandesh")

# Use custom config
content = extract_article(url, config=my_config)
```

### `register_domain(config, domains=None)`

Register a new domain configuration.

**Parameters:**
- `config` (DomainConfig): The configuration to register
- `domains` (list[str], optional): List of domain names (e.g., ['example.com', 'www.example.com'])

### `get_config_for_url(url)`

Get configuration for a URL.

**Parameters:**
- `url` (str): The URL to get configuration for

**Returns:**
- `DomainConfig | None`: Configuration if found, None otherwise

### `get_config_by_name(name)`

Get configuration by domain name.

**Parameters:**
- `name` (str): The domain name (e.g., 'sandesh')

**Returns:**
- `DomainConfig | None`: Configuration if found, None otherwise

## How It Works

1. **Configuration Lookup**: When you call `extract_article()`, it looks up the appropriate configuration based on the URL or domain name
2. **Playwright Rendering**: Uses Playwright to render the page with resource blocking for speed
3. **HTML Parsing**: Parses the HTML using BeautifulSoup with domain-specific selectors
4. **Content Extraction**: Extracts text from allowed tags while filtering noise
5. **Deduplication**: Removes duplicate content
6. **Formatting**: Returns clean, formatted HTML

## Performance

- **Resource Blocking**: Images, media, and fonts are blocked for faster loading
- **Selective Waiting**: Only waits for article container, not full page load
- **Optimized Parsing**: Uses lxml parser for speed

## License

MIT
