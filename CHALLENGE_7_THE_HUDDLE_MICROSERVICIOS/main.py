import requests
import os
import logging
from pybreaker import CircuitBreaker, CircuitBreakerError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# --- CONFIGURACIÓN DE LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(name)s] - %(levelname)s: %(message)s'
)
logger = logging.getLogger("PenguinShop_Client")

# --- VARIABLES DE ENTORNO ---
MODO_DOCKER = os.getenv("DOCKER_ENV")
URL_AUTH = "http://auth-service:5000" if MODO_DOCKER else "http://localhost:5000"
URL_INVENTARIO = "http://inventario-service:5001" if MODO_DOCKER else "http://localhost:5001"
URL_PEDIDOS = "http://servicio-pedidos:5002" if MODO_DOCKER else "http://localhost:5002"

# --- CONFIGURACIÓN DE CIRCUIT BREAKERS ---
# Falla tras 5 errores, espera 30 seg para reintentar (estado semi-abierto)
breaker_auth = CircuitBreaker(fail_max=5, reset_timeout=30, name="AUTH_CB")
breaker_inv = CircuitBreaker(fail_max=5, reset_timeout=30, name="INV_CB")
breaker_ped = CircuitBreaker(fail_max=5, reset_timeout=30, name="PED_CB")

# --- DECORADOR DE RETRY ---
# Reintenta 3 veces con espera exponencial (1s, 2s, 4s...) solo si hay error de conexión
retry_config = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(requests.exceptions.RequestException),
    before_sleep=lambda retry_state: logger.info(f"🔄 Reintentando conexión... Intento {retry_state.attempt_number}")
)

# --- FUNCIÓN NÚCLEO DE RESILIENCIA ---

def peticion_segura(metodo, url, cb, **kwargs):
    """
    Encapsula la lógica de Circuit Breaker y Retry.
    Primero intenta el Retry. Si falla 3 veces, el CB cuenta 1 fallo.
    """
    @retry_config
    def ejecutar_con_reintento():
        return cb.call(metodo, url, **kwargs)
    
    try:
        return ejecutar_con_reintento()
    except CircuitBreakerError:
        logger.error(f"🚨 Circuito {cb.name} ABIERTO. Abortando petición a {url}")
        raise Exception("Servicio temporalmente fuera de servicio (Circuit Breaker)")
    except Exception as e:
        # Aquí llegan los errores después de agotar los 3 reintentos
        raise e

# --- FUNCIONES DE SERVICIO ---

def registrar():
    print("\n--- Registro ---")
    nombre = input("Nombre: ")
    pw = input("Contraseña: ")
    try:
        res = peticion_segura(requests.post, f"{URL_AUTH}/registro", breaker_auth, 
                             json={"nombre": nombre, "password": pw}, timeout=5)
        if res.status_code == 201:
            print("✓ Usuario creado correctamente")
        else:
            print(f"❌ Error: {res.json().get('error')}")
    except Exception as e:
        print(f"🚨 Error: {e}")

def iniciar_sesion():
    print("\n--- Inicio de sesión ---")
    nombre = input("Nombre: ")
    pw = input("Contraseña: ")
    try:
        res = peticion_segura(requests.post, f"{URL_AUTH}/login", breaker_auth, 
                             json={"nombre": nombre, "password": pw}, timeout=5)
        if res.status_code == 200:
            datos = res.json()
            print(f"✓ {datos.get('mensaje')}")
            return datos.get("token")
        else:
            print(f"❌ Error: {res.json().get('error')}")
    except Exception as e:
        print(f"🚨 Error de conexión en login: {e}")
    return None

def ver_productos(token):
    print("\n--- Catálogo de Productos ---")
    headers = {"Authorization": f"Bearer {token}"}
    try:
        res = peticion_segura(requests.get, f"{URL_INVENTARIO}/productos", breaker_inv, 
                             headers=headers, timeout=5)
        if res.status_code == 200:
            productos = res.json().get("products", [])
            print(f"{'ID':<4} | {'Nombre':<20} | {'Precio':<10} | {'Stock':<8}")
            print("-" * 50)
            for p in productos:
                print(f"{p['id']:<4} | {p['nombre']:<20} | {p['precio']:<10} | {p['stock']:<8}")
        else:
            print(f"❌ Error: {res.status_code}")
    except Exception as e:
        print(f"🚨 Catálogo no disponible: {e}")

def realizar_pedido(token):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        res_inv = peticion_segura(requests.get, f"{URL_INVENTARIO}/productos", breaker_inv, 
                                 headers=headers, timeout=5)
        productos = res_inv.json().get("products", [])
        for p in productos:
            print(f"ID: {p['id']} | {p['nombre']} | Stock: {p['stock']}")
    except Exception as e:
        print(f"🚨 No se puede acceder al inventario: {e}")
        return

    elementos = []
    while True:
        id_p = input("ID (o 'fin'): ")
        if id_p.lower() == 'fin': break
        cant = input("Cantidad: ")
        elementos.append({"producto_id": id_p, "cantidad": int(cant)})

    if elementos:
        try:
            res = peticion_segura(requests.post, f"{URL_PEDIDOS}/pedidos", breaker_ped, 
                                 json={"items": elementos}, headers=headers, timeout=10)
            if res.status_code == 201:
                print(f"✓ Pedido ID {res.json().get('pedido_id')} creado.")
            else:
                print(f"❌ Error: {res.json().get('error')}")
        except Exception as e:
            print(f"🚨 Servicio de pedidos caído: {e}")

def ver_mis_pedidos(token):
    print("\n── Mis Órdenes ──")
    headers = {"Authorization": f"Bearer {token}"}
    try:
        res = peticion_segura(requests.get, f"{URL_PEDIDOS}/pedidos", breaker_ped, 
                             headers=headers, timeout=5)
        if res.status_code == 200:
            for ped in res.json().get("pedidos", []):
                print(f"ID: {ped['id'][:8]}... | Total: ${ped['total']} | Estado: {ped['estado']}")
    except Exception as e:
        print(f"🚨 Error al recuperar pedidos: {e}")

# --- MENÚS ---

def menu_usuario(token):
    while True:
        print("\n=== Gestión de Penguin Shop ===")
        print("1. Catálogo | 2. Agregar Producto | 3. Comprar | 4. Mis Pedidos | 5. Salir")
        op = input("\nSeleccioná: ")
        if op == "1": ver_productos(token)
        elif op == "3": realizar_pedido(token)
        elif op == "4": ver_mis_pedidos(token)
        elif op == "5": break

def menu_principal():
    while True:
        print("\n=== Penguin Shop ===")
        print("1. Registrarse | 2. Login | 3. Salir")
        op = input("\nSeleccioná: ")
        if op == "1": registrar()
        elif op == "2":
            tk = iniciar_sesion()
            if tk: menu_usuario(tk)
        elif op == "3": break

if __name__ == "__main__":
    menu_principal()