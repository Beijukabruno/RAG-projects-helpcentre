import json
import pandas as pd
import time
from pathlib import Path
from langchain_ollama.llms import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate

# ---------------- CONFIG ----------------
MODEL_NAME = "llama3.2"
INPUT_JSON = "/content/data/chunks.json"
OUTPUT_JSONL = "Evaluation_dataset_400.jsonl"
MAX_QUESTIONS = 400   # stop after this many valid QA pairs
SLEEP_TIME = 1        # gentle pacing
# ----------------------------------------

df = pd.read_json(INPUT_JSON)

llm = OllamaLLM(model=MODEL_NAME)

prompt_template = ChatPromptTemplate.from_template("""
You are a medical dataset generator.

From the TEXT below:
1. Generate ONE clear factual question about tuberculosis.
2. Generate its answer using ONLY information in the TEXT.
3. The answer must be fully contained in the TEXT.
4. If the TEXT does not contain useful TB facts, respond with: SKIP

Do NOT:
- ask about missing information
- answer with "not mentioned", "not specified", or "none"
- use outside knowledge

Return JSON only in this format:
{{
  "question": "...",
  "answer": "..."
}}

TEXT:
{chunk}
""")

chain = prompt_template | llm

output_path = Path(OUTPUT_JSONL)

# Load existing progress if present
existing = []
if output_path.exists():
    with open(output_path, "r") as f:
        for line in f:
            existing.append(json.loads(line))

print(f"Loaded {len(existing)} existing samples")

count = len(existing)

with open(output_path, "a") as fout:
    for idx, row in df.iterrows():
        if count >= MAX_QUESTIONS:
            break

        chunk = row["text"]

        try:
            response = chain.invoke({"chunk": chunk}).strip()
        except Exception as e:
            print(f"[ERROR] LLM failed at row {idx}: {e}")
            continue

        if response.upper().startswith("SKIP"):
            print(f"[SKIP] row {idx}")
            continue

        try:
            qa = json.loads(response)
        except Exception:
            print(f"[BAD JSON] row {idx}: {response}")
            continue

        answer = qa["answer"].lower()
        if any(x in answer for x in ["not mentioned", "not specified", "none"]):
            print(f"[FILTERED] weak answer at row {idx}")
            continue

        record = {
            "question": qa["question"],
            "ground_truth": qa["answer"],
            "context": chunk,
            "source_file": row["source_file"],
            "source_name": row["source_name"],
            "source_url": row["source_url"]
        }

        fout.write(json.dumps(record, ensure_ascii=False) + "\n")
        fout.flush()

        count += 1
        print(f"[OK] {count} samples")

        time.sleep(SLEEP_TIME)

print("Done.")