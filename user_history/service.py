import os
import uuid
import numpy as np
from datetime import datetime
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
from models.schemas import HistoryRecord

load_dotenv()

collection_name = "user_history"
embedding_model = "text-embedding-3-small"
embedding_size = 1536

# Initialize Qdrant once
qdrant_client = QdrantClient(host="qdrant", port=6333, https=False)

# Lazily initialize OpenAI client
def get_openai_client():
    from openai import OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not found in environment variables.")
    return OpenAI(api_key=api_key)

# Ensure the Qdrant collection exists
def ensure_collection_exists():
    if not qdrant_client.collection_exists(collection_name):
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

# Log interaction to Qdrant
def log_interaction(record: HistoryRecord):
    openai_client = get_openai_client()
    embedding = openai_client.embeddings.create(
        model=embedding_model,
        input=record.question
    )
    vector = np.array(embedding.data[0].embedding).tolist()

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

    return {"status": "✅ saved"}
