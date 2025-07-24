# models.py
import bcrypt
from db import Database

db = Database()

class User:
    @staticmethod
    def create(full_name, username, password, role="Administrador"):
        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        db.execute(
            "INSERT INTO users (full_name, username, password_hash, role) VALUES (?,?,?,?)",
            (full_name, username, pw_hash.decode(), role)
        )

    @staticmethod
    def authenticate(username, password):
        row = db.query("SELECT * FROM users WHERE username = ?", (username,))
        if not row:
            return None
        stored = row[0]["password_hash"].encode()
        if bcrypt.checkpw(password.encode(), stored):
            return dict(row[0])
        return None

    @staticmethod
    def exists_any():
        row = db.query("SELECT COUNT(*) as cnt FROM users")
        return row[0]["cnt"] > 0

    @staticmethod
    def all(order_by="full_name"):
        return db.query(f"SELECT * FROM users ORDER BY {order_by}")

    @staticmethod
    def update(user_id, full_name, username, role, password=None):
        if password:
            pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            db.execute(
                "UPDATE users SET full_name=?, username=?, role=?, password_hash=? WHERE id=?",
                (full_name, username, role, pw_hash, user_id)
            )
        else:
            db.execute(
                "UPDATE users SET full_name=?, username=?, role=? WHERE id=?",
                (full_name, username, role, user_id)
            )

    @staticmethod
    def delete(user_id):
        db.execute("DELETE FROM users WHERE id = ?", (user_id,))


class Product:
    @staticmethod
    def all(order_by="name"):
        return db.query(f"SELECT * FROM products ORDER BY {order_by}")

    @staticmethod
    def search(term, order_by="name"):
        t = f"%{term}%"
        return db.query(
            f"SELECT * FROM products WHERE name LIKE ? OR code LIKE ? ORDER BY {order_by}",
            (t, t)
        )

    @staticmethod
    def by_category(category, order_by="name"):
        return db.query(
            f"SELECT * FROM products WHERE category = ? ORDER BY {order_by}",
            (category,)
        )

    @staticmethod
    def get_categories():
        rows = db.query(
            "SELECT DISTINCT category FROM products WHERE category IS NOT NULL AND category <> ''"
        )
        return [r["category"] for r in rows]

    @staticmethod
    def get(product_id):
        rows = db.query("SELECT * FROM products WHERE id = ?", (product_id,))
        return dict(rows[0]) if rows else None

    @staticmethod
    def create(code, name, category, cost_price, sell_price, type_, stock):
        db.execute(
            "INSERT INTO products (code, name, category, cost_price, sell_price, type, stock) "
            "VALUES (?,?,?,?,?,?,?)",
            (code or None, name, category, cost_price, sell_price, type_, stock)
        )

    @staticmethod
    def update(product_id, code, name, category, cost_price, sell_price, type_, stock):
        db.execute(
            "UPDATE products SET code=?, name=?, category=?, cost_price=?, sell_price=?, type=?, stock=? "
            "WHERE id=?",
            (code or None, name, category, cost_price, sell_price, type_, stock, product_id)
        )

    @staticmethod
    def delete(product_id):
        db.execute("DELETE FROM products WHERE id = ?", (product_id,))

    @staticmethod
    def adjust_stock(product_id, delta):
        db.execute(
            "UPDATE products SET stock = stock + ? WHERE id = ?",
            (delta, product_id)
        )


class Client:
    @staticmethod
    def all(order_by="full_name"):
        return db.query(f"SELECT * FROM clients ORDER BY {order_by}")

    @staticmethod
    def search(term, order_by="full_name"):
        t = f"%{term}%"
        return db.query(
            f"SELECT * FROM clients WHERE full_name LIKE ? OR cedula LIKE ? ORDER BY {order_by}",
            (t, t)
        )

    @staticmethod
    def get(client_id):
        rows = db.query("SELECT * FROM clients WHERE id = ?", (client_id,))
        return dict(rows[0]) if rows else None

    @staticmethod
    def create(full_name, cedula, contact, address, email):
        db.execute(
            "INSERT INTO clients (full_name, cedula, contact, address, email) VALUES (?,?,?,?,?)",
            (full_name, cedula or None, contact or None, address or None, email or None)
        )

    @staticmethod
    def update(client_id, full_name, cedula, contact, address, email):
        db.execute(
            "UPDATE clients SET full_name=?, cedula=?, contact=?, address=?, email=? WHERE id=?",
            (full_name, cedula or None, contact or None, address or None, email or None, client_id)
        )

    @staticmethod
    def delete(client_id):
        db.execute("DELETE FROM clients WHERE id = ?", (client_id,))


class Document:
    @staticmethod
    def create(type_, date, client_id, discount, total):
        cur = db.execute(
            "INSERT INTO documents (type, date, client_id, discount, total) VALUES (?,?,?,?,?)",
            (type_, date, client_id, discount, total)
        )
        return cur.lastrowid

    @staticmethod
    def get(doc_id):
        rows = db.query("SELECT * FROM documents WHERE id = ?", (doc_id,))
        return dict(rows[0]) if rows else None

    @staticmethod
    def all(order_by="date DESC"):
        return db.query(f"SELECT * FROM documents ORDER BY {order_by}")

    @staticmethod
    def delete(doc_id):
        db.execute("DELETE FROM documents WHERE id = ?", (doc_id,))


class DocumentItem:
    @staticmethod
    def add(document_id, product_id, qty, unit_price, subtotal):
        db.execute(
            "INSERT INTO document_items (document_id, product_id, qty, unit_price, subtotal) VALUES (?,?,?,?,?)",
            (document_id, product_id, qty, unit_price, subtotal)
        )

    @staticmethod
    def get_by_document(document_id):
        rows = db.query(
            "SELECT di.*, p.name FROM document_items di "
            "JOIN products p ON di.product_id = p.id "
            "WHERE document_id = ?",
            (document_id,)
        )
        return [dict(r) for r in rows]

    @staticmethod
    def delete_by_document(document_id):
        db.execute(
            "DELETE FROM document_items WHERE document_id = ?",
            (document_id,)
        )
