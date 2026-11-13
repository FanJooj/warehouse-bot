import sqlite3
from datetime import datetime

DB_NAME = "warehouse.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            display_name TEXT NOT NULL,
            quantity INTEGER NOT NULL CHECK(quantity >= 0),
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS operations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            user_name TEXT NOT NULL,
            delta INTEGER NOT NULL,
            action TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

def normalize_name(name: str) -> str:
    return " ".join(name.strip().lower().split())

def add_product(display_name: str, quantity: int, user_id: int, user_name: str):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN TRANSACTION")
        norm_name = normalize_name(display_name)
        
        cursor.execute("SELECT id, quantity FROM products WHERE name = ?", (norm_name,))
        row = cursor.fetchone()
        
        if row:
            product_id, current_qty = row["id"], row["quantity"]
            new_qty = current_qty + quantity
            cursor.execute(
                "UPDATE products SET quantity = ?, display_name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (new_qty, display_name.strip(), product_id)
            )
        else:
            cursor.execute(
                "INSERT INTO products (name, display_name, quantity, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                (norm_name, display_name.strip(), quantity)
            )
            
        cursor.execute(
            "INSERT INTO operations (product_name, user_id, user_name, delta, action, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (display_name.strip(), user_id, user_name, quantity, "add", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        return True, f"Добавлено: {display_name.strip()} — {quantity} шт. Всего на складе: {quantity if not row else row['quantity'] + quantity} шт."
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_all_products():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products ORDER BY display_name COLLATE NOCASE ASC")
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_product_by_id(product_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def update_quantity(product_id: int, delta: int, action: str, user_id: int, user_name: str):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN TRANSACTION")
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        product = cursor.fetchone()
        if not product:
            conn.rollback()
            return False, "Товар не найден."
        
        current_qty = product["quantity"]
        new_qty = current_qty + delta
        if new_qty < 0:
            conn.rollback()
            return False, f"На складе только {current_qty} шт."
            
        cursor.execute(
            "UPDATE products SET quantity = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (new_qty, product_id)
        )
        cursor.execute(
            "INSERT INTO operations (product_name, user_id, user_name, delta, action, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (product["display_name"], user_id, user_name, delta, action, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        return True, f"Успешно. Осталось: {new_qty} шт."
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def delete_product(product_id: int, user_id: int, user_name: str):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN TRANSACTION")
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        product = cursor.fetchone()
        if not product:
            conn.rollback()
            return False, "Товар не найден."
            
        cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
        cursor.execute(
            "INSERT INTO operations (product_name, user_id, user_name, delta, action, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (product["display_name"], user_id, user_name, -product["quantity"], "delete", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        return True, "Товар удалён."
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def search_products(query: str):
    conn = get_connection()
    cursor = conn.cursor()
    like_query = f"%{query.strip().lower()}%"
    cursor.execute("SELECT * FROM products WHERE LOWER(display_name) LIKE ? ORDER BY display_name COLLATE NOCASE ASC", (like_query,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_last_operations(limit: int = 20):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM operations ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows