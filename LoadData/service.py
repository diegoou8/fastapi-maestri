import os
import re
import uuid
import logging
import traceback
import requests
import pandas as pd
import numpy as np

from typing import List
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from fastapi import HTTPException

from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from qdrant_client.http.models import VectorParams as HTTPVectorParams, Distance as HTTPDistance
from sentence_transformers import SentenceTransformer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_all_webflow_items():
    offset = 0
    limit = 100
    all_items = []

    

    while True:
        try:
            response = requests.get(
                BASE_URL,
                headers=HEADERS,
                params={"offset": offset, "limit": limit}
            )
            response.raise_for_status()
            data = response.json()
            items = data.get("items", [])

            all_items.extend(items)
            

            if len(items) < limit:
                logger.info("All items fetched.")
                break

            offset += limit

        except requests.exceptions.RequestException as e:
            
            break
        except Exception as e:
            
            break

    
    
    return all_items



# Function to flatten and extract only desired fields
def extract_selected_fields(item):
    row = {}

    # Top-level fields
    for field in top_fields:
        row[field] = item.get(field)

    # From fieldData
    field_data = item.get("fieldData", {})
    for field in fielddata_fields:
        row[field] = field_data.get(field)
    
    # ✅ Extract image URL from 'imagen-del-producto'
    image_info = field_data.get("imagen-del-producto", {})
    if isinstance(image_info, dict):
        row["imagen_url"] = image_info.get("url")
    else:
        row["imagen_url"] = None

    return row


def get_all_products():

    load_dotenv()
    # ✅ Assign the API key
    openai_api_key = os.getenv("OPENAI_API_KEY")

    # ✅ Use it here
    openai_client = OpenAI(
        api_key=openai_api_key
    )
    # Load environment variables
    WEBFLOW_API_TOKEN = "026a04fef179155b6a04fbfd49e07c722e7621b91ad98961f6f298987c070180"
    COLLECTION_ID = "6660d3a96fe3b376c162563e"
    BASE_URL = f"https://api.webflow.com/v2/collections/{COLLECTION_ID}/items"

    HEADERS = {
        "Authorization": f"Bearer {WEBFLOW_API_TOKEN}",
        "accept-version": "2.0.0"
    }


    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger(__name__)

    # Define top-level fields (outside fieldData)
    top_fields = [
        "id",
        "lastPublished",
        "lastUpdated",
        "isArchived",
        "isDraft"
    ]

    # Define selected fieldData fields
    fielddata_fields = [
        "gr-ml",
        "ocasion",  # make sure spelling is consistent with Webflow — was 'ocasion' or 'occasion'?
        "precio",
        "maridaje-1",
        "maridaje-2",
        "pasillo",
        "bodega",
        "name",
        "descripcion",
        "notas-de-cata",
        "tipo",
        "slug",
        "descuento",
        "descuento-2x1",
        "descuento-3x2",
        "productoreserva",
        "descuento-off"
    ]

    # Get and transform all items
    items = get_all_webflow_items()
    flattened_data = [extract_selected_fields(item) for item in items]

    # Create the DataFrame
    df = pd.DataFrame(flattened_data)

    # Utility functions
    def clean(text):
        if pd.isna(text): return ""
        return str(text).strip()

    def strip_html(text):
        return BeautifulSoup(text, "html.parser").get_text(separator=" ", strip=True)


    def get_openai_embedding(text: str) -> list:
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding

    # Connect to Qdrant
    client = QdrantClient(host="qdrant", port=6333, https=False)
    collection_name = "maestri_products"
    embedding_size = 1536  # ✅ OpenAI embedding size is 1536

    client.recreate_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=embedding_size, distance=Distance.COSINE),
    )

    points = []

    for _, row in df.iterrows():
        if pd.isna(row.get("name")) or pd.isna(row.get("precio")) or row.get("isArchived") is True or row.get("isDraft") is True or row.get("lastPublished") is None:
            continue

        product_name = clean(row.get("name"))
        bodega = clean(row.get("bodega"))
        tipo = clean(row.get("tipo"))
        maridaje1 = clean(row.get("maridaje-1"))
        maridaje2 = clean(row.get("maridaje-2"))
        maridaje = " y ".join([m for m in [maridaje1, maridaje2] if m])
        notas = clean(row.get("notas-de-cata"))
        descripcion = strip_html(clean(row.get("descripcion")))
        precio = clean(row.get("precio"))
        category = clean(row.get("pasillo"))
        gr_ml = clean(row.get("gr-ml"))
        ocasion = clean(row.get("ocasion"))
        slug = clean(row.get("slug"))
        url = f"https://maestri.com.co/products/{slug}" if slug else ""

        descuento = bool(row.get("descuento", False))
        descuento_2x1 = bool(row.get("descuento-2x1", False))
        descuento_3x2 = bool(row.get("descuento-3x2", False))
        productoreserva = bool(row.get("productoreserva", False))
        descuento_off = bool(row.get("descuento-off", False))
        url_imagen = row.get("imagen_url", "")
        if pd.isna(url_imagen):
            url_imagen = ""

        alternate_names = ""

        short_text = f"""Producto: {product_name}. Tipo: {tipo}. Bodega: {bodega}.
        Maridaje: {maridaje}. Notas: {notas}. Descripción: {descripcion}.
        También conocido como: {alternate_names}. Precio: {precio}. GR/ML: {gr_ml}. Ocasion: {ocasion}.
        """

        if not short_text.strip():
            continue

        # Get vector
        vector = get_openai_embedding(short_text)

        # Payload for Qdrant
        payload = {
            "product_name": product_name,
            "bodega": bodega,
            "tipo": tipo,
            "precio": precio,
            "notas": notas,
            "descripcion": descripcion,
            "maridaje": maridaje,
            "category": category,
            "gr_ml": gr_ml,
            "ocasion": ocasion,
            "url": url,
            "descuento": descuento,
            "descuento_2x1": descuento_2x1,
            "descuento_3x2": descuento_3x2,
            "productoreserva": productoreserva,
            "descuento_off": descuento_off,
            "alternate_names": alternate_names,
            "url_imagen": url_imagen
        }


        points.append(PointStruct(id=str(uuid.uuid4()), vector=vector, payload=payload))

    # Insert into Qdrant
    client.upsert(collection_name=collection_name, points=points)
    print(f"✅ Inserted {len(points)} products into Qdrant collection: {collection_name}")
    return {"message": f"Inserted {len(points)} products into Qdrant collection: {collection_name}"}