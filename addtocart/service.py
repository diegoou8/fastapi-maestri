import pymysql
from fastapi import HTTPException
import logging

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