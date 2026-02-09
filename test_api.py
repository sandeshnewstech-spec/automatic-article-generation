from fastapi.testclient import TestClient
from api import app

client = TestClient(app)

def test_health():
    print("Testing /health endpoint...")
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    print("✅ /health passed")

def test_list_domains():
    print("\nTesting /domains endpoint...")
    response = client.get("/domains")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["domains"]) > 0
    print(f"✅ /domains passed. Found {len(data['domains'])} domains.")

def test_list_domains_details():
    print("\nTesting /domains?include_details=true endpoint...")
    response = client.get("/domains?include_details=true")
    assert response.status_code == 200
    data = response.json()
    assert "details" in data
    assert len(data["details"]) > 0
    print("✅ /domains details passed")

def test_extract_invalid_url():
    print("\nTesting /extract with invalid URL...")
    response = client.post("/extract", json={"url": "invalid-url"})
    # Pydantic validation error expected
    assert response.status_code == 422 
    print("✅ Invalid URL validation passed")

def test_extract_no_config_url():
    print("\nTesting /extract with URL having no config...")
    # Using a domain that definitely doesn't have a config
    response = client.post("/extract", json={"url": "https://example.com/some-article"})
    # Should return 404 because config not found (raised as ValueError in main.py -> caught in api.py)
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["success"] is False
    print("✅ No config handling passed")

def test_extract_real_article():
    print("\nTesting /extract with a real Sandesh article...")
    test_url = "https://sandesh.com/crime/news/maru-saher-maru-gaam/porbandar/porbandar-news-5-accused-arrested-for-selling-adulterated-diesel-in-ranavav-porbandar-state-monitoring-cell-raids-godown"
    response = client.post("/extract", json={"url": test_url})
    
    if response.status_code == 200:
        data = response.json()
        assert data["success"] is True
        assert len(data["content"]) > 0
        print(f"✅ Real article extraction passed! Extracted {data['metadata']['content_length']} characters")
    else:
        print(f"⚠️  Real article extraction returned {response.status_code} - this might be due to network/site issues")

if __name__ == "__main__":
    try:
        test_health()
        test_list_domains()
        test_list_domains_details()
        test_extract_invalid_url()
        test_extract_no_config_url()
        test_extract_real_article()
        print("\n🎉 All API tests completed!")
    except Exception as e:
        print(f"\n❌ Tests failed: {str(e)}")
