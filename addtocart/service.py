import pymysql
import logging
import os

def add_product_to_cart(user_id: str, product_id: str, product_url: str, quantity: int = 1):
    try:
        conn = pymysql.connect(
        host="62.72.7.225",
        user="fastapi",
        password="your_secure_password",
        database="ecommerce",
        cursorclass=pymysql.cursors.DictCursor
        )
        cursor = conn.cursor()

        # Get or create a cart session for today
        cursor.execute("""
            SELECT cart_id FROM cart_sessions 
            WHERE user_id = %s AND DATE(created_at) = CURDATE()
        """, (user_id,))
        result = cursor.fetchone()

        if result:
            session_id = result[0]
        else:
            cursor.execute("""
                INSERT INTO cart_sessions (user_id) 
                VALUES (%s)
            """, (user_id,))
            session_id = cursor.lastrowid

        # Insert/update or delete cart item
        if quantity == 0:
            cursor.execute("""
                DELETE FROM cart_items 
                WHERE session_id = %s AND product_id = %s
            """, (session_id, product_id))
        else:
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

    return {"message": "Product updated in cart successfully"}
