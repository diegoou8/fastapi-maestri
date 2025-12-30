from qdrant_client import QdrantClient
import importlib.metadata
import sys

def diagnose():
    try:
        version = importlib.metadata.version("qdrant-client")
        print(f"✅ Library version: {version}")
    except Exception:
        print("❌ Library version: NOT FOUND")
        return

    try:
        client = QdrantClient(host="localhost", port=6333)
        if hasattr(client, "search"):
            print("✅ Method 'search' exists in QdrantClient")
        else:
            print("❌ Method 'search' IS MISSING in QdrantClient")
            print("Available methods:", dir(client))
    except Exception as e:
        print(f"⚠️ Could not instantiate client (expected if Qdrant isn't at localhost): {e}")
        # Still check the class itself
        if hasattr(QdrantClient, "search"):
            print("✅ Method 'search' exists in CLASS QdrantClient")
        else:
            print("❌ Method 'search' IS MISSING in CLASS QdrantClient")

if __name__ == "__main__":
    diagnose()
