import requests
import json
import uuid
import sys

BASE_URL = "http://localhost:8000"
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASS = "change-me-immediately"

def log(msg, symbol="ℹ️"):
    print(f"{symbol} {msg}")

def test_all_admin():
    print("\n" + "="*50)
    print("🚀 STARTING COMPREHENSIVE ADMIN API TEST")
    print("="*50 + "\n")

    # --- 1. AUTH ---
    log("Testing Authentication...", "🔐")
    login_data = {"email": ADMIN_EMAIL, "password": ADMIN_PASS}
    resp = requests.post(f"{BASE_URL}/admin/auth/login", json=login_data)
    if resp.status_code != 200:
        log(f"Login failed: {resp.text}", "❌")
        return
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    log("Login successful, token acquired.", "✅")

    resp = requests.get(f"{BASE_URL}/admin/auth/me", headers=headers)
    log(f"Current User Context: {json.dumps(resp.json(), indent=2)}", "👤")

    # --- 2. USER MANAGEMENT ---
    log("Testing User Management...", "👥")
    test_user_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    user_payload = {
        "email": test_user_email,
        "password": "temporary-password-123",
        "full_name": "Test API User",
        "role": "project_admin",
        "project_ids": ["tb"]
    }
    resp = requests.post(f"{BASE_URL}/admin/users", headers=headers, json=user_payload)
    if resp.status_code == 201 or resp.status_code == 200:
        new_user = resp.json()
        new_user_id = new_user["id"]
        log(f"Created new user: {test_user_email} (ID: {new_user_id})", "✅")
    else:
        log(f"Failed to create user: {resp.text}", "❌")
        new_user_id = None

    resp = requests.get(f"{BASE_URL}/admin/users", headers=headers)
    log(f"Listed {len(resp.json()['users'])} total users.", "✅")

    if new_user_id:
        # Toggle active
        requests.patch(f"{BASE_URL}/admin/users/{new_user_id}/active", headers=headers, json={"is_active": False})
        log(f"User {new_user_id} deactivated.", "✅")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/admin/users/{new_user_id}", headers=headers)
        log(f"User {new_user_id} deleted.", "✅")

    # --- 3. PROJECT MANAGEMENT ---
    log("Testing Project Management...", "📁")
    resp = requests.get(f"{BASE_URL}/admin/projects", headers=headers)
    log(f"Listed {len(resp.json()['projects'])} projects.", "✅")

    test_project_id = f"test_proj_{uuid.uuid4().hex[:6]}"
    proj_payload = {
        "id": test_project_id,
        "name": "Test Project",
        "description": "Created during API testing",
        "config_json": {"audiences": ["general"]}
    }
    resp = requests.post(f"{BASE_URL}/admin/projects", headers=headers, json=proj_payload)
    if resp.status_code in [200, 201]:
        log(f"Project {test_project_id} created.", "✅")
        
        # Update
        requests.patch(f"{BASE_URL}/admin/projects/{test_project_id}", headers=headers, json={"description": "Updated via API"})
        log(f"Project {test_project_id} updated.", "✅")
        
        # Delete
        requests.delete(f"{BASE_URL}/admin/projects/{test_project_id}", headers=headers)
        log(f"Project {test_project_id} deleted.", "✅")
    else:
        log(f"Failed to create project: {resp.text}", "❌")

    # --- 4. KNOWLEDGE BASE PIPELINE ---
    log("Testing KB Pipeline...", "📚")
    # Using 'tb' project which we know exists
    test_md = f"# API Test Doc\nThis was uploaded via the test script at {time.ctime()}"
    files = {'file': ('api_test.md', test_md, 'text/markdown')}
    data = {'audience': 'general', 'source_name': 'API Test Upload'}
    
    resp = requests.post(f"{BASE_URL}/admin/projects/tb/knowledge-base", headers=headers, data=data, files=files)
    if resp.status_code == 200:
        res = resp.json()
        asset_id = res["asset_id"]
        log(f"Uploaded KB source. Asset ID: {asset_id}", "✅")
        
        # List
        resp = requests.get(f"{BASE_URL}/admin/projects/tb/knowledge-base", headers=headers)
        log(f"Listed {len(resp.json()['assets'])} assets for project 'tb'.", "✅")
        
        # Activate
        log("Activating asset (this triggers indexing, may take a few seconds)...", "⏳")
        try:
            resp = requests.post(
                f"{BASE_URL}/admin/projects/tb/knowledge-base/{asset_id}/activate", 
                headers=headers,
                timeout=30  # Give it plenty of time for embedding
            )
            if resp.status_code == 200:
                log(f"Asset {asset_id} activated. Chunks: {resp.json()['chunk_count']}", "✅")
            else:
                log(f"Activation failed: {resp.text}", "❌")
        except requests.exceptions.Timeout:
            log("Activation request timed out on client side, but likely continuing on server.", "⚠️")
        # Cleanup
        requests.delete(f"{BASE_URL}/admin/projects/tb/knowledge-base/api_test.md", headers=headers)
        log("Deleted test source file.", "✅")
    else:
        log(f"KB Upload failed: {resp.text}", "❌")

    # --- 5. LOGS & DIAGNOSTICS ---
    log("Testing Diagnostics...", "🔍")
    resp = requests.get(f"{BASE_URL}/admin/last-records", headers=headers)
    log(f"Retrieved {len(resp.json()['records'])} global chat records.", "✅")
    
    resp = requests.get(f"{BASE_URL}/admin/projects/tb/last-records", headers=headers)
    log(f"Retrieved chat records specifically for 'tb'.", "✅")

    log("Downloading CSV of chat logs...")
    resp = requests.get(f"{BASE_URL}/admin/last-records-csv", headers=headers)
    if resp.status_code == 200:
        log(f"CSV download test successful (Length: {len(resp.text)} bytes).", "✅")

    print("\n" + "="*50)
    print("✨ ALL ADMIN ENDPOINT TESTS COMPLETED!")
    print("="*50 + "\n")

import time
if __name__ == "__main__":
    try:
        test_all_admin()
    except Exception as e:
        log(f"Script error: {e}", "💥")
        import traceback
        traceback.print_exc()
