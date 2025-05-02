from pydantic import BaseModel
from qdrant_client import QdrantClient
from fastapi import APIRouter, HTTPException
import numpy as np
from typing import List, Optional
import re
import os
import logging
import traceback
from openai import OpenAI
from dotenv import load_dotenv

# === Load environment variables
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

# === Initialize OpenAI client
openai_client = OpenAI(api_key=openai_api_key)

DBInformacionMaestri_router = APIRouter()

# === Connect to Qdrant
qdrant_knowledge = QdrantClient(host="qdrant", port=6333, https=False)
qdrant_products = QdrantClient(host="qdrant", port=6333, https=False)
collection_knowledge = "maestri_knowledge"
collection_products = "maestri_products"

@DBInformacionMaestri_router.on_event("startup")
def load_model():
    global model
    model = openai_client

# === Request schema
class QueryRequest(BaseModel):
    question: str
    top_k: int = 3
    source_type: str  # "informacion" or "productos"
    expanded_terms: Optional[List[str]] = []

# === Response schema
class QueryResponse(BaseModel):
    top_answer: str
    context: List[str]
    source: str
    question: str

# === Hybrid reranking function
def hybrid_rerank(results, query, vector, expanded_terms=None):
    query_terms = query.lower().split()
    expanded_terms = [term.lower() for term in expanded_terms or []]
    boosted = []

    for r in results:
        base_score = np.dot(vector, r.vector)

        product_name = str(r.payload.get("product_name", "")).lower()
        tipo = str(r.payload.get("tipo", "")).lower()
        category = str(r.payload.get("category", "")).lower()
        description = str(r.payload.get("descripcion", "")).lower()
        alt_names = str(r.payload.get("alternate_names", "")).lower()

        score = base_score

        def count_exact_matches(keywords, field, weight):
            return sum(1 for kw in keywords if re.search(rf"\b{re.escape(kw)}\b", field)) * weight

        score += count_exact_matches(query_terms, product_name, 0.3)
        score += count_exact_matches(query_terms, tipo, 0.2)
        score += count_exact_matches(query_terms, category, 0.2)
        score += count_exact_matches(query_terms, description, 0.1)
        score += count_exact_matches(query_terms, alt_names, 0.1)

        score += count_exact_matches(expanded_terms, product_name, 0.7)
        score += count_exact_matches(expanded_terms, tipo, 0.4)
        score += count_exact_matches(expanded_terms, category, 0.4)
        score += count_exact_matches(expanded_terms, description, 0.2)
        score += count_exact_matches(expanded_terms, alt_names, 0.3)

        boosted.append((score, r))

    return [r for _, r in sorted(boosted, key=lambda x: x[0], reverse=True)]

# === Root endpoint
@DBInformacionMaestri_router.get("/")
def read_root():
    return {"message": "FastAPI Maestri is live!"}

# === Main Query endpoint
@DBInformacionMaestri_router.post("/query", response_model=QueryResponse)
def query_qdrant(request: QueryRequest):
    try:
        if model is None:
            raise HTTPException(status_code=500, detail="Model not loaded")

        # ✅ Generate OpenAI vector
        embedding = model.embeddings.create(
            model="text-embedding-3-small",
            input=request.question
        )
        vector = np.array(embedding.data[0].embedding)

        if request.source_type == "productos":
            results = qdrant_products.search(
                collection_name=collection_products,
                query_vector=vector.tolist(),
                limit=20,
                with_payload=True,
                with_vectors=True
            )

            reranked = hybrid_rerank(results, request.question, vector, request.expanded_terms)[:request.top_k]

            def format_product_payload(p):
                return "\n".join(
                    f"{k.replace('_', ' ').capitalize()}: {v}" for k, v in p.items() if v and k in [
                        "product_name", "bodega", "tipo", "region", "precio", "notas", "maridaje", "descripcion"]
                )

            context = [format_product_payload(r.payload) for r in reranked]

            if not context:
                raise HTTPException(status_code=404, detail="No matching products found.")

            return QueryResponse(top_answer=context[0],context=context, source="products", question=request.question)

        elif request.source_type == "informacion":
            results = qdrant_knowledge.search(
                collection_name=collection_knowledge,
                query_vector=vector.tolist(),
                limit=request.top_k,
                with_payload=True,
                with_vectors=True
            )

            context = [r.payload.get("text") for r in results if "text" in r.payload]

            if not context:
                raise HTTPException(status_code=404, detail="No matching knowledge found.")

            return QueryResponse(top_answer=context[0], context=context, source="informacion", question=request.question)

        else:
            raise HTTPException(status_code=400, detail="Invalid source_type. Must be 'informacion' or 'productos'.")

    except Exception as e:
        logging.error("Exception occurred:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
