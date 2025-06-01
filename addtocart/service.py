import pymysql
from fastapi import HTTPException
import logging
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, ScrollRequest
import os
import urllib.parse

def get_db_connection():
    return pymysql.connect(
        host="62.72.7.225",
        user="fastapi",
        password="your_secure_password",
        database="ecommerce",
        cursorclass=pymysql.cursors.DictCursor
    )

def create_cart_session(user_id: str) -> int:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT cart_id FROM cart_sessions 
            WHERE user_id = %s AND DATE(created_at) = CURDATE()
        """, (user_id,))
        result = cursor.fetchone()

        if result:
            session_id = result["cart_id"]
        else:
            cursor.execute("INSERT INTO cart_sessions (user_id) VALUES (%s)", (user_id,))
            session_id = cursor.lastrowid

        conn.commit()
        return session_id

    except Exception as e:
        logging.error(f"Cart session error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


def add_product_to_cart(user_id: str, product_id: str, product_url: str, quantity: int = 1):
    try:
        session_id = create_cart_session(user_id)
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO cart_items (session_id, product_id, product_url, quantity)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE quantity = quantity + %s
        """, (session_id, product_id, product_url, quantity, quantity))

        conn.commit()
        return {"message": "Product added to cart"}

    except Exception as e:
        logging.error(f"Add item error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


def remove_product_from_cart(user_id: str, product_id: str):
    try:
        session_id = create_cart_session(user_id)
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM cart_items 
            WHERE session_id = %s AND product_id = %s
        """, (session_id, product_id))

        conn.commit()
        return {"message": "Product removed from cart"}

    except Exception as e:
        logging.error(f"Remove item error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()
        
def get_cart_contents(user_id: str):
    try:
        session_id = create_cart_session(user_id)
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT product_id, product_url, quantity
            FROM cart_items
            WHERE session_id = %s
        """, (session_id,))
        items = cursor.fetchall()

        return {
            "session_id": session_id,
            "items": items
        }

    except Exception as e:
        logging.error(f"View cart error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

# Here this function is going to be used for pulling the cart items and search those items in qdrant
def foxycart_payload(user_id: str):
    try:
        cart_contents = get_cart_contents(user_id)
        product_ids = [item['product_id'] for item in cart_contents['items']]
        if not product_ids:
            raise HTTPException(status_code=404, detail="Cart is empty")

        client = QdrantClient(host="qdrant", port=6333, https=False)

        filter_conditions = [
            FieldCondition(key="product_id", match=MatchValue(value=pid))
            for pid in product_ids
        ]
        qdrant_filter = Filter(should=filter_conditions)

        results, _ = client.scroll(
            collection_name="maestri_products",
            with_payload=True,
            with_vectors=False,
            limit=100,
            filter=qdrant_filter
        )

        if not results:
            raise HTTPException(status_code=404, detail="No matching products found in Qdrant")

        # === Build query string payload
        index = 1
        query_params = {}

        for item in cart_contents['items']:
            pid = item['product_id']
            quantity = item['quantity']

            match = next((r.payload for r in results if r.payload.get("product_id") == pid), None)
            if not match:
                continue

            name = match.get("name")
            price = match.get("precio")
            category = match.get("category")
            image = match.get("url_imagen")

            for _ in range(quantity):
                query_params[f"{index}:name"] = name
                query_params[f"{index}:price"] = price
                query_params[f"{index}:category"] = category
                query_params[f"{index}:image"] = image
                index += 1

        base_url = "https://maestrimilano.foxycart.com/cart"
        encoded_query = urllib.parse.urlencode(query_params)
        checkout_url = f"{base_url}?{encoded_query}"

        return {
            "checkout_url": checkout_url,
            "item_count": index - 1
        }

    except Exception as e:
        logging.error(f"Foxycart payload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        print("FoxyCart payload generated successfully")