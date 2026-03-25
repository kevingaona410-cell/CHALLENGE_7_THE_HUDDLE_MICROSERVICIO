import sqlite3

def iniciar_db():
    conn = sqlite3.connect("inventario.db")
    cursor = conn.cursor()
    
    # Usamos INTEGER PRIMARY KEY para que lastrowid funcione correctamente
    # Añadimos 'tipo' y cambiamos 'cantidad' por 'stock' para ser coherentes
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