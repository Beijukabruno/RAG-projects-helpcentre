import pandas as pd
df = pd.read_csv("eval_results_full_remote.csv")

print("Precision@5:", df["precision@5"].mean())
print("Recall@5:", df["recall@5"].mean())
print("MRR@5:", df["mrr@5"].mean())
print("NDCG@5:", df["ndcg@5"].mean())
print("MAP@5:", df["map@5"].mean())

print("ROUGE-1:", df["rouge1"].mean())
print("ROUGE-2:", df["rouge2"].mean())
print("ROUGE-L:", df["rougeL"].mean())
print("BERTScore F1:", df["bertscore_f1"].mean())

print("Avg latency:", df["latency_sec"].mean())