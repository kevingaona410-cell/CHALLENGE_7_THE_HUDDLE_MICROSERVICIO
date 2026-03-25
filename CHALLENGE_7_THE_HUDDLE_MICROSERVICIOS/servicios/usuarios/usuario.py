import os
import uuid
import hashlib
import jwt
from flask import Flask, jsonify, request
from users import obtener_conn, iniciar_db

app = Flask(__name__)

SECRET = os.environ.get("JWT_SECRET", "clave_mega_secreto_y_es_123")


def hash_password(password):
    """
    Hashea la contraseña usando SHA256.
    """
    return hashlib.sha256(password.encode()).hexdigest()


# ── Rutas ──────────────────────────────────────────────────────────

@app.route("/registro", methods=["POST"])
def registro():
    """
    Registra un nuevo usuario.
    """
    data     = request.get_json()
    nombre   = data.get("nombre")
    password = data.get("password")

    if not nombre or not password:
        return jsonify({"error": "nombre y password son requeridos"}), 400

    conn   = obtener_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM usuario WHERE nombre = ?", (nombre,))
    if cursor.fetchone():
        conn.close()
        return jsonify({"error": "El nombre de usuario ya existe"}), 409

    user_id = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO usuario (id, nombre, password) VALUES (?, ?, ?)",
        (user_id, nombre, hash_password(password))
    )
    conn.commit()
    conn.close()

    return jsonify({"mensaje": "Usuario registrado con éxito", "id_usuario": user_id}), 201


@app.route("/login", methods=["POST"])
def login():
    """
    Inicia sesión y devuelve un token JWT si las credenciales son correctas.
    """
    data     = request.get_json()
    nombre   = data.get("nombre")
    password = data.get("password")

    if not nombre or not password:
        return jsonify({"error": "nombre y password son requeridos"}), 400

    conn   = obtener_conn()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, nombre FROM usuario WHERE nombre = ? AND password = ?",
        (nombre, hash_password(password))
    )
    usuario = cursor.fetchone()
    conn.close()

    if not usuario:
        return jsonify({"error": "Credenciales inválidas"}), 401

    token = jwt.encode(
        {"user_id": usuario["id"], "nombre": usuario["nombre"]},
        SECRET,
        algorithm="HS256"
    )

    return jsonify({
        "mensaje": f"Bienvenido, {usuario['nombre']}",
        "token": token
    })


# ── Inicio ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    iniciar_db()
    app.run(host="0.0.0.0", port=5000, debug=True)