from utils import AdminSession, log, save_result

def test_logs_comprehensive():
    session = AdminSession()
    if not session.token:
        return

    results = {}
    log("Starting Comprehensive Logs and Diagnostics Test", "🔍")

    # 1. Global Last Records
    log("Retrieving global last records...")
    resp = session.get("/admin/last-records?n=10")
    if resp.status_code == 200:
        data = resp.json()
        results["last_records_global"] = data
        log(f"Retrieved {len(data.get('records', []))} global records.", "✅")
    else:
        log(f"Failed: {resp.text}", "❌")

    # 2. Project-specific Last Records
    project_id = "tb"
    log(f"Retrieving last records for project '{project_id}'...")
    resp = session.get(f"/admin/projects/{project_id}/last-records?n=5")
    if resp.status_code == 200:
        data = resp.json()
        results["last_records_project"] = data
        log(f"Retrieved project records.", "✅")
    else:
        log(f"Failed: {resp.text}", "❌")

    # 3. Global CSV Export
    log("Testing global CSV export...")
    resp = session.get("/admin/last-records-csv?n=10")
    if resp.status_code == 200:
        results["csv_export_global"] = {"content_type": resp.headers.get("Content-Type"), "length": len(resp.text)}
        log(f"CSV export successful ({len(resp.text)} bytes).", "✅")
    else:
        log(f"Failed: {resp.text}", "❌")

    # 4. Project CSV Export
    log(f"Testing CSV export for project '{project_id}'...")
    resp = session.get(f"/admin/projects/{project_id}/last-records-csv?n=5")
    if resp.status_code == 200:
        results["csv_export_project"] = {"content_type": resp.headers.get("Content-Type"), "length": len(resp.text)}
        log(f"Project CSV export successful.", "✅")
    else:
        log(f"Failed: {resp.text}", "❌")

    save_result("admin_logs_test", results)

if __name__ == "__main__":
    test_logs_comprehensive()
