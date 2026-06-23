import requests
from utils import BASE_URL, log, save_result

def test_chat_search():
    log("Testing Chat and Search Endpoints...")
    all_results = {}

    # 1. Search (TB General)
    log("Testing TB Search...")
    search_payload = {"query": "What is TB?", "k": 3}
    resp = requests.post(f"{BASE_URL}/tb/search/general", json=search_payload)
    if resp.status_code == 200:
        search_data = resp.json()
        all_results["search_tb_general"] = search_data
        log(f"TB Search successful. Found {len(search_data['matches'])} chunks.", "✅")
    else:
        log(f"TB Search failed: {resp.text}", "❌")

    # 2. Chat (TB General)
    log("Testing TB Chat (this may take a moment for LLM)...")
    chat_payload = {"query": "Tell me about TB treatment.", "k": 3}
    try:
        resp = requests.post(f"{BASE_URL}/tb/chat/general", json=chat_payload, timeout=60)
        if resp.status_code == 200:
            chat_data = resp.json()
            all_results["chat_tb_general"] = chat_data
            log("TB Chat successful.", "✅")
            log(f"Answer snippet: {chat_data['answer'][:100]}...", "💬")
        else:
            log(f"TB Chat failed: {resp.text}", "❌")
    except Exception as e:
        log(f"TB Chat request error: {e}", "💥")

    save_result("chat_search_test", all_results)

if __name__ == "__main__":
    test_chat_search()
