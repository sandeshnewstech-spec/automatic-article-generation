"""
REST API for Article Extraction Service

This FastAPI application provides endpoints for extracting article content
from various news websites using domain-specific configurations.
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, HttpUrl, validator
from typing import Optional, List
import logging
from datetime import datetime, timedelta
import asyncio
from concurrent.futures import ThreadPoolExecutor
import hashlib

from main import extract_article
from scraper_config import get_config_by_name, registry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Thread pool for running sync Playwright in async context
thread_pool = ThreadPoolExecutor(max_workers=4)

# Simple in-memory cache with TTL
_cache = {}
_cache_ttl = 300  # 5 minutes


def get_cache_key(url: str, domain_name: Optional[str]) -> str:
    """Generate cache key from URL and domain name."""
    key = f"{url}:{domain_name or 'auto'}"
    return hashlib.md5(key.encode()).hexdigest()


def get_cached_content(url: str, domain_name: Optional[str]) -> Optional[dict]:
    """Get cached content if available and not expired."""
    cache_key = get_cache_key(url, domain_name)
    if cache_key in _cache:
        cached_data = _cache[cache_key]
        if datetime.now() < cached_data["expires_at"]:
            logger.info(f"Cache HIT for {url}")
            return cached_data["data"]
        else:
            # Expired, remove from cache
            del _cache[cache_key]
            logger.info(f"Cache EXPIRED for {url}")
    return None


def set_cached_content(url: str, domain_name: Optional[str], data: dict):
    """Cache content with TTL."""
    cache_key = get_cache_key(url, domain_name)
    _cache[cache_key] = {
        "data": data,
        "expires_at": datetime.now() + timedelta(seconds=_cache_ttl)
    }
    logger.info(f"Cached content for {url} (TTL: {_cache_ttl}s)")

# Initialize FastAPI app
app = FastAPI(
    title="Article Extraction API",
    description="Extract clean article content from news websites",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this based on your needs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Request/Response Models
# ============================================================================

class ExtractionRequest(BaseModel):
    """Request model for article extraction."""
    
    url: str = Field(
        ...,
        description="URL of the article to extract",
        example="https://sandesh.com/crime/news/..."
    )
    domain_name: Optional[str] = Field(
        None,
        description="Optional domain name to use specific configuration (e.g., 'sandesh', 'tv9gujarati')",
        example="sandesh"
    )
    
    @validator('url')
    def validate_url(cls, v):
        """Validate URL format."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "url": "https://sandesh.com/crime/news/maru-saher-maru-gaam/porbandar/porbandar-news-5-accused-arrested-for-selling-adulterated-diesel-in-ranavav-porbandar-state-monitoring-cell-raids-godown",
                "domain_name": "sandesh"
            }
        }


class ExtractionResponse(BaseModel):
    """Response model for successful article extraction."""
    
    success: bool = Field(True, description="Indicates successful extraction")
    content: str = Field(..., description="Extracted article content in HTML format")
    metadata: dict = Field(
        ...,
        description="Additional metadata about the extraction"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "content": "<h1>Article Title</h1>\n\n<p>Article content...</p>",
                "metadata": {
                    "url": "https://example.com/article",
                    "domain_name": "sandesh",
                    "extracted_at": "2026-01-21T14:51:38+05:30",
                    "content_length": 1234
                }
            }
        }


class ErrorResponse(BaseModel):
    """Response model for errors."""
    
    success: bool = Field(False, description="Indicates failed extraction")
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Additional error details")
    
    class Config:
        schema_extra = {
            "example": {
                "success": False,
                "error": "No configuration found for URL",
                "detail": "The domain is not registered in the system"
            }
        }


class DomainInfo(BaseModel):
    """Information about a registered domain."""
    
    domain_name: str = Field(..., description="Domain identifier")
    article_container_selector: str = Field(..., description="CSS selector for article container")
    has_load_more: bool = Field(..., description="Whether domain has load more functionality")
    wait_strategy: str = Field(..., description="Page load wait strategy")


class DomainsResponse(BaseModel):
    """Response model for domain listing."""
    
    success: bool = Field(True, description="Indicates successful request")
    count: int = Field(..., description="Number of registered domains")
    domains: List[str] = Field(..., description="List of registered domain names")
    details: Optional[List[DomainInfo]] = Field(None, description="Detailed domain configurations")


class HealthResponse(BaseModel):
    """Response model for health check."""
    
    status: str = Field(..., description="Service health status")
    timestamp: str = Field(..., description="Current server timestamp")
    version: str = Field(..., description="API version")


# ============================================================================
# API Endpoints
# ============================================================================

@app.get(
    "/",
    response_model=dict,
    summary="API Root",
    description="Welcome endpoint with API information"
)
async def root():
    """Root endpoint providing API information."""
    return {
        "message": "Article Extraction API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "extract": "POST /extract",
            "domains": "GET /domains",
            "health": "GET /health"
        }
    }


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Check if the API service is running"
)
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }


@app.get(
    "/domains",
    response_model=DomainsResponse,
    summary="List Domains",
    description="Get list of all registered domain configurations"
)
async def list_domains(include_details: bool = False):
    """
    List all registered domain configurations.
    
    Args:
        include_details: If True, includes detailed configuration for each domain
    
    Returns:
        List of registered domain names and optionally their configurations
    """
    try:
        domain_names = registry.list_domains()
        
        response = {
            "success": True,
            "count": len(domain_names),
            "domains": domain_names
        }
        
        if include_details:
            details = []
            for name in domain_names:
                config = get_config_by_name(name)
                if config:
                    details.append({
                        "domain_name": config.domain_name,
                        "article_container_selector": config.article_container_selector,
                        "has_load_more": config.load_more_selector is not None,
                        "wait_strategy": config.wait_until
                    })
            response["details"] = details
        
        return response
    
    except Exception as e:
        logger.error(f"Error listing domains: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list domains: {str(e)}"
        )


@app.get(
    "/cache/stats",
    response_model=dict,
    summary="Cache Statistics",
    description="Get cache statistics and performance metrics"
)
async def cache_stats():
    """Get cache statistics."""
    return {
        "cache_size": len(_cache),
        "ttl_seconds": _cache_ttl,
        "cached_urls": [
            {
                "url_hash": key[:8],
                "expires_in_seconds": max(0, int((data["expires_at"] - datetime.now()).total_seconds()))
            }
            for key, data in _cache.items()
        ]
    }


@app.post(
    "/cache/clear",
    response_model=dict,
    summary="Clear Cache",
    description="Clear all cached content"
)
async def clear_cache():
    """Clear all cached content."""
    global _cache
    count = len(_cache)
    _cache.clear()
    logger.info(f"Cache cleared. Removed {count} entries.")
    return {
        "success": True,
        "message": f"Cache cleared. Removed {count} entries."
    }


@app.post(
    "/extract",
    response_model=ExtractionResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        404: {"model": ErrorResponse, "description": "Domain not found"},
        500: {"model": ErrorResponse, "description": "Extraction failed"}
    },
    summary="Extract Article",
    description="Extract clean article content from a given URL"
)
async def extract_article_endpoint(request: ExtractionRequest):
    """
    Extract article content from a URL.
    
    Args:
        request: ExtractionRequest containing URL and optional domain name
    
    Returns:
        ExtractionResponse with extracted content and metadata
    
    Raises:
        HTTPException: If extraction fails or domain is not found
    """
    logger.info(f"Extraction request received for URL: {request.url}")
    
    # Check cache first
    cached = get_cached_content(request.url, request.domain_name)
    if cached:
        return cached
    
    try:
        # Extract article content using thread pool executor
        # This allows sync Playwright to run without blocking the async event loop
        loop = asyncio.get_event_loop()
        content = await loop.run_in_executor(
            thread_pool,
            extract_article,
            request.url,
            None,  # config
            request.domain_name
        )
        
        # Check if content was extracted
        if content is None or content.strip() == "":
            logger.warning(f"No content extracted from URL: {request.url}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "success": False,
                    "error": "No content extracted",
                    "detail": "The article container was not found or contained no valid content"
                }
            )
        
        # Prepare metadata
        metadata = {
            "url": request.url,
            "domain_name": request.domain_name or "auto-detected",
            "extracted_at": datetime.now().isoformat(),
            "content_length": len(content),
            "cached": False
        }
        
        logger.info(f"Successfully extracted {len(content)} characters from {request.url}")
        
        response_data = {
            "success": True,
            "content": content,
            "metadata": metadata
        }
        
        # Cache the successful response
        set_cached_content(request.url, request.domain_name, response_data)
        
        return response_data
    
    except ValueError as e:
        # Configuration not found
        logger.error(f"Configuration error for URL {request.url}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "error": "Domain configuration not found",
                "detail": str(e)
            }
        )
    
    except Exception as e:
        # Other extraction errors
        logger.error(f"Extraction failed for URL {request.url}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "success": False,
                "error": "Extraction failed",
                "detail": str(e)
            }
        )


# ============================================================================
# Application Startup/Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Log startup information."""
    logger.info("Article Extraction API starting up...")
    logger.info(f"Registered domains: {', '.join(registry.list_domains())}")


@app.on_event("shutdown")
async def shutdown_event():
    """Log shutdown information."""
    logger.info("Article Extraction API shutting down...")


if __name__ == "__main__":
    import uvicorn
    
    # Run the API server
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
