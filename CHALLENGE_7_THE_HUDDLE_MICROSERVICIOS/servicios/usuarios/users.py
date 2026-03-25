import sqlite3

def obtener_conn():
    conn = sqlite3.connect("usuarios.db")
    conn.row_factory = sqlite3.Row 
    return conn

def iniciar_db():
    conn = obtener_conn()
    cursor = conn.cursor()
    cursor.execute("""
       CREATE TABLE IF NOT EXISTS usuario (
            id TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            password TEXT NOT NULL)""")
    conn.commit()
    conn.close()