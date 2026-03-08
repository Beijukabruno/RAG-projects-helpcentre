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

# ================= CONFIG =================

API_URL = "https://helpcentre-dsi-mdr.emergentai.ug/chat"  # remote endpoint
INPUT_CSV = "data/Evaluation_dataset_400_with_ids.csv"
OUTPUT_CSV = "eval_results_full_remote.csv"

TOP_K = 5
MAX_QUESTIONS = 50
SLEEP_SEC = 2
TIMEOUT = 60
MAX_RETRIES = 3

# ================= METRIC FUNCTIONS =================

def precision_at_k(relevant, retrieved, k):
    return len(set(relevant) & set(retrieved[:k])) / k if k > 0 else 0

def recall_at_k(relevant, retrieved, k):
    return len(set(relevant) & set(retrieved[:k])) / len(relevant) if relevant else 0

def hit_at_k(relevant, retrieved, k):
    return 1 if len(set(relevant) & set(retrieved[:k])) > 0 else 0

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

df = pd.read_csv(INPUT_CSV).head(MAX_QUESTIONS)

# Resume support
if os.path.exists(OUTPUT_CSV):
    done_df = pd.read_csv(OUTPUT_CSV)
    done_questions = set(done_df["question"])
else:
    done_df = pd.DataFrame()
    done_questions = set()

scorer = rouge_scorer.RougeScorer(["rouge1","rouge2","rougeL"], use_stemmer=True)

# ================= MAIN LOOP =================

for _, row in tqdm(df.iterrows(), total=len(df)):

    question = row["question"]
    gt_answer = str(row["ground_truth"])
    true_chunk = row["true_chunk_id"]

    if question in done_questions:
        continue

    payload = {"query": question}

    retries = 0
    success = False

    while retries < MAX_RETRIES and not success:
        try:
            start = time.time()
            r = requests.post(API_URL, json=payload, timeout=TIMEOUT)
            latency = time.time() - start

            if r.status_code != 200:
                raise RuntimeError(f"HTTP {r.status_code}")

            data = r.json()
            success = True

        except Exception as e:
            retries += 1
            print(f"⚠️ Retry {retries}/{MAX_RETRIES} for question: {question}")
            print(e)
            time.sleep(2)

    if not success:
        result = {
            "question": question,
            "true_chunk_id": true_chunk,
            "retrieved_chunk_ids": "[]",
            "precision@5": 0,
            "recall@5": 0,
            "hit@5": 0,
            "mrr@5": 0,
            "ndcg@5": 0,
            "map@5": 0,
            "rouge1": 0,
            "rouge2": 0,
            "rougeL": 0,
            "bertscore_f1": 0,
            "latency_sec": None,
            "status": "failed",
            "timestamp": datetime.utcnow().isoformat()
        }
        pd.DataFrame([result]).to_csv(
            OUTPUT_CSV, mode="a", index=False,
            header=not os.path.exists(OUTPUT_CSV)
        )
        continue

    answer = data.get("answer","")
    sources = data.get("sources", [])

    # Extract retrieved chunk IDs safely
    retrieved_ids = []
    for s in sources:
        if isinstance(s, dict) and "doc_id" in s:
            retrieved_ids.append(s["doc_id"])

    relevant = [true_chunk]

    # ===== Retriever metrics =====
    p5 = precision_at_k(relevant, retrieved_ids, TOP_K)
    r5 = recall_at_k(relevant, retrieved_ids, TOP_K)
    hit5 = hit_at_k(relevant, retrieved_ids, TOP_K)
    mrr5 = mrr_at_k(relevant, retrieved_ids, TOP_K)
    ndcg5 = ndcg_at_k(relevant, retrieved_ids, TOP_K)
    map5 = ap_at_k(relevant, retrieved_ids, TOP_K)

    # ===== Generator metrics =====
    rouge_scores = scorer.score(gt_answer, answer)
    rouge1 = rouge_scores["rouge1"].fmeasure
    rouge2 = rouge_scores["rouge2"].fmeasure
    rougeL = rouge_scores["rougeL"].fmeasure

    try:
        P, R, F1 = bertscore([answer], [gt_answer], lang="en", model_type="microsoft/deberta-xlarge-mnli")
        bert_f1 = F1.item()
    except:
        bert_f1 = 0

    result = {
        "question": question,
        "true_chunk_id": true_chunk,
        "answer": answer,
        "retrieved_chunk_ids": json.dumps(retrieved_ids),
        "precision@5": p5,
        "recall@5": r5,
        "hit@5": hit5,
        "mrr@5": mrr5,
        "ndcg@5": ndcg5,
        "map@5": map5,
        "rouge1": rouge1,
        "rouge2": rouge2,
        "rougeL": rougeL,
        "bertscore_f1": bert_f1,
        "latency_sec": latency,
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat()
    }

    pd.DataFrame([result]).to_csv(
        OUTPUT_CSV, mode="a", index=False,
        header=not os.path.exists(OUTPUT_CSV)
    )

    time.sleep(SLEEP_SEC)

print("✅ Evaluation complete.")