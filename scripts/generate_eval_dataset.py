#!/usr/bin/env python3
"""
Generate an evaluation dataset (question, answer, chunk_id) from chunks.json
using Gemini 2.5 Flash. Safe to resume if interrupted.

Output: data/eval_dataset.jsonl (one JSON object per line)

Limits:
- MAX_QUESTIONS = 50 (to avoid hitting API daily quota)
- Skips chunks that are too short or have no meaningful TB content
"""

import json
import os
import time
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv
load_dotenv()

# --------------------
# CONFIG
# --------------------
BASE_DIR = Path(__file__).resolve().parents[1]
CHUNKS_PATH = BASE_DIR / "data" / "chunks.json"
OUTPUT_PATH = BASE_DIR / "data" / "eval_dataset.jsonl"
LOG_PATH = BASE_DIR / "data" / "eval_errors.log"

# Gemini 2.5 Flash setup
GEN_API_KEY = os.getenv("QUESTIONS_API_KEY")  # Set QUESTIONS_API_KEY in your environment
if not GEN_API_KEY:
    raise ValueError("Set QUESTIONS_API_KEY in your environment.")
genai.configure(api_key=GEN_API_KEY)
MODEL = genai.GenerativeModel("gemini-2.5-flash")

MAX_QUESTIONS = 50  # daily limit
MIN_CHUNK_LEN = 200  # skip tiny chunks

# --------------------
# PROMPT TEMPLATE
# --------------------
PROMPT_TEMPLATE = """
You are helping build a medical question-answer dataset about tuberculosis (TB).

Using ONLY the text below:
----------------
{chunk_text}
----------------

Task:
1. If the text does NOT contain meaningful TB-related medical information, respond with:
   SKIP

2. Otherwise, generate:
   - ONE clear factual question about TB that can be answered ONLY from this text.
   - ONE short precise answer based only on the text.

Rules:
- Do NOT use outside knowledge.
- Do NOT create yes/no questions.
- Do NOT mention "the text says".
- The answer must be supported by the text.
- Keep the answer under 2 sentences.

Return ONLY valid JSON with this format:
{{
  "question": "...",
  "answer": "..."
}}
"""

# --------------------
# LLM CALL
# --------------------
def call_llm(prompt: str) -> str:
    """Call Gemini 2.5 Flash with the given prompt."""
    response = MODEL.generate_content(
        prompt,
        generation_config={
            "temperature": 0.2,
            "max_output_tokens": 300
        }
    )
    return response.text.strip()

# --------------------
# RESUME LOGIC
# --------------------
def load_existing_ids(output_path: Path):
    processed = set()
    if output_path.exists():
        with output_path.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    processed.add(obj["chunk_id"])
                except:
                    continue
    return processed

# --------------------
# MAIN LOOP
# --------------------
def main():
    print("Loading chunks...")
    with CHUNKS_PATH.open("r", encoding="utf-8") as f:
        chunks = json.load(f)

    processed_ids = load_existing_ids(OUTPUT_PATH)
    print(f"Already processed: {len(processed_ids)} chunks")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    for i, chunk in enumerate(chunks):
        if count >= MAX_QUESTIONS:
            print("Reached daily limit.")
            break

        chunk_id = f"{chunk.get('source_file','unknown')}_{i}"

        if chunk_id in processed_ids:
            continue

        text = chunk.get("text", "").strip()
        if len(text) < MIN_CHUNK_LEN:
            print(f"[SKIP] {chunk_id} (too short)")
            continue

        prompt = PROMPT_TEMPLATE.format(chunk_text=text)

        try:
            response = call_llm(prompt)

            if response.strip().upper().startswith("SKIP"):
                print(f"[SKIP] {chunk_id} (no TB content)")
                continue

            data = json.loads(response)

            record = {
                "chunk_id": chunk_id,
                "question": data["question"],
                "answer": data["answer"],
                "chunk_text": text,
                "source_file": chunk.get("source_file", ""),
                "source_name": chunk.get("source_name", ""),
                "source_url": chunk.get("source_url", "")
            }

            # Append safely
            with OUTPUT_PATH.open("a", encoding="utf-8") as out:
                out.write(json.dumps(record, ensure_ascii=False) + "\n")

            count += 1
            print(f"[OK] {chunk_id} ({count}/{MAX_QUESTIONS})")

            # Polite rate limiting
            time.sleep(1)

        except Exception as e:
            with LOG_PATH.open("a", encoding="utf-8") as log:
                log.write(f"{chunk_id}: {str(e)}\n")
            print(f"[ERROR] {chunk_id}: {e}")
            continue

    print("Done generating evaluation dataset.")

if __name__ == "__main__":
    main()