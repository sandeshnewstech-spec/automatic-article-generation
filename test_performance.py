"""
Performance testing script for the Article Extraction API.
Tests response times with and without caching.
"""

import requests
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"

# Test URLs
TEST_URLS = {
    "sandesh": "https://sandesh.com/crime/news/maru-saher-maru-gaam/porbandar/porbandar-news-5-accused-arrested-for-selling-adulterated-diesel-in-ranavav-porbandar-state-monitoring-cell-raids-godown",
    "tv9gujarati": "https://tv9gujarati.com/latest-news/",
    "aajtak": "https://www.aajtak.in/trending/story/canadian-influencer-julia-ann-o1b-visa-extraordinary-talent-story-rttw-dskc-2444955-2026-01-21"
}


def test_extraction_performance(url: str, domain_name: str = None):
    """Test extraction performance for a URL."""
    print(f"\n{'='*60}")
    print(f"Testing: {domain_name or 'auto-detect'}")
    print(f"{'='*60}")
    
    # Clear cache first
    try:
        requests.post(f"{BASE_URL}/cache/clear")
        print("✓ Cache cleared")
    except:
        print("⚠ Could not clear cache")
    
    # First request (no cache)
    print("\n1️⃣  First request (no cache)...")
    start = time.time()
    try:
        response = requests.post(
            f"{BASE_URL}/extract",
            json={"url": url, "domain_name": domain_name},
            timeout=60
        )
        elapsed = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            content_length = data["metadata"]["content_length"]
            print(f"   ✅ Success!")
            print(f"   ⏱️  Time: {elapsed:.2f}s")
            print(f"   📄 Content: {content_length} characters")
        else:
            print(f"   ❌ Failed: {response.status_code}")
            print(f"   ⏱️  Time: {elapsed:.2f}s")
            return
    except Exception as e:
        elapsed = time.time() - start
        print(f"   ❌ Error: {e}")
        print(f"   ⏱️  Time: {elapsed:.2f}s")
        return
    
    # Second request (cached)
    print("\n2️⃣  Second request (should be cached)...")
    start = time.time()
    try:
        response = requests.post(
            f"{BASE_URL}/extract",
            json={"url": url, "domain_name": domain_name},
            timeout=60
        )
        elapsed = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Success!")
            print(f"   ⏱️  Time: {elapsed:.2f}s")
            print(f"   🚀 Speedup: {(elapsed_first / elapsed):.1f}x faster")
            
            # Check cache stats
            cache_response = requests.get(f"{BASE_URL}/cache/stats")
            if cache_response.status_code == 200:
                cache_data = cache_response.json()
                print(f"   💾 Cache size: {cache_data['cache_size']} entries")
        else:
            print(f"   ❌ Failed: {response.status_code}")
            print(f"   ⏱️  Time: {elapsed:.2f}s")
    except Exception as e:
        elapsed = time.time() - start
        print(f"   ❌ Error: {e}")
        print(f"   ⏱️  Time: {elapsed:.2f}s")
    
    elapsed_first = elapsed


def test_health_and_domains():
    """Test basic endpoints."""
    print(f"\n{'='*60}")
    print("Testing Basic Endpoints")
    print(f"{'='*60}\n")
    
    # Health check
    start = time.time()
    response = requests.get(f"{BASE_URL}/health")
    elapsed = time.time() - start
    if response.status_code == 200:
        print(f"✅ Health check: {elapsed*1000:.0f}ms")
    else:
        print(f"❌ Health check failed")
    
    # Domains list
    start = time.time()
    response = requests.get(f"{BASE_URL}/domains")
    elapsed = time.time() - start
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Domains list: {elapsed*1000:.0f}ms ({data['count']} domains)")
    else:
        print(f"❌ Domains list failed")
    
    # Cache stats
    start = time.time()
    response = requests.get(f"{BASE_URL}/cache/stats")
    elapsed = time.time() - start
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Cache stats: {elapsed*1000:.0f}ms ({data['cache_size']} cached)")
    else:
        print(f"❌ Cache stats failed")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 Article Extraction API - Performance Test")
    print("="*60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test basic endpoints
    test_health_and_domains()
    
    # Test extraction performance for Sandesh (fastest)
    test_extraction_performance(TEST_URLS["sandesh"], "sandesh")
    
    print(f"\n{'='*60}")
    print("✅ Performance testing complete!")
    print(f"{'='*60}\n")
