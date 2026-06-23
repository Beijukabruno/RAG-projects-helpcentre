import requests
from utils import BASE_URL, log, save_result

def test_health():
    log("Testing Health Endpoints...")
    results = {}
    
    # /health
    resp = requests.get(f"{BASE_URL}/health")
    results["health"] = resp.json()
    log(f"Health: {results['health']}", "✅")
    
    # /ready
    resp = requests.get(f"{BASE_URL}/ready")
    results["ready"] = resp.json()
    log(f"Ready: {results['ready']}", "✅")
    
    save_result("health_test", results)

if __name__ == "__main__":
    test_health()
