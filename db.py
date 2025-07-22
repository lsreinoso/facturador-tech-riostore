# db.py
import sqlite3
from cryptography.fernet import Fernet
import os
from paths import rel_to_data  # Importa la función centralizada

DB_PATH = rel_to_data("riostore.db")
KEY_PATH = rel_to_data("key.key")

class Database:
    def __init__(self, db_path=DB_PATH, key_path=KEY_PATH):
        # Ya no necesitas crear la carpeta aquí, rel_to_data lo garantiza
        self.key = self._load_or_create_key(key_path)
        self.conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _load_or_create_key(self, path):
        if os.path.exists(path):
            return open(path, "rb").read()
        else:
            key = Fernet.generate_key()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(key)
            return key

    def _create_tables(self):
        c = self.conn.cursor()

        # Usuarios
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL
            );
        """)

        # Productos
        c.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT,
                name TEXT NOT NULL,
                category TEXT,
                cost_price REAL,
                sell_price REAL,
                type TEXT CHECK(type IN ('Producto','Servicio')),
                stock INTEGER DEFAULT 0
            );
        """)

        # Clientes (con migración de versiones anteriores)
        c.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                cedula TEXT UNIQUE,
                contact TEXT,
                address TEXT,
                email TEXT
            );
        """)
        # migrar si faltan columnas en una versión anterior
        existing_cols = [row["name"] for row in c.execute("PRAGMA table_info(clients)").fetchall()]
        if "address" not in existing_cols:
            c.execute("ALTER TABLE clients ADD COLUMN address TEXT;")
        if "email" not in existing_cols:
            c.execute("ALTER TABLE clients ADD COLUMN email TEXT;")

        # Documentos (proformas y notas)
        c.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT CHECK(type IN ('PROFORMA','NOTA')) NOT NULL,
                date TEXT NOT NULL,
                client_id INTEGER NOT NULL,
                discount REAL DEFAULT 0,
                total REAL NOT NULL,
                FOREIGN KEY(client_id) REFERENCES clients(id)
            );
        """)

        # Ítems de documento
        c.execute("""
            CREATE TABLE IF NOT EXISTS document_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                qty INTEGER NOT NULL,
                unit_price REAL NOT NULL,
                subtotal REAL NOT NULL,
                FOREIGN KEY(document_id) REFERENCES documents(id),
                FOREIGN KEY(product_id) REFERENCES products(id)
            );
        """)

        self.conn.commit()

    def execute(self, sql, params=()):
        cur = self.conn.cursor()
        cur.execute(sql, params)
        self.conn.commit()
        return cur

    def query(self, sql, params=()):
        cur = self.conn.cursor()
        cur.execute(sql, params)
        return cur.fetchall()
