from utils import AdminSession, log, save_result

def test_monitoring_comprehensive():
    session = AdminSession()
    if not session.token:
        return

    results = {}
    log("Starting Comprehensive Monitoring and Overview Test", "📊")

    # 1. Platform Overview (Super Admin)
    log("Retrieving platform-wide overview...")
    resp = session.get("/admin/overview")
    if resp.status_code == 200:
        results["platform_overview"] = resp.json()
        log("Platform overview retrieved successfully.", "✅")
    else:
        log(f"Platform overview failed (Are you a super_admin?): {resp.text}", "❌")

    # 2. Project Overview
    project_id = "tb"
    log(f"Retrieving overview for project '{project_id}'...")
    resp = session.get(f"/admin/projects/{project_id}/overview")
    if resp.status_code == 200:
        results["project_overview"] = resp.json()
        log(f"Project overview for '{project_id}' retrieved.", "✅")
    else:
        log(f"Project overview failed: {resp.text}", "❌")

    # 3. Global Audit Logs
    log("Retrieving global audit logs...")
    resp = session.get("/admin/audit-logs?limit=10")
    if resp.status_code == 200:
        data = resp.json()
        results["global_audit_logs"] = data
        log(f"Retrieved {len(data.get('logs', []))} audit entries.", "✅")
    else:
        log(f"Global audit logs failed: {resp.text}", "❌")

    # 4. Project Audit Logs
    log(f"Retrieving audit logs for project '{project_id}'...")
    resp = session.get(f"/admin/projects/{project_id}/audit-logs?limit=10")
    if resp.status_code == 200:
        data = resp.json()
        results["project_audit_logs"] = data
        log(f"Project audit logs retrieved.", "✅")
    else:
        log(f"Project audit logs failed: {resp.text}", "❌")

    save_result("admin_monitoring_test", results)

if __name__ == "__main__":
    test_monitoring_comprehensive()
