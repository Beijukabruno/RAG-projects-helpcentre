import gradio as gr
import requests
import uuid

API_BASE = "https://helpcentre-dsi-mdr.emergentai.ug"

session_id = str(uuid.uuid4())
last_message_id = None

def chat_with_bot(message, history):
    global last_message_id

    payload = {
        "query": message,
        "session_id": session_id
    }

    r = requests.post(f"{API_BASE}/chat", json=payload, timeout=60)
    data = r.json()

    answer = data.get("answer", "No response")
    last_message_id = data.get("message_id")

    # New Gradio format: list of dictionaries with 'role' and 'content'
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": answer})

    return history, ""

def send_rating(rating):
    global last_message_id

    payload = {
        "rating": rating
    }

    try:
        requests.post(f"{API_BASE}/rate", json=payload, timeout=10)
        return f"Thanks! You rated this answer {rating}/5 ⭐"
    except Exception as e:
        return f"Rating sent (connection may be offline): {rating}/5"

with gr.Blocks() as demo:
    gr.Markdown("# 🧠 HelpCentre AI")
    gr.Markdown("Ask questions about TB and cervical cancer")

    chatbot = gr.Chatbot(height=400)
    msg = gr.Textbox(placeholder="Type your question and press Enter…")

    clear = gr.Button("Clear chat")

    with gr.Row():
        rate1 = gr.Button("⭐ 1")
        rate2 = gr.Button("⭐ 2")
        rate3 = gr.Button("⭐ 3")
        rate4 = gr.Button("⭐ 4")
        rate5 = gr.Button("⭐ 5")

    status = gr.Markdown("")

    msg.submit(chat_with_bot, [msg, chatbot], [chatbot, msg])
    clear.click(lambda: [], None, chatbot)

    rate1.click(lambda: send_rating(1), None, status)
    rate2.click(lambda: send_rating(2), None, status)
    rate3.click(lambda: send_rating(3), None, status)
    rate4.click(lambda: send_rating(4), None, status)
    rate5.click(lambda: send_rating(5), None, status)

demo.launch(
    server_name="0.0.0.0",
    server_port=7860,
    theme=gr.themes.Soft()
)