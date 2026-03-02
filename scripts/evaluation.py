import requests
import pandas as pd
import time
import json
from tqdm import tqdm
from math import log2
from rouge_score import rouge_scorer
from bert_score import score as bertscore
from datetime import datetime
import os

API_URL = "http://localhost:8000/chat"  # CHANGE to your local endpoint
INPUT_CSV = "data/Evaluation_dataset_400_with_ids.csv"
OUTPUT_CSV = "eval_results_full_v2.csv"
TOP_K = 5
MAX_QUESTIONS = 50   # safe for rate limits
SLEEP_SEC = 2        # be gentle to server

# ================= METRIC FUNCTIONS =================

def precision_at_k(relevant, retrieved, k):
    return len(set(relevant) & set(retrieved[:k])) / k

def recall_at_k(relevant, retrieved, k):
    return len(set(relevant) & set(retrieved[:k])) / len(relevant) if relevant else 0

def mrr_at_k(relevant, retrieved, k):
    for i, doc in enumerate(retrieved[:k]):
        if doc in relevant:
            return 1 / (i + 1)
    return 0

def ndcg_at_k(relevant, retrieved, k):
    dcg = sum(1/log2(i+2) for i, d in enumerate(retrieved[:k]) if d in relevant)
    idcg = sum(1/log2(i+2) for i in range(min(len(relevant), k)))
    return dcg/idcg if idcg > 0 else 0

def ap_at_k(relevant, retrieved, k):
    hits = 0
    score = 0
    for i, d in enumerate(retrieved[:k]):
        if d in relevant:
            hits += 1
            score += hits/(i+1)
    return score/len(relevant) if relevant else 0

# ================= LOAD DATA =================

df = pd.read_csv(INPUT_CSV)
df = df.head(MAX_QUESTIONS)

# Resume support
if os.path.exists(OUTPUT_CSV):
    done_df = pd.read_csv(OUTPUT_CSV)
    done_questions = set(done_df["question"])
else:
    done_df = pd.DataFrame()
    done_questions = set()

scorer = rouge_scorer.RougeScorer(["rouge1","rouge2","rougeL"], use_stemmer=True)
rows = []

# ================= MAIN LOOP =================

for _, row in tqdm(df.iterrows(), total=len(df)):

    question = row["question"]
    gt_answer = row["ground_truth"]
    true_chunk = row["true_chunk_id"]

    if question in done_questions:
        continue

    payload = {"query": question}

    start = time.time()
    try:
        r = requests.post(API_URL, json=payload, timeout=60)
        latency = time.time() - start
        
        if r.status_code != 200:
            print(f"\nError: API returned status {r.status_code}")
            print(f"Response: {r.text}")
            continue
        
        data = r.json()
    except requests.exceptions.ConnectionError:
        print(f"\nError: Cannot connect to API at {API_URL}")
        print("Make sure the chatbot server is running (e.g., uvicorn or Flask server)")
        break
    except json.JSONDecodeError as e:
        print(f"\nError: Invalid JSON response from API")
        print(f"Response text: {r.text[:500]}")  # Print first 500 chars
        continue

    answer = data.get("answer","")
    sources = data.get("sources",[])
    retrieved_ids = [s["doc_id"] for s in sources]

    relevant = [true_chunk]

    p5 = precision_at_k(relevant, retrieved_ids, TOP_K)
    r5 = recall_at_k(relevant, retrieved_ids, TOP_K)
    mrr5 = mrr_at_k(relevant, retrieved_ids, TOP_K)
    ndcg5 = ndcg_at_k(relevant, retrieved_ids, TOP_K)
    map5 = ap_at_k(relevant, retrieved_ids, TOP_K)

    rouge_scores = scorer.score(gt_answer, answer)
    rouge1 = rouge_scores["rouge1"].fmeasure
    rouge2 = rouge_scores["rouge2"].fmeasure
    rougeL = rouge_scores["rougeL"].fmeasure

    P, R, F1 = bertscore([answer], [gt_answer], lang="en", model_type="microsoft/deberta-xlarge-mnli")
    bert_f1 = F1.item()

    result = {
        "question": question,
        "true_chunk_id": true_chunk,
        "retrieved_chunk_ids": json.dumps(retrieved_ids),
        "precision@5": p5,
        "recall@5": r5,
        "mrr@5": mrr5,
        "ndcg@5": ndcg5,
        "map@5": map5,
        "rouge1": rouge1,
        "rouge2": rouge2,
        "rougeL": rougeL,
        "bertscore_f1": bert_f1,
        "latency_sec": latency,
        "timestamp": datetime.utcnow().isoformat()
    }

    rows.append(result)

    pd.DataFrame(rows).to_csv(OUTPUT_CSV, mode="a", index=False, header=not os.path.exists(OUTPUT_CSV))
    rows = []

    time.sleep(SLEEP_SEC)

print("Evaluation complete.")