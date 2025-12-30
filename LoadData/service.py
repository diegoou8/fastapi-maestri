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
import requests
import logging
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build




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
    "categories",
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
    "descuento-off",
    "Biologico",
    "denominacion"
]

# Helper to fetch dynamic categories from Webflow
def get_webflow_categories():
    TOKEN = "026a04fef179155b6a04fbfd49e07c722e7621b91ad98961f6f298987c070180"
    CAT_COLL_ID = "6660ca2d6fe3b376c15a6141" # 'Categorias' collection
    url = f"https://api.webflow.com/v2/collections/{CAT_COLL_ID}/items"
    headers = {"Authorization": f"Bearer {TOKEN}", "accept-version": "2.0.0"}
    
    resp = requests.get(url, headers=headers)
    mapping = {}
    if resp.status_code == 200:
        items = resp.json().get("items", [])
        for item in items:
            name = item.get("fieldData", {}).get("name")
            if name:
                mapping[item.get("id")] = name
    return mapping

category_mapping = {} # Will be populated dynamically
reverse_category_mapping = {} # Legacy fallback

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
        category = reverse_category_mapping.get(clean(row.get("categories")).lower(), clean(row.get("categories")))
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
        biologico = bool(row.get("Biologico", False))

        # Insert into MySQL
        insert_sql = """
            INSERT INTO products (
                id, product_name, bodega, tipo, precio, notas, descripcion, maridaje, category,
                gr_ml, ocasion, url, url_imagen, descuento, descuento_2x1, descuento_3x2,
                productoreserva, descuento_off, alternate_names,biologico
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s)
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
                alternate_names = VALUES(alternate_names),
                biologico = VALUES(biologico)
        """
        mysql_cursor.execute(insert_sql, (
            id, product_name, bodega, tipo, precio, notas, descripcion, maridaje, category,
            gr_ml, ocasion, url, url_imagen, descuento, descuento_2x1, descuento_3x2,
            productoreserva, descuento_off, alternate_names,biologico
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

    # Fetch dynamic category names
    dynamic_mapping = get_webflow_categories()

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
        denominacion = clean(row.get("denominacion"))
        maridaje1 = clean(row.get("maridaje-1"))
        maridaje2 = clean(row.get("maridaje-2"))
        maridaje = " y ".join([m for m in [maridaje1, maridaje2] if m])
        notas = clean(row.get("notas-de-cata"))
        descripcion = strip_html(clean(row.get("descripcion")))
        
        # ✅ Clean and Parse numeric price
        precio_raw = clean(row.get("precio"))
        try:
            precio_numeric = float(precio_raw.replace(",", "").replace("$", "")) if precio_raw else 0.0
        except:
            precio_numeric = 0.0
        
        # ✅ Dynamic Category
        cat_id = clean(row.get("categories"))
        category = dynamic_mapping.get(cat_id, cat_id)

        gr_ml = clean(row.get("gr-ml"))
        ocasion = clean(row.get("ocasion"))
        slug = clean(row.get("slug"))
        url = f"https://maestri.com.co/products/{slug}" if slug else ""

        descuento = bool(row.get("descuento", False))
        descuento_2x1 = bool(row.get("descuento-2x1", False))
        descuento_3x2 = bool(row.get("descuento-3x2", False))
        productoreserva = bool(row.get("productoreserva", False))
        descuento_off = bool(row.get("descuento-off", False))
        biologico = bool(row.get("Biologico", False))
        url_imagen = row.get("imagen_url", "")
        if pd.isna(url_imagen):
            url_imagen = ""

        # ✅ Semantic Enrichment
        semantic_tags = []
        # Price Tiers
        if precio_numeric > 0:
            if precio_numeric < 80000:
                semantic_tags.append("Vino económico, precio bajo, barato, accesible")
            elif precio_numeric < 200000:
                semantic_tags.append("Vino de precio medio, buena relación calidad-precio")
            else:
                semantic_tags.append("Vino premium, alta gama, exclusivo, lujo")
        
        # House Wine Check (Category ID: 66635db36d9753905f695788)
        if cat_id == "66635db36d9753905f695788":
            semantic_tags.append("Vino de la casa, recomendación especial de Maestri Milano")

        alternate_names = ""
        tags_text = ". ".join(semantic_tags)

        short_text = f"Producto: {product_name}. Tipo: {tipo}. Bodega: {bodega}. Origen: {denominacion}. Categoría: {category}. Contenido: {gr_ml}. "
        short_text += f"Maridaje: {maridaje}. Notas: {notas}. Descripción: {descripcion}. {tags_text}. "
        short_text += f"También conocido como: {alternate_names}. Precio: {precio_raw}. Ocasion: {ocasion}. Biologico: {biologico}."

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
            "denominacion": denominacion,
            "precio": precio_raw,
            "precio_numeric": precio_numeric,
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
            "biologico": biologico,
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
            "category":             reverse_category_mapping.get(clean(row.get("categories")).lower(), clean(row.get("categories"))),
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

def google_merchant_upload():
    """
    Fetch items from Webflow and upload them to Google Merchant Center.
    """

    MERCHANT_ID = "441343742"   

    SERVICE_ACCOUNT_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "service_account.json"))
    SCOPES = ["https://www.googleapis.com/auth/content"]

    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )

    # Build Google Content API client
    service = build("content", "v2.1", credentials=credentials)
    def clean(text):
        if pd.isna(text): return ""
        return str(text).strip()
        # Get and transform all items
    def strip_html(text):
        return BeautifulSoup(text, "html.parser").get_text(separator=" ", strip=True)

    def webflow_to_product(row):
        fd = row.get("fieldData", {})  # shortcut

        # Core fields
        id = clean(row.get("id"))
        product_name = clean(fd.get("name"))
        precio_raw = clean(fd.get("precio"))
        slug = clean(fd.get("slug"))

        # Image handling
        imagen_data = fd.get("imagen-del-producto")
        url_imagen = ""

        if isinstance(imagen_data, dict):
            url_imagen = clean(imagen_data.get("url"))
        elif isinstance(imagen_data, list) and len(imagen_data) > 0 and isinstance(imagen_data[0], dict):
            url_imagen = clean(imagen_data[0].get("url"))

        if not url_imagen.startswith("http"):
            url_imagen = "https://maestri.com.co/default-image.jpg"

        # ✅ Normalize price
        try:
            precio = float(precio_raw.replace(",", "").replace("$", "")) if precio_raw else 0.0
        except Exception:
            precio = 0.0

        # ✅ Build link
        url = f"https://maestri.com.co/products/{slug}" if slug else ""

        # ✅ Build description
        bodega = clean(fd.get("bodega"))
        tipo = clean(fd.get("tipo"))
        maridaje1 = clean(fd.get("maridaje-1"))
        maridaje2 = clean(fd.get("maridaje-2"))
        maridaje = " y ".join([m for m in [maridaje1, maridaje2] if m])
        notas = clean(fd.get("notas-de-cata"))
        gr_ml = clean(fd.get("gr-ml"))
        ocasion = clean(fd.get("ocasion"))
        descripcion_html = fd.get("descripcion")
        descripcion_texto = strip_html(descripcion_html)

        description_parts = [
            f"{product_name} - {bodega}" if product_name else "",
            f"Tipo: {tipo}" if tipo else "",
            f"Notas: {notas}" if notas else "",
            f"Maridaje: {maridaje}" if maridaje else "",
            f"Ocasión: {ocasion}" if ocasion else "",
            f"Contenido: {gr_ml}" if gr_ml else "",
            descripcion_texto,
        ]
        description = " | ".join([d for d in description_parts if d])

        # ✅ Availability logic
        if row.get("isArchived") or row.get("isDraft"):
            availability = "out of stock"
        else:
            availability = "in stock"

        return {
            "offerId": id,
            "title": product_name or "Producto Maestri",
            "description": description or "Producto disponible en Maestri Milano.",
            "link": url,
            "imageLink": url_imagen,
            "contentLanguage": "es",
            "targetCountry": "CO",
            "channel": "online",
            "availability": availability,
            "condition": "new",
            "price": {"value": f"{precio:.2f}", "currency": "COP"},
        }

    # ---------------------------
    # UPSERT TO GOOGLE MERCHANT
    # ---------------------------
    def upsert_products_to_merchant():
        webflow_items = get_all_webflow_items()

        if not webflow_items:
            print("⚠️ No items fetched from Webflow.")
            return

        # Map all Webflow items to Merchant products
        products = [webflow_to_product(item) for item in webflow_items]

        # Debug: show an example
        print("🔎 Example product being uploaded:")
        import json
        print(json.dumps(products[0], indent=4, ensure_ascii=False))

        # Batch insert
        batch_request = {
            "entries": [
                {"batchId": i, "merchantId": MERCHANT_ID, "method": "insert", "product": p}
                for i, p in enumerate(products)
            ]
        }

        try:
            response = service.products().custombatch(body=batch_request).execute()
            print(f"✅ Synced {len(products)} products to Google Merchant.")
        except Exception as e:
            print(f"❌ Failed batch insert: {e}")

    upsert_products_to_merchant()
def sync_knowledge_from_sheet():
    """
    Sync business info from Google Sheets to Qdrant collection 'maestri_knowledge'.
    """
    SPREADSHEET_ID = '1kahhXVs12upC_Z3LUUl5B8IcoThbDFTn4Ypp9WfFZqE'
    RANGE_NAME = 'Sheet1!A2:B'
    creds_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "service_account.json"))
    
    creds = service_account.Credentials.from_service_account_file(creds_path, scopes=['https://www.googleapis.com/auth/spreadsheets.readonly'])
    service = build('sheets', 'v4', credentials=creds)
    
    try:
        result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
        values = result.get('values', [])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error reading Google Sheet: {str(e)}')

    if not values:
        return {'message': 'No data found in the Google Sheet.'}

    documents = []
    for row in values:
        if len(row) >= 2 and row[0] and row[1]:
            documents.append({'category': str(row[0]).strip(), 'text': str(row[1]).strip()})

    if not documents:
        return {'message': 'No valid data found.'}

    load_dotenv()
    openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    qdrant_client = QdrantClient(host='qdrant', port=6333, https=False)
    
    qdrant_client.recreate_collection(
        collection_name='maestri_knowledge',
        vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
    )

    texts = [doc['text'] for doc in documents]
    response = openai_client.embeddings.create(input=texts, model='text-embedding-3-small')
    
    points = [
        PointStruct(id=str(uuid.uuid4()), vector=emb.embedding, payload=documents[i]) 
        for i, emb in enumerate(response.data)
    ]
    
    qdrant_client.upsert(collection_name='maestri_knowledge', points=points)
    
    return {'message': f'Successfully synced {len(points)} knowledge items.'}
