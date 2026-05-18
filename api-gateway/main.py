# api-gateway/main.py
from fastapi import FastAPI, Request
from prometheus_fastapi_instrumentator import Instrumentator
from langsmith import traceable
import httpx, os, time

app = FastAPI(title="AI Platform API Gateway")
Instrumentator().instrument(app).expose(app)  # Integration 9: Prometheus

VLLM_URL = os.environ.get("VLLM_URL", "http://localhost:8001")
QDRANT_URL = os.environ.get("QDRANT_URL", "http://qdrant:6333")

@app.post("/api/v1/chat")
@traceable(name="Chat Endpoint", run_type="chain")
async def chat(request: Request):
    body = await request.json()
    if "query" not in body or not body.get("query"):
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="query is required")
    query = body["query"]
    start = time.time()


    # 1. Vector search with graceful degradation fallback
    context = []
    try:
        async with httpx.AsyncClient() as client:
            search_resp = await client.post(
                f"{QDRANT_URL}/collections/documents/points/search", 
                json={
                    "vector": body.get("embedding", [0.0] * 384),
                    "limit": 3
                },
                timeout=3.0
            )
            if search_resp.status_code == 200:
                context = search_resp.json().get("result", [])
            else:
                print(f"Qdrant returned non-200 status code: {search_resp.status_code}")
    except Exception as e:
        print(f"Qdrant vector search failed (graceful degradation fallback active): {e}")

    # 2. LLM inference with ngrok connection fallback
    prompt = f"Context: {context}\n\nQuery: {query}"
    answer = "Error: LLM service is currently unavailable. Falling back to offline response."
    model_name = "fallback-offline"
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            llm_resp = await client.post(f"{VLLM_URL}/v1/chat/completions", json={
                "model": "Qwen/Qwen2.5-7B-Instruct-GPTQ-Int4",
                "messages": [{"role": "user", "content": prompt}]
            })
            if llm_resp.status_code == 200:
                result = llm_resp.json()
                answer = result["choices"][0]["message"]["content"]
                model_name = result["model"]
            else:
                print(f"vLLM serving returned non-200 status code: {llm_resp.status_code}")
    except Exception as e:
        print(f"vLLM connection failed (hybrid disconnect fallback active): {e}")

    latency = (time.time() - start) * 1000

    return {
        "answer": answer,
        "latency_ms": round(latency, 2),
        "model": model_name
    }

@app.get("/health")
def health():
    return {"status": "ok"}

