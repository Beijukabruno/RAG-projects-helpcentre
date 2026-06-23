import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("BASE_URL", "http://localhost:8001")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")
ADMIN_PASS = os.getenv("ADMIN_PASS", "change-me-immediately")

RESULTS_DIR = "tests/integration_scripts/results"

def ensure_results_dir():
    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR, exist_ok=True)

def save_result(filename, data):
    ensure_results_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(RESULTS_DIR, f"{filename}_{timestamp}.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"✅ Result saved to {path}")
    return path

def log(msg, symbol="ℹ️"):
    print(f"{symbol} {msg}")

class AdminSession:
    def __init__(self):
        self.token = self._get_token()
        self.headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def _get_token(self):
        payload = {"email": ADMIN_EMAIL, "password": ADMIN_PASS}
        try:
            resp = requests.post(f"{BASE_URL}/admin/auth/login", json=payload)
            if resp.status_code == 200:
                return resp.json()["access_token"]
            else:
                log(f"Failed to get admin token: {resp.text}", "❌")
                return None
        except Exception as e:
            log(f"Connection error while getting token: {e}", "❌")
            return None

    def get(self, endpoint, **kwargs):
        headers = {**self.headers, **kwargs.pop("headers", {})}
        return requests.get(f"{BASE_URL}{endpoint}", headers=headers, **kwargs)

    def post(self, endpoint, **kwargs):
        headers = {**self.headers, **kwargs.pop("headers", {})}
        return requests.post(f"{BASE_URL}{endpoint}", headers=headers, **kwargs)

    def patch(self, endpoint, **kwargs):
        headers = {**self.headers, **kwargs.pop("headers", {})}
        return requests.patch(f"{BASE_URL}{endpoint}", headers=headers, **kwargs)

    def delete(self, endpoint, **kwargs):
        headers = {**self.headers, **kwargs.pop("headers", {})}
        return requests.delete(f"{BASE_URL}{endpoint}", headers=headers, **kwargs)
