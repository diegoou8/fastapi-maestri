import os
import re
import uuid
import logging
import traceback
import requests
import pandas as pd
import numpy as np
import pymysql
import json

from typing import List, Dict, Any
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from fastapi import HTTPException, Request

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
def get_all_webflow_items():

    # Load environment variables
    WEBFLOW_API_TOKEN = "026a04fef179155b6a04fbfd49e07c722e7621b91ad98961f6f298987c070180"
    COLLECTION_ID = "6660d3a96fe3b376c162563e"
    BASE_URL = f"https://api.webflow.com/v2/collections/{COLLECTION_ID}/items"

    HEADERS = {
        "Authorization": f"Bearer {WEBFLOW_API_TOKEN}",
        "accept-version": "2.0.0"
    }

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


def insert_sql(items):
    """
    Function to insert products into SQL database.
    This function is a placeholder and should be implemented based on your SQL database schema.
    """
    import mysql.connector

    # Connect to MySQL once before the loop
    mysql_conn = pymysql.connect(
        host="62.72.7.225",
        user="fastapi",
        password="your_secure_password",
        database="ecommerce",
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )
    mysql_cursor = mysql_conn.cursor()

    # 🔴 TRUNCATE TABLE BEFORE INSERTING
    mysql_cursor.execute("TRUNCATE TABLE products")
    mysql_conn.commit()
    def clean(text):
        if pd.isna(text): return ""
        return str(text).strip()
        # Get and transform all items
    def strip_html(text):
        return BeautifulSoup(text, "html.parser").get_text(separator=" ", strip=True)
    # Get all items from Webflow
    items = items
    flattened_data = [extract_selected_fields(item) for item in items]

    # Create the DataFrame
    df = pd.DataFrame(flattened_data)
    # Add inside your for loop, right after you clean and build each row:
    for _, row in df.iterrows():
        if pd.isna(row.get("name")) or pd.isna(row.get("precio")) or row.get("isArchived") is True or row.get("isDraft") is True or row.get("lastPublished") is None:
            continue

        id = clean(row.get("id"))
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
        url_imagen = row.get("imagen_url", "") if not pd.isna(row.get("imagen_url")) else ""

        descuento = bool(row.get("descuento", False))
        descuento_2x1 = bool(row.get("descuento-2x1", False))
        descuento_3x2 = bool(row.get("descuento-3x2", False))
        productoreserva = bool(row.get("productoreserva", False))
        descuento_off = bool(row.get("descuento-off", False))
        alternate_names = ""

        # Insert into MySQL
        insert_sql = """
            INSERT INTO products (
                id, product_name, bodega, tipo, precio, notas, descripcion, maridaje, category,
                gr_ml, ocasion, url, url_imagen, descuento, descuento_2x1, descuento_3x2,
                productoreserva, descuento_off, alternate_names
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                product_name = VALUES(product_name),
                bodega = VALUES(bodega),
                tipo = VALUES(tipo),
                precio = VALUES(precio),
                notas = VALUES(notas),
                descripcion = VALUES(descripcion),
                maridaje = VALUES(maridaje),
                category = VALUES(category),
                gr_ml = VALUES(gr_ml),
                ocasion = VALUES(ocasion),
                url = VALUES(url),
                url_imagen = VALUES(url_imagen),
                descuento = VALUES(descuento),
                descuento_2x1 = VALUES(descuento_2x1),
                descuento_3x2 = VALUES(descuento_3x2),
                productoreserva = VALUES(productoreserva),
                descuento_off = VALUES(descuento_off),
                alternate_names = VALUES(alternate_names)
        """
        mysql_cursor.execute(insert_sql, (
            id, product_name, bodega, tipo, precio, notas, descripcion, maridaje, category,
            gr_ml, ocasion, url, url_imagen, descuento, descuento_2x1, descuento_3x2,
            productoreserva, descuento_off, alternate_names
        ))
        mysql_conn.commit()
    mysql_cursor.close()
    mysql_conn.close()
    return {"message": "SQL Insert completed successfully."}

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

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger(__name__)

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
    insert_sql(items)
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
        id=clean(row.get("id"))
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
            "id": id,
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


def get_rows_sheet_products(rows: List[Dict[str, Any]]) -> pd.DataFrame:

    """
    Function to get rows from the Google sheet products once any row is updated.
    Coming from n8n automation.
    """
    def clean(text):
        if pd.isna(text): return ""
        return str(text).strip()
        # Get and transform all items
    def strip_html(text):
        return BeautifulSoup(text, "html.parser").get_text(separator=" ", strip=True)

    processed = []
    for row in rows:
        # skip if missing required fields or marked for deletion
        if (
            pd.isna(row.get("Nombre")) or
            pd.isna(row.get("Precio")) 
            ##or bool(row.get("Eliminar"))
        ):
            continue

        # build your record
        record = {
            "id":                   clean(row.get("Item ID")),
            "product_name":         clean(row.get("Nombre")),
            "bodega":               clean(row.get("Bodega")),
            "tipo":                 clean(row.get("Tipo")),
            "maridaje":             " y ".join(filter(None, [
                                        clean(row.get("Maridaje 1")),
                                        clean(row.get("Maridaje 2"))
                                    ])),
            "notas":                clean(row.get("Notas de cata")),
            "descripcion":          strip_html(clean(row.get("Descripción"))),
            "precio":               clean(row.get("Precio")),
            "category":             clean(row.get("Pasillo")),
            "gr_ml":                clean(row.get("Gr/ml")),
            "ocasion":              clean(row.get("Ocasión")),
            "slug":                 clean(row.get("Slug")),
            "url":                  f"https://maestri.com.co/products/{clean(row.get('Slug'))}"
                                   if row.get("Slug") else "",
            "descuento":            bool(row.get("Descuento", False)),
            "descuento_2x1":        bool(row.get("Descuento 2x1", False)),
            "descuento_3x2":        bool(row.get("Descuento 3x2", False)),
            "productoreserva":      bool(row.get("ProductoReserva", False)),
            "descuento_off":        bool(row.get("Descuento%off", False)),
            "url_imagen":           clean(row.get("Imagen del Producto") or ""),
            "draft":                bool(row.get("Draft", False)),
        }
        processed.append(record)

    # now build your dataframe
    df = pd.DataFrame(processed)
    
    return df


def sync_items_individually(dataframe) -> List[Dict[str, Any]]:
    """
    For each row, send a PATCH updating exactly that one item.
    Returns a list of the Webflow responses.
    """

    # Load environment variables
    WEBFLOW_API_TOKEN = "026a04fef179155b6a04fbfd49e07c722e7621b91ad98961f6f298987c070180"
    COLLECTION_ID = "6660d3a96fe3b376c162563e"

    BASE_URL = f"https://api.webflow.com/v2/collections/{COLLECTION_ID}/items/live"
    HEADERS = {
        "Authorization": f"Bearer {WEBFLOW_API_TOKEN}",
        "Content-Type":  "application/json",
        "Accept-Version": "1.0.0",
    }
    results = []

    # First, transform your raw rows into the clean records:
    df = dataframe.copy()
    records = df.to_dict(orient="records")
    success_count = 0

    for rec in records:
        payload = {
            "items": [
                {
                    "id": rec["id"],
                    "cmsLocaleId": rec.get("locale_id", rec.get("Locale ID")),  # whichever key holds your locale
                    "fieldData": {
                        "name":               rec["product_name"],
                        "slug":               rec["slug"],
                        "bodega":             rec["bodega"],
                        "tipo":               rec["tipo"],
                        "maridaje":           rec["maridaje"],
                        "notas":              rec["notas"],
                        "descripcion":        rec["descripcion"],
                        "precio":             rec["precio"],
                        "categoria":          rec["category"],
                        "gr-ml":              rec["gr_ml"],
                        "ocasion":            rec["ocasion"],
                        "url":                rec["url"],
                        "descuento":          rec["descuento"],
                        "descuento-2x1":      rec["descuento_2x1"],
                        "descuento-3x2":      rec["descuento_3x2"],
                        "productoreserva":    rec["productoreserva"],
                        "descuento-off":      rec["descuento_off"],
                        "imagen-del-producto": {
                            "url": rec["url_imagen"]
                        },
                        "draft":              rec["draft"]
                    }
                }
            ]
        }
        # single-item endpoint
        item_url = (
            f"https://api.webflow.com/v2/collections/"
            f"{COLLECTION_ID}/items/{rec['id']}/live?skipInvalidFiles=true"
        )

        resp = requests.patch(item_url, headers=HEADERS, json=payload, timeout=10)

        if resp.ok:
            success_count += 1
        else:
            # optionally log: rec['id'], resp.status_code, resp.text
            print(f"Failed {rec['id']}: {resp.status_code} {resp.text}")

    return success_count