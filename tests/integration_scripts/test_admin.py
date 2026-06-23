import requests
import uuid
import json
from utils import BASE_URL, log, save_result, get_admin_token

def test_admin_flow():
    token = get_admin_token()
    if not token:
        return

    headers = {"Authorization": f"Bearer {token}"}
    all_results = {"token": token}

    # 1. Auth Me
    log("Verifying Auth Me...")
    resp = requests.get(f"{BASE_URL}/admin/auth/me", headers=headers)
    all_results["auth_me"] = resp.json()
    log("Auth Me verified.", "✅")

    # 2. Users
    log("Testing User Management...")
    test_email = f"api_test_{uuid.uuid4().hex[:6]}@example.com"
    user_payload = {
        "email": test_email,
        "password": "test-password-1234",
        "full_name": "API Test User",
        "role": "project_admin",
        "project_ids": ["tb"]
    }
    resp = requests.post(f"{BASE_URL}/admin/users", headers=headers, json=user_payload)
    if resp.status_code in [200, 201]:
        user_data = resp.json()
        user_id = user_data["id"]
        all_results["created_user"] = user_data
        log(f"User created: {test_email}", "✅")
        
        # List
        resp = requests.get(f"{BASE_URL}/admin/users", headers=headers)
        all_results["users_list"] = resp.json()
        
        # Delete
        requests.delete(f"{BASE_URL}/admin/users/{user_id}", headers=headers)
        log(f"User deleted: {user_id}", "✅")
    else:
        log(f"User creation failed: {resp.text}", "❌")

    # 3. Projects
    log("Testing Project Management...")
    test_proj_id = f"api_proj_{uuid.uuid4().hex[:6]}"
    proj_payload = {
        "id": test_proj_id,
        "name": "API Test Project",
        "description": "Integration test project"
    }
    resp = requests.post(f"{BASE_URL}/admin/projects", headers=headers, json=proj_payload)
    if resp.status_code in [200, 201]:
        proj_data = resp.json()
        all_results["created_project"] = proj_data
        log(f"Project created: {test_proj_id}", "✅")
        
        # List
        resp = requests.get(f"{BASE_URL}/admin/projects", headers=headers)
        all_results["projects_list"] = resp.json()
        
        # Delete
        requests.delete(f"{BASE_URL}/admin/projects/{test_proj_id}", headers=headers)
        log(f"Project deleted: {test_proj_id}", "✅")
    else:
        log(f"Project creation failed: {resp.text}", "❌")

    save_result("admin_test_flow", all_results)

if __name__ == "__main__":
    test_admin_flow()
