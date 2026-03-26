from flask import Flask, request, jsonify
import sqlite3
import jwt
from stock import iniciar_db 
app = Flask(__name__)
SECRET_KEY = "clave_mega_secreto_y_es_123"

def obtener_conn():
    """
    Obtiene una conexión a la base de datos inventario.db
    """
    conn = sqlite3.connect("inventario.db")
    conn.row_factory = sqlite3.Row
    return conn

def verificar_token():
    """
    Verifica el token JWT en el header Authorization.
    Devuelve el payload decodificado o error.
    """
    auth = request.headers.get("Authorization")

    if not auth or not auth.startswith("Bearer "):
        return None, jsonify({"error": "Token incorrecto o faltante"}), 401

    token = auth.split("Bearer ")[1]

    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        
    except jwt.ExpiredSignatureError:
        return None, jsonify({"error": "Token expirado"}), 401
    
    except jwt.InvalidTokenError:
        return None, jsonify({"error": "Token inválido"}), 403

    return decoded, None, None

@app.route("/productos", methods=["POST"])
def crear_productos():
    """
    Crea un nuevo producto en el inventario.
    Requiere token de autenticación.
    """
    decoded, error_response, status_code = verificar_token()
    
    if error_response:
        return error_response, status_code

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON inválido o body vacío"}), 400

    nombre = data.get("nombre")
    precio = data.get("precio")
    stock = data.get("stock")
    tipo = data.get("tipo")

    errores = []
    if not nombre or not isinstance(nombre, str):
        errores.append("nombre es obligatorio y debe ser texto")

    if precio is None:
        errores.append("precio es obligatorio")

    else:
        try:
            precio = float(precio)
            if precio < 0:
                errores.append("precio debe ser un número positivo")

        except (ValueError, TypeError):
            errores.append("precio debe ser un número")
    if stock is None:
        errores.append("stock es obligatorio")

    else:
        try:
            stock = int(stock)
            if stock < 0:
                errores.append("stock debe ser un entero no negativo")

        except (ValueError, TypeError):
            errores.append("stock debe ser un entero")

    if not tipo or not isinstance(tipo, str):
        errores.append("tipo es obligatorio y debe ser texto")

    if errores:
        return jsonify({"errores": errores}), 400

    conn = obtener_conn()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO stock (nombre, precio, stock, tipo) VALUES (?, ?, ?, ?)",
        (nombre, precio, stock, tipo),
    )
    conn.commit()
    insert_id = cursor.lastrowid
    cursor.execute("SELECT * FROM stock WHERE id = ?", (insert_id,))
    row = cursor.fetchone()
    conn.close()

    producto = dict(row) if row else {
        "id": insert_id,
        "nombre": nombre,
        "precio": precio,
        "stock": stock,
        "tipo": tipo,
    }

    return jsonify({"usuario": decoded, "producto": producto}), 201


@app.route("/productos", methods=["GET"])
def obtener_productos():
    """
    Obtiene la lista de todos los productos.
    Requiere token de autenticación.
    """
    decoded, error_response, status_code = verificar_token()
    if error_response:
        return error_response, status_code

    # listar productos de stock
    conn = obtener_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM stock")
    rows = cursor.fetchall()
    conn.close()

    productos = [dict(row) for row in rows]
    return jsonify({"usuario": decoded, "products": productos}), 200


@app.route("/productos/<int:id>", methods=["GET"])
def obtener_producto(id):
    """
    Obtiene un producto específico por ID.
    Requiere token de autenticación.
    """
    decoded, error_response, status_code = verificar_token()
    if error_response:
        return error_response, status_code

    conn = obtener_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM stock WHERE id = ?", (id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify({"error": "Producto no encontrado"}), 404

    producto = dict(row)
    return jsonify({"usuario": decoded, "producto": producto}), 200


@app.route("/productos/<int:id>/stock", methods=["GET"])
def obtener_stock(id):
    """
    Obtiene el stock de un producto específico.
    Requiere token de autenticación.
    """
    decoded, error_response, status_code = verificar_token()
    if error_response:
        return error_response, status_code

    conn = obtener_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, stock FROM stock WHERE id = ?", (id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return jsonify({"error": "Producto no encontrado"}), 404

    stock_info = dict(row)
    return jsonify({"usuario": decoded, "stock": stock_info}), 200


@app.route("/productos/<int:id>/stock", methods=["PUT"])
def actualizar_stock(id):
    """
    Actualiza el stock de un producto (suma o resta cantidad).
    Requiere token de autenticación.
    """
    decoded, error_response, status_code = verificar_token()
    if error_response:
        return error_response, status_code

    data = request.get_json(silent=True)
    if not data or "cantidad" not in data:
        return jsonify({"error": "JSON inválido o falta 'cantidad'"}), 400

    cantidad = data.get("cantidad")
    try:
        cantidad = int(cantidad)
    except (ValueError, TypeError):
        return jsonify({"error": "cantidad debe ser un entero"}), 400

    conn = obtener_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT stock FROM stock WHERE id = ?", (id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return jsonify({"error": "Producto no encontrado"}), 404

    stock_actual = row["stock"]
    nuevo_stock = stock_actual + cantidad  

    if nuevo_stock < 0:
        conn.close()
        return jsonify({"error": "Stock insuficiente"}), 400

    cursor.execute("UPDATE stock SET stock = ? WHERE id = ?", (nuevo_stock, id))
    conn.commit()
    conn.close()

    return jsonify({"usuario": decoded, "id": id, "nuevo_stock": nuevo_stock}), 200

if __name__ == "__main__":
    iniciar_db() 
    app.run(host='0.0.0.0', debug=True, port=5001)