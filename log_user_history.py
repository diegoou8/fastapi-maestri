from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance, CollectionStatus
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime
import uuid
import os
import numpy as np

# === Load environment variables
load_dotenv()

# === Initialize router
router = APIRouter()

# === Clients
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
qdrant_client = QdrantClient(host="qdrant", port=6333, https=False)

# === Collection configuration
collection_name = "user_history"
embedding_model = "text-embedding-3-small"
embedding_size = 1536

# === Request body schema
class HistoryRecord(BaseModel):
    subscriber_id: str
    question: str
    answer: str
    product_ids: list[str] = []

# === Response schema
class SuccessResponse(BaseModel):
    status: str

# === Ensure collection exists
def ensure_collection_exists():
    if not qdrant_client.collection_exists(collection_name):
        print(f"🛠️ Creating collection '{collection_name}'...")
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=embedding_size, distance=Distance.COSINE),
            on_disk_payload=True,
            payload_schema={
                "question": {"type": "text"},
                "answer": {"type": "text"},
                "subscriber_id": {"type": "keyword"},
                "product_ids": {"type": "keyword"},
                "timestamp": {"type": "text"}
            }
        )
        print(f"✅ Collection '{collection_name}' created.")
    else:
        print(f"✅ Collection '{collection_name}' already exists.")

# === Check collection at startup
ensure_collection_exists()

# === POST endpoint to log interaction
@router.post("/log_user_history", response_model=SuccessResponse)
def log_user_history(record: HistoryRecord):
    try:
        # Generate embedding
        embedding = openai_client.embeddings.create(
            model=embedding_model,
            input=record.question
        )
        vector = np.array(embedding.data[0].embedding).tolist()

        # Insert into Qdrant
        qdrant_client.upsert(
            collection_name=collection_name,
            points=[
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload={
                        "question": record.question,
                        "answer": record.answer,
                        "subscriber_id": record.subscriber_id,
                        "product_ids": record.product_ids,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
            ]
        )

        print(f"✅ Logged interaction: {record.question[:40]}... (Subscriber: {record.subscriber_id})")
        return {"status": "✅ saved"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
