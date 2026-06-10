from google import genai
import os
from dotenv import load_dotenv
from pathlib import Path
load_dotenv()
NEW_GEMMA_API_KEY = os.getenv("NEW_GEMMA_API_KEY")

client = genai.Client(api_key=NEW_GEMMA_API_KEY)

texts = [
    "tuberculosis treatment",
    "TB medication",
    "football match",
]

result = client.models.embed_content(
    model="gemini-embedding-2",
    contents=texts
)

print(len(result.embeddings))
embedding = result.embeddings[0].values

print(type(embedding))
print(len(embedding))
print(embedding[:20])  # first 20 dimensions

for i, emb in enumerate(result.embeddings):
    print(f"Text {i}")
    print(f"Dimensions: {len(emb.values)}")
    print(f"First 10 values: {emb.values[:10]}")
    print()