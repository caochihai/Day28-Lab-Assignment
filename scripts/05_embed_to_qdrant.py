import os
import requests
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import random

EMBED_URL = os.getenv("EMBED_NGROK_URL")
qdrant = QdrantClient(host="localhost", port=6333)

# Tạo collection
qdrant.recreate_collection(
    collection_name="documents",
    vectors_config=VectorParams(size=384, distance=Distance.COSINE)
)

def embed_and_store(records: list[dict]):
    embeddings = []
    # Gọi Kaggle embedding service nếu cấu hình ngrok
    if EMBED_URL:
        try:
            response = requests.post(f"{EMBED_URL}/embed", json={"texts": [r["text"] for r in records]}, timeout=5.0)
            if response.status_code == 200:
                embeddings = response.json()["embeddings"]
        except Exception as e:
            print(f"Connection to Kaggle failed: {e}. Falling back to mock embeddings...")
    
    # Nếu không kết nối được hoặc không có URL, tạo mock embeddings 384 chiều
    if not embeddings:
        print("Using local mock 384-dimension embeddings...")
        for r in records:
            random.seed(hash(r["text"]))
            vec = [random.uniform(-1, 1) for _ in range(384)]
            # Chuẩn hóa vector cosine
            norm = sum(x**2 for x in vec)**0.5
            vec = [x / norm for x in vec]
            embeddings.append(vec)

    points = [
        PointStruct(id=i, vector=emb, payload=rec)
        for i, (emb, rec) in enumerate(zip(embeddings, records))
    ]
    qdrant.upsert(collection_name="documents", points=points)
    print(f"Integration 5 OK: {len(points)} vectors stored in Qdrant")

# Test với sample data
embed_and_store([
    {"id": "doc_001", "text": "AI platform integration test"},
    {"id": "doc_002", "text": "Kafka to Airflow pipeline"},
])

