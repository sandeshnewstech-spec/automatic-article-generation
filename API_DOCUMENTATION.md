# Article Extraction API Documentation

A high-performance REST API for extracting clean, formatted content from various news websites using Playwright and Trafilatura.

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- Playwright browsers installed (`playwright install chromium`)

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the server:
```bash
uvicorn api:app --reload
```

The API will be available at `http://localhost:8000`.

## 📚 API Endpoints

### 1. Extract Article

Extract content from a news article URL.

- **URL**: `/extract`
- **Method**: `POST`
- **Content-Type**: `application/json`

#### Request Body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | string | Yes | The full URL of the article to extract. |
| `domain_name` | string | No | Optional domain identifier to force a specific configuration. |

#### Example Request

```json
{
  "url": "https://sandesh.com/crime/news/...",
  "domain_name": "sandesh"
}
```

#### Example Response

```json
{
  "success": true,
  "content": "<h1>Article Title</h1>\n<p>Extracted content...</p>",
  "metadata": {
    "url": "https://sandesh.com/crime/news/...",
    "domain_name": "sandesh",
    "extracted_at": "2026-01-21T14:55:00+05:30",
    "content_length": 1542
  }
}
```

### 2. List Domains

List all supported news domains and their configurations.

- **URL**: `/domains`
- **Method**: `GET`
- **Query Parameters**:
  - `include_details` (boolean, default: false): Include detailed configuration for each domain.

#### Example Response

```json
{
  "success": true,
  "count": 4,
  "domains": [
    "sandesh",
    "tv9gujarati",
    "gujaratsamachar",
    "aajtak"
  ]
}
```

### 3. Health Check

Check the API service status.

- **URL**: `/health`
- **Method**: `GET`

#### Example Response

```json
{
  "status": "healthy",
  "timestamp": "2026-01-21T14:55:00+05:30",
  "version": "1.0.0"
}
```

### 4. Cache Statistics

Get cache performance metrics.

- **URL**: `/cache/stats`
- **Method**: `GET`

#### Example Response

```json
{
  "cache_size": 5,
  "ttl_seconds": 300,
  "cached_urls": [
    {
      "url_hash": "a1b2c3d4",
      "expires_in_seconds": 245
    }
  ]
}
```

### 5. Clear Cache

Clear all cached content.

- **URL**: `/cache/clear`
- **Method**: `POST`

#### Example Response

```json
{
  "success": true,
  "message": "Cache cleared. Removed 5 entries."
}
```

## ⚡ Performance

The API has been optimized for speed:

- **First request**: 3-5 seconds (with persistent browser pool)
- **Cached request**: <1 second (5-minute cache TTL)
- **Speedup**: 3-5x faster than initial implementation

### Performance Features

1. **Persistent Browser Pool**: Reuses browser instances across requests
2. **In-Memory Caching**: 5-minute TTL for extracted content
3. **Optimized Timeouts**: Reduced wait times (3-5s) based on site performance
4. **Resource Blocking**: Blocks images, media, fonts, and stylesheets
5. **Fast HTML Parsing**: Uses Python's built-in html.parser

### Testing Performance

Run the performance test script:

```bash
python test_performance.py
```

## 🛠️ Error Handling

The API uses standard HTTP status codes:

- `200`: Success
- `400`: Bad Request (invalid URL format)
- `404`: Not Found (domain config not found or content not extracted)
- `422`: Validation Error (missing fields)
- `500`: Internal Server Error

## 📦 Supported Domains

Currently supported domains include:
- `sandesh` (Sandesh News)
- `tv9gujarati` (TV9 Gujarati)
- `gujaratsamachar` (Gujarat Samachar)
- `aajtak` (Aaj Tak)

New domains can be added by registering a `DomainConfig` in `scraper_config.py`.
