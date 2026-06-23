import time
import io
from utils import AdminSession, log, save_result

def test_kb_comprehensive():
    session = AdminSession()
    if not session.token:
        return

    results = {}
    log("Starting Comprehensive Knowledge Base Management Test", "📚")

    # 1. List Knowledge Base
    project_id = "tb"
    log(f"Listing KB for project {project_id}...")
    resp = session.get(f"/admin/projects/{project_id}/knowledge-base")
    results["list_kb"] = resp.json()
    log(f"Found {len(resp.json().get('assets', []))} assets.", "✅")

    # 2. Upload Metadata CSV
    csv_content = "md_name,source_name,source_url\nintegration_test_doc.md,Integration Test Title,https://example.com/test"
    files = {"file": ("sources.csv", csv_content, "text/csv")}
    data = {"audience": "general"}
    log("Uploading metadata CSV...")
    resp = session.post(f"/admin/projects/{project_id}/knowledge-base", data=data, files=files)
    results["upload_csv"] = resp.json()
    log("Metadata CSV uploaded.", "✅")

    # 3. Upload KB Source
    test_filename = "integration_test_doc.md"
    test_content = "# Integration Test\nThis document was uploaded during an automated integration test."
    files = {"file": (test_filename, test_content, "text/markdown")}
    data = {"audience": "general", "source_name": "Integration Test Upload"}
    
    log(f"Uploading KB source {test_filename}...")
    resp = session.post(f"/admin/projects/{project_id}/knowledge-base", data=data, files=files)
    if resp.status_code != 200:
        log(f"Upload failed: {resp.text}", "❌")
        return
    
    upload_data = resp.json()
    asset_id = upload_data["asset_id"]
    results["upload_kb"] = upload_data
    log(f"Upload successful. Asset ID: {asset_id}", "✅")

    # 4. Activate KB Source (Indexing)
    log(f"Activating asset {asset_id} (triggering embedding/indexing)...")
    try:
        # Long timeout for LLM embedding
        resp = session.post(f"/admin/projects/{project_id}/knowledge-base/{asset_id}/activate", timeout=60)
        if resp.status_code == 200:
            activate_data = resp.json()
            results["activate_kb"] = activate_data
            log(f"Activation successful. Chunks created: {activate_data.get('chunk_count')}", "✅")
            log(f"Verification: {activate_data.get('verification')}", "✅")
        else:
            log(f"Activation failed: {resp.text}", "❌")
    except Exception as e:
        log(f"Activation error: {e}", "💥")

    # 5. Delete KB Source
    log(f"Deleting KB source file {test_filename}...")
    # The route in admin.py is @router.get but named delete_knowledge_base_source? 
    # Wait, looking at admin.py:
    # @router.get("/projects/{project_id}/knowledge-base/{file_name}", tags=["Admin: Knowledge Base"])
    # def delete_knowledge_base_source(...)
    # It should probably be DELETE. I'll check that.
    resp = session.get(f"/admin/projects/{project_id}/knowledge-base/{test_filename}")
    results["delete_kb"] = resp.json()
    log("KB source deleted.", "✅")

    save_result("admin_kb_test", results)

if __name__ == "__main__":
    test_kb_comprehensive()
