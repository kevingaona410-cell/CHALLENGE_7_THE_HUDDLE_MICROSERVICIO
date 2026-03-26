from flask import Flask, request, jsonify
import sqlite3
import uuid
import jwt
import datetime
import requests
import os
import logging
from pybreaker import CircuitBreaker
from orders import crear_tabla_pedidos

# Configurar logging en español
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(name)s] - %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Variables de entorno
CLAVE_SECRETA = os.getenv("SECRET_KEY", "clave_mega_secreto_y_es_123")
URL_INVENTARIO = os.getenv("INVENTARIO_URL", "http://localhost:5001")

# Disyuntor de circuito para el servicio de inventario
disyuntor_inventario = CircuitBreaker(fail_max=5, reset_timeout=30, name="inventario")

def obtener_conexion():
    """
    Obtiene una conexión a la base de datos pedidos.db
    """
    conexion = sqlite3.connect("pedidos.db")
    conexion.row_factory = sqlite3.Row
    return conexion


def verificar_token():
    """
    Verifica el token JWT en el header Authorization.
    Devuelve el payload decodificado o error.
    """
    autenticacion = request.headers.get("Authorization")

    if not autenticacion or not autenticacion.startswith("Bearer "):
        return None, jsonify({"error": "Token faltante"}), 401

    token = autenticacion.split(" ")[1]

    try:
        decodificado = jwt.decode(token, CLAVE_SECRETA, algorithms=["HS256"])
        return decodificado, None, None
    except jwt.ExpiredSignatureError:
        return None, jsonify({"error": "Token expirado"}), 401
    except jwt.InvalidTokenError:
        return None, jsonify({"error": "Token inválido"}), 403


@app.route("/pedidos", methods=["POST"])
def crear_pedido():
    """
    Crea un nuevo pedido con los elementos especificados.
    Valida stock y actualiza inventario.
    Requiere token de autenticación.
    """
    decodificado, error, estado = verificar_token()
    if error:
        return error, estado

    datos = request.get_json()

    if not datos or "items" not in datos:
        return jsonify({"error": "Debe enviar elementos"}), 400

    elementos = datos["items"]
    if not isinstance(elementos, list) or len(elementos) == 0:
        return jsonify({"error": "Elementos inválidos"}), 400

    detalles = []
    total = 0

    # VALIDAR STOCK PRIMERO
    for elemento in elementos:
        id_producto = elemento.get("producto_id")
        cantidad = elemento.get("cantidad")

        if not id_producto or not cantidad:
            return jsonify({"error": "Elemento inválido"}), 400

        try:
            cantidad = int(cantidad)
        except:
            return jsonify({"error": "Cantidad inválida"}), 400

        # Llamar a inventario con disyuntor
        try:
            logger.info(f"Validando stock para producto {id_producto}")
            respuesta = disyuntor_inventario.call(
                requests.get,
                f"{URL_INVENTARIO}/productos/{id_producto}",
                headers={"Authorization": request.headers.get("Authorization")},
                timeout=5
            )

            if respuesta.status_code != 200:
                logger.warning(f"Producto {id_producto} no encontrado en inventario")
                return jsonify({"error": "Producto no encontrado"}), 404

            producto = respuesta.json()["producto"]
            logger.info(f"Producto {id_producto} validado: stock={producto['stock']}")

        except requests.RequestException as e:
            logger.error(f"Error conectando con inventario: {str(e)}")
            return jsonify({"error": "Error conectando con inventario"}), 500

        if producto["stock"] < cantidad:
            logger.warning(f"Stock insuficiente para {id_producto}: hay {producto['stock']}, requiere {cantidad}")
            return jsonify({"error": f"Stock insuficiente para {id_producto}"}), 400

        precio = producto["precio"]
        subtotal = precio * cantidad

        total += subtotal

        detalles.append({
            "producto_id": id_producto,
            "cantidad": cantidad,
            "precio": precio
        })

    # CREAR PEDIDO
    id_pedido = str(uuid.uuid4())

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    cursor.execute(
        "INSERT INTO pedidos (id, usuario_id, total, estado) VALUES (?, ?, ?, ?)",
        (id_pedido, decodificado["user_id"], total, "pendiente")
    )

    # INSERTAR DETALLES
    for d in detalles:
        cursor.execute(
            "INSERT INTO pedido_detalle (id, pedido_id, producto_id, cantidad, precio_unitario) VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), id_pedido, d["producto_id"], d["cantidad"], d["precio"])
        )

    conexion.commit()
    conexion.close()

    # DESCONTAR STOCK - Con disyuntor
    for d in detalles:
        try:
            logger.info(f"Descontando {d['cantidad']} unidades del producto {d['producto_id']}")
            respuesta = disyuntor_inventario.call(
                requests.put,
                f"{URL_INVENTARIO}/productos/{d['producto_id']}/stock",
                json={"cantidad": -d["cantidad"]},
                headers={"Authorization": request.headers.get("Authorization")},
                timeout=5
            )
            if respuesta.status_code == 200:
                logger.info(f"Stock descontado exitosamente para producto {d['producto_id']}")
            else:
                logger.warning(f"Fallo al descontar stock para {d['producto_id']}: {respuesta.status_code}")
        except requests.RequestException as e:
            logger.error(f"Error descont stock de {d['producto_id']}: {str(e)}")

    return jsonify({
        "mensaje": "Pedido creado",
        "pedido_id": id_pedido,
        "total": total
    }), 201


@app.route("/pedidos", methods=["GET"])
def listar_pedidos():
    """
    Lista los pedidos del usuario autenticado.
    """
    decodificado, error, estado = verificar_token()
    if error:
        return error, estado

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    cursor.execute("SELECT * FROM pedidos WHERE usuario_id = ?", (decodificado["user_id"],))
    pedidos = [dict(row) for row in cursor.fetchall()]

    conexion.close()

    return jsonify({"pedidos": pedidos})

if __name__ == "__main__":
    crear_tabla_pedidos()
    app.run(host="0.0.0.0", port=5002)