import uuid
from utils import AdminSession, log, save_result

def test_users_comprehensive():
    session = AdminSession()
    if not session.token:
        return

    results = {}
    log("Starting Comprehensive User Management Test", "👥")

    # 1. List Users
    log("Listing users...")
    resp = session.get("/admin/users")
    results["list_users"] = resp.json()
    log(f"Found {len(resp.json().get('users', []))} users.", "✅")

    # 2. Create User
    test_email = f"user_{uuid.uuid4().hex[:6]}@example.com"
    user_payload = {
        "email": test_email,
        "password": "secure-password-123",
        "full_name": "Integration Test User",
        "role": "project_admin",
        "project_ids": ["tb"]
    }
    log(f"Creating user {test_email}...")
    resp = session.post("/admin/users", json=user_payload)
    if resp.status_code not in [200, 201]:
        log(f"Failed to create user: {resp.text}", "❌")
        return
    
    user_data = resp.json()
    user_id = user_data["id"]
    results["create_user"] = user_data
    log(f"User created with ID: {user_id}", "✅")

    # 3. Set User Active (Toggle)
    log(f"Deactivating user {user_id}...")
    resp = session.patch(f"/admin/users/{user_id}/active", json={"is_active": False})
    results["deactivate_user"] = resp.json()
    log("User deactivated.", "✅")

    # 4. Add User Role
    log(f"Adding super_admin role to user {user_id}...")
    resp = session.post(f"/admin/users/{user_id}/roles", json={"role": "super_admin"})
    results["add_role"] = resp.json()
    log("Role added.", "✅")

    # 5. Remove User Role
    log(f"Removing super_admin role from user {user_id}...")
    resp = session.delete(f"/admin/users/{user_id}/roles/super_admin")
    results["remove_role"] = resp.json()
    log("Role removed.", "✅")

    # 6. Delete User
    log(f"Deleting user {user_id}...")
    resp = session.delete(f"/admin/users/{user_id}")
    results["delete_user"] = resp.json()
    log("User deleted.", "✅")

    save_result("admin_users_test", results)

if __name__ == "__main__":
    test_users_comprehensive()
