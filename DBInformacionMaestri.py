from pydantic import BaseModel
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from typing import List
import uuid
from fastapi import APIRouter, HTTPException
import numpy as np

DBInformacionMaestri_router = APIRouter()

# Qdrant connections
qdrant_knowledge = QdrantClient(host="vps.maestri.com.co", port=6333, https=False)
qdrant_products = QdrantClient(host="vps.maestri.com.co", port=6333, https=False)
collection_knowledge = "maestri_knowledge"
collection_products = "maestri_products"

@DBInformacionMaestri_router.on_event("startup")
def load_model():
    global model
    model = SentenceTransformer("distiluse-base-multilingual-cased-v2")

# Request schema
class QueryRequest(BaseModel):
    question: str
    top_k: int = 3

# Response schema
class QueryResponse(BaseModel):
    top_answer: str
    context: List[str]
    source: str

@DBInformacionMaestri_router.get("/")
def read_root():
    return {"message": "FastAPI Maestri is live!"}

@DBInformacionMaestri_router.post("/query", response_model=QueryResponse)
def query_qdrant(request: QueryRequest):
    try:
        if model is None:
            raise HTTPException(status_code=500, detail="Model not loaded")

        # Step 1: Vectorize the question
        vector = model.encode(request.question, convert_to_numpy=True, normalize_embeddings=True)

        # Step 2: Query both collections
        knowledge_results = qdrant_knowledge.search(
            collection_name=collection_knowledge,
            query_vector=vector.tolist(),
            limit=request.top_k,
            with_payload=True,
            with_vectors=True
        )
        product_results = qdrant_products.search(
            collection_name=collection_products,
            query_vector=vector.tolist(),
            limit=request.top_k,
            with_payload=True,
            with_vectors=True
        )

        # Step 3: Score top hits
        def max_score(results):
            return max(np.dot(vector, r.vector) for r in results) if results else 0.0

        knowledge_score = max_score(knowledge_results)
        product_score = max_score(product_results)

        print("Knowledge Score:", knowledge_score)
        print("Product Score:", product_score)

        # Step 4: Choose best matching collection
        if product_score > knowledge_score:
            top = sorted(product_results, key=lambda r: np.dot(vector, r.vector), reverse=True)[:request.top_k]
            def format_product_payload(p):
                return "\n".join(
                    f"{k.replace('_', ' ').capitalize()}: {v}" for k, v in p.items() if v and k in [
                        "product_name", "bodega", "tipo", "region", "precio", "notas", "maridaje", "descripcion"]
                )
            context = [format_product_payload(r.payload) for r in top]
            return QueryResponse(top_answer=context[0], context=context, source="products")

        else:
            top = sorted(knowledge_results, key=lambda r: np.dot(vector, r.vector), reverse=True)[:request.top_k]
            context = [r.payload.get("text") for r in top if "text" in r.payload]
            return QueryResponse(top_answer=context[0], context=context, source="knowledge")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))