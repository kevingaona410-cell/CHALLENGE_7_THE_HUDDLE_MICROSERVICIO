from flask import Flask, request, jsonify
import sqlite3
import uuid
import jwt
import datetime
import requests
import os
from orders import crear_tabla_pedidos # Importa tu función de creación

app = Flask(__name__)

# Variables de entorno - Unificadas para consistencia con el auth-service
SECRET_KEY = os.getenv("SECRET_KEY", "clave_mega_secreto_y_es_123")
INVENTARIO_URL = os.getenv("INVENTARIO_URL", "http://localhost:5001")

def obtener_conn():
    """
    Obtiene una conexión a la base de datos pedidos.db
    """
    conn = sqlite3.connect("pedidos.db")
    conn.row_factory = sqlite3.Row
    return conn

def verificar_token():
    """
    Verifica el token JWT en el header Authorization.
    Devuelve el payload decodificado o error.
    """
    auth = request.headers.get("Authorization")

    if not auth or not auth.startswith("Bearer "):
        return None, jsonify({"error": "Token faltante"}), 401

    token = auth.split(" ")[1]

    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return decoded, None, None
    except jwt.ExpiredSignatureError:
        return None, jsonify({"error": "Token expirado"}), 401
    except jwt.InvalidTokenError:
        return None, jsonify({"error": "Token inválido"}), 403


@app.route("/pedidos", methods=["POST"])
def crear_pedido():
    """
    Crea un nuevo pedido con los items especificados.
    Valida stock y actualiza inventario.
    Requiere token de autenticación.
    """
    decoded, error, status = verificar_token()
    if error:
        return error, status

    data = request.get_json()

    if not data or "items" not in data:
        return jsonify({"error": "Debe enviar items"}), 400

    items = data["items"]
    if not isinstance(items, list) or len(items) == 0:
        return jsonify({"error": "Items inválidos"}), 400

    detalles = []
    total = 0

    # VALIDAR STOCK PRIMERO
    for item in items:
        producto_id = item.get("producto_id")
        cantidad = item.get("cantidad")

        if not producto_id or not cantidad:
            return jsonify({"error": "Item inválido"}), 400

        try:
            cantidad = int(cantidad)
        except:
            return jsonify({"error": "Cantidad inválida"}), 400

        # Llamar a inventario
        try:
            res = requests.get(
                f"{INVENTARIO_URL}/productos/{producto_id}",
                headers={"Authorization": request.headers.get("Authorization")}
            )

            if res.status_code != 200:
                return jsonify({"error": "Producto no encontrado"}), 404

            producto = res.json()["producto"]

        except:
            return jsonify({"error": "Error conectando con inventario"}), 500

        if producto["stock"] < cantidad:
            return jsonify({"error": f"Stock insuficiente para {producto_id}"}), 400

        precio = producto["precio"]
        subtotal = precio * cantidad

        total += subtotal

        detalles.append({
            "producto_id": producto_id,
            "cantidad": cantidad,
            "precio": precio
        })

    # CREAR PEDIDO
    pedido_id = str(uuid.uuid4())

    conn = obtener_conn()
    cursor = conn.cursor()

    # CORRECCIÓN: Se cambió decoded["id_usuario"] por decoded["user_id"]
    cursor.execute(
        "INSERT INTO pedidos (id, usuario_id, total, estado) VALUES (?, ?, ?, ?)",
        (pedido_id, decoded["user_id"], total, "pendiente")
    )

    # INSERTAR DETALLES
    for d in detalles:
        cursor.execute(
            "INSERT INTO pedido_detalle (id, pedido_id, producto_id, cantidad, precio_unitario) VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), pedido_id, d["producto_id"], d["cantidad"], d["precio"])
        )

    conn.commit()
    conn.close()

    # DESCONTAR STOCK
    for d in detalles:
        try:
            requests.put(
                f"{INVENTARIO_URL}/productos/{d['producto_id']}/stock",
                json={"cantidad": -d["cantidad"]},
                headers={"Authorization": request.headers.get("Authorization")}
            )
        except:
            pass  # simplificado para el challenge

    return jsonify({
        "mensaje": "Pedido creado",
        "pedido_id": pedido_id,
        "total": total
    }), 201


@app.route("/pedidos", methods=["GET"])
def listar_pedidos():
    """
    Lista los pedidos del usuario autenticado.
    """
    decoded, error, status = verificar_token()
    if error:
        return error, status

    conn = obtener_conn()
    cursor = conn.cursor()

    # CORRECCIÓN: Se cambió decoded["id_usuario"] por decoded["user_id"]
    cursor.execute("SELECT * FROM pedidos WHERE usuario_id = ?", (decoded["user_id"],))
    pedidos = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return jsonify({"pedidos": pedidos})

if __name__ == "__main__":
    crear_tabla_pedidos() # Asegura las tablas antes de iniciar Flask
    app.run(host="0.0.0.0", port=5002)