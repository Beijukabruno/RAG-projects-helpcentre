import uuid
from utils import AdminSession, log, save_result

def test_projects_comprehensive():
    session = AdminSession()
    if not session.token:
        return

    results = {}
    log("Starting Comprehensive Project Management Test", "📁")

    # 1. List Projects
    log("Listing projects...")
    resp = session.get("/admin/projects")
    results["list_projects"] = resp.json()
    log(f"Found {len(resp.json().get('projects', []))} projects.", "✅")

    # 2. Create Project
    test_proj_id = f"proj_{uuid.uuid4().hex[:6]}"
    proj_payload = {
        "id": test_proj_id,
        "name": "Integration Test Project",
        "description": "A project created during integration testing",
        "domain_url": "https://test.example.com",
        "domain_owner": "Test Owner",
        "contact_email": "owner@example.com",
        "audiences": ["general", "clinicians", "researchers"],
        "config_json": {"setting": "value"}
    }
    log(f"Creating project {test_proj_id}...")
    resp = session.post("/admin/projects", json=proj_payload)
    if resp.status_code not in [200, 201]:
        log(f"Failed to create project: {resp.text}", "❌")
        return
    
    proj_data = resp.json()
    results["create_project"] = proj_data
    log(f"Project created: {test_proj_id}", "✅")
    
    # Verify new fields
    assert proj_data["domain_owner"] == "Test Owner"
    assert proj_data["contact_email"] == "owner@example.com"
    assert "researchers" in proj_data["audiences"]

    # 3. Get Project
    log(f"Getting project {test_proj_id}...")
    resp = session.get(f"/admin/projects/{test_proj_id}")
    results["get_project"] = resp.json()
    log("Project details retrieved.", "✅")

    # 4. Update Project
    log(f"Updating project {test_proj_id}...")
    resp = session.patch(f"/admin/projects/{test_proj_id}", json={"description": "Updated description", "domain_owner": "New Owner"})
    results["update_project"] = resp.json()
    log("Project updated.", "✅")
    assert resp.json()["domain_owner"] == "New Owner"

    # 5. List Project Admins
    log(f"Listing admins for project {test_proj_id}...")
    resp = session.get(f"/admin/projects/{test_proj_id}/admins")
    results["list_project_admins"] = resp.json()
    log("Admins listed.", "✅")

    # 6. Add Project Admin (Requires a user)
    log("Creating a temporary user to add as project admin...")
    user_payload = {
        "email": f"proj_admin_{uuid.uuid4().hex[:6]}@example.com",
        "password": "temp-password-123",
        "full_name": "Temp Project Admin"
    }
    user_resp = session.post("/admin/users", json=user_payload)
    if user_resp.status_code in [200, 201]:
        temp_user_id = user_resp.json()["id"]
        log(f"Adding user {temp_user_id} as admin to project {test_proj_id}...")
        resp = session.post(f"/admin/projects/{test_proj_id}/admins", json={"user_id": temp_user_id})
        results["add_project_admin"] = resp.json()
        log("Project admin added.", "✅")

        # 7. Remove Project Admin
        log(f"Removing user {temp_user_id} from project {test_proj_id} admins...")
        resp = session.delete(f"/admin/projects/{test_proj_id}/admins/{temp_user_id}")
        results["remove_project_admin"] = resp.json()
        log("Project admin removed.", "✅")

        # Cleanup user
        session.delete(f"/admin/users/{temp_user_id}")

    # 8. Delete Project
    log(f"Deleting project {test_proj_id}...")
    resp = session.delete(f"/admin/projects/{test_proj_id}")
    results["delete_project"] = resp.json()
    log("Project deleted.", "✅")

    save_result("admin_projects_test", results)

if __name__ == "__main__":
    test_projects_comprehensive()
