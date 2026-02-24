import gradio as gr
import requests

API_URL_CHAT = "http://localhost:8000/chat"
API_URL_SEARCH = "http://localhost:8000/search"

# Helper to call /chat endpoint
def chat_with_bot(message, session_id=None):
    payload = {"query": message}
    headers = {}
    if session_id:
        headers["X-Session-ID"] = session_id
    response = requests.post(API_URL_CHAT, json=payload, headers=headers)
    data = response.json()
    answer = data.get("answer", "")
    sources = data.get("sources", [])
    toxicity = data.get("toxicity_output", {})
    sources_str = "\n".join([
        f"{s.get('source_name','')} ({s.get('source_url','')})" for s in sources
    ])
    return answer, sources_str, toxicity

# Helper to call /search endpoint
def search_knowledge(query):
    payload = {"query": query}
    response = requests.post(API_URL_SEARCH, json=payload)
    data = response.json()
    matches = data.get("matches", [])
    results = []
    for m in matches:
        results.append(f"{m.get('source_name','')} ({m.get('source_url','')}): {m.get('full_text','')[:200]}...")
    return "\n\n".join(results)

with gr.Blocks() as demo:
    gr.Markdown("# TB Help Centre")
    with gr.Tab("Chatbot"):
        chatbot = gr.Chatbot()
        msg = gr.Textbox(label="Your message", placeholder="Type your question here...")
        sources = gr.Textbox(label="Sources", interactive=False)
        toxicity = gr.Textbox(label="Toxicity Output", interactive=False)
        session_id = gr.State()
        send_btn = gr.Button("Send")

        def respond(message, chat_history, session_id):
            answer, sources_str, toxicity_out = chat_with_bot(message, session_id)
            chat_history = chat_history + [[message, answer]]
            return chat_history, sources_str, str(toxicity_out), session_id

        send_btn.click(respond, [msg, chatbot, session_id], [chatbot, sources, toxicity, session_id])

    with gr.Tab("Semantic Search"):
        search_query = gr.Textbox(label="Search Knowledge Base", placeholder="Enter search query...")
        search_results = gr.Textbox(label="Search Results", interactive=False)
        search_btn = gr.Button("Search")

        def do_search(query):
            return search_knowledge(query)

        search_btn.click(do_search, search_query, search_results)

demo.launch()
