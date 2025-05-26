from pydantic import BaseModel
from typing import Optional
import mysql.connector
import logging

class AddToCartRequest(BaseModel):
    user_id: str
    product_id: str
    product_url: str
    quantity: Optional[int] = 1

def add_product_to_cart(user_id: str, product_id: str, product_url: str, quantity: int = 1):
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="your_mysql_password",
            database="ecommerce"
        )
        cursor = conn.cursor()

        cursor.execute("SELECT cart_id FROM cart_sessions WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        if result:
            session_id = result[0]
        else:
            cursor.execute("INSERT INTO cart_sessions (user_id) VALUES (%s)", (user_id,))
            session_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO cart_items (session_id, product_id, product_url, quantity)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE quantity = quantity + %s
        """, (session_id, product_id, product_url, quantity, quantity))

        conn.commit()

    except Exception as e:
        logging.error(f"MySQL cart insert error: {e}")
        raise e
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return {"message": "Product added to cart successfully"}