import sqlite3

def crear_tabla_pedidos():
    conexion = sqlite3.connect('pedidos.db')
    cursor = conexion.cursor()

    # Tabla de pedidos 
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pedidos (
            id TEXT PRIMARY KEY,
            usuario_id TEXT NOT NULL,
            fecha_pedido TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total REAL NOT NULL,
            estado TEXT DEFAULT 'pendiente',
            FOREIGN KEY (usuario_id) REFERENCES usuario (id) ON DELETE CASCADE
        )
    ''')

    # Tabla intermedia para saber qué productos hay en cada pedido
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pedido_detalle (
            id TEXT PRIMARY KEY,
            pedido_id TEXT NOT NULL,
            producto_id TEXT NOT NULL,
            cantidad INTEGER NOT NULL,
            precio_unitario REAL NOT NULL
        )
    ''')

    conexion.commit()
    conexion.close()
    print("Tablas de 'pedidos' y 'detalle' creadas exitosamente.")

if __name__ == "__main__":
    crear_tabla_pedidos()
