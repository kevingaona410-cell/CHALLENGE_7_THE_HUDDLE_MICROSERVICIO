import sqlite3

def iniciar_db():
    """
    Inicializa la base de datos creando la tabla stock si no existe.
    """
    conn = sqlite3.connect("inventario.db")
    cursor = conn.cursor()
    
    cursor.execute("""
       CREATE TABLE IF NOT EXISTS stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            precio REAL NOT NULL,
            stock INTEGER DEFAULT 0,
            tipo TEXT NOT NULL
            )""")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    iniciar_db()