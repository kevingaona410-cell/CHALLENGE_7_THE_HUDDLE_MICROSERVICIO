# Cliente principal para la tienda Penguin Shop
import requests
import os

# Detectamos si estamos dentro de la red de Docker o en Windows local
DOCKER_MODE = os.getenv("DOCKER_ENV")

AUTH_URL = "http://auth-service:5000" if DOCKER_MODE else "http://localhost:5000"
INVENTARIO_URL = "http://inventario-service:5001" if DOCKER_MODE else "http://localhost:5001"
PEDIDOS_URL = "http://servicio-pedidos:5002" if DOCKER_MODE else "http://localhost:5002"

def registrar():
    """
    Registra un nuevo usuario en el sistema.
    """
    print("\n--- Registro ---")
    nombre   = input("Nombre: ")
    password = input("Contraseña: ")

    res = requests.post(f"{AUTH_URL}/registro", json={
        "nombre": nombre,
        "password": password
    })

    if res.status_code == 201:
        print("Usuario creado correctamente")
    else:
        print(f"Error: {res.json().get('error')}")


def iniciar_sesion():
    """
    Inicia sesión de un usuario y devuelve el token si es exitoso.
    """
    print("\n--- Inicio de sesión ---")
    nombre   = input("Nombre: ")
    password = input("Contraseña: ")

    res = requests.post(f"{AUTH_URL}/login", json={
        "nombre": nombre,
        "password": password
    })

    if res.status_code == 200:
        data  = res.json()
        token = data.get("token")
        print(data.get('mensaje'))
        print(f"  Token: {token}")
        return token
    else:
        print(f"Error: {res.json().get('error')}")
        return None

def menu_usuario(token):
    """
    Menú principal para usuarios autenticados.
    """
    while True:
        print("\n=== Gestión de Penguin Shop ===")
        print("1. Ver Catálogo de Productos")
        print("2. Agregar Producto al Inventario")
        print("3. REALIZAR COMPRA (Pedido)")
        print("4. Ver Mis Pedidos")
        print("5. Cerrar Sesión")
        
        op = input("\nSeleccioná: ").strip()
        
        if op == "1":
            ver_productos(token) 
        elif op == "2":
            agregar_producto(token)
        elif op == "3":
            realizar_pedido(token)
        elif op == "4":
            ver_mis_pedidos(token)
        elif op == "5":
            break
def menu_principal():
    """
    Menú principal de la aplicación.
    """
    while True:
        print("\n=== Penguin Shop ===")
        print("1. Registrarse")
        print("2. Iniciar sesión")
        print("3. Salir")
        
        opcion = input("\nSeleccioná: ")
        if opcion == "1":
            registrar()
        elif opcion == "2":
            token = iniciar_sesion()
            if token:
                menu_usuario(token)
        elif opcion == "3":
            break
            
def agregar_producto(token):
    """
    Agrega un nuevo producto al inventario.
    """
    print("\n--- Registrar Nuevo Producto ---")
    nombre = input("Nombre del producto: ")
    precio = input("Precio: ")
    stock  = input("Cantidad inicial: ")
    tipo   = input("Categoría (ej. Ropa, Alimento): ")

    # Construimos el Header con el Token
    headers = {"Authorization": f"Bearer {token}"}
    
    data = {
        "nombre": nombre,
        "precio": precio,
        "stock": stock,
        "tipo": tipo
    }

    try:
        res = requests.post(f"{INVENTARIO_URL}/productos", json=data, headers=headers)
        
        if res.status_code == 201:
            print("Producto registrado con éxito en el inventario.")
        else:
            print(f"Error ({res.status_code}): {res.json().get('errores' or 'error')}")
            
    except requests.exceptions.ConnectionError:
        print("Error de conexión: ¿Está el servicio de inventario activo en Docker?")
        
def ver_productos(token):
    """
    Muestra el catálogo de productos disponibles.
    """
    print("\n--- Catálogo de Productos ---")
    
    # El "pasaporte" para entrar al inventario
    headers = {"Authorization": f"Bearer {token}"}

    try:
        res = requests.get(f"{INVENTARIO_URL}/productos", headers=headers)

        if res.status_code == 200:
            data = res.json()
            productos = data.get("products", [])
            
            if not productos:
                print("El inventario está vacío.")
            else:
                # Imprimimos una tabla simple para Jopara Studios
                print(f"{'ID':<4} | {'Nombre':<20} | {'Precio':<10} | {'Stock':<8} | {'Tipo'}")
                print("-" * 60)
                for p in productos:
                    print(f"{p['id']:<4} | {p['nombre']:<20} | {p['precio']:<10} | {p['stock']:<8} | {p['tipo']}")
        else:
            print(f"Error ({res.status_code}): {res.json().get('error')}")

    except requests.exceptions.ConnectionError:
        print("Error: No se pudo conectar con el servicio de inventario.")

def realizar_pedido(token):
    """
    Permite al usuario realizar un pedido seleccionando productos y cantidades.
    """
    headers = {"Authorization": f"Bearer {token}"}
    
    # Primero mostramos qué hay para comprar
    print("\n--- Productos Disponibles ---")
    try:
        res_inv = requests.get(f"{INVENTARIO_URL}/productos", headers=headers)
        if res_inv.status_code != 200:
            print("No se pudo obtener el inventario.")
            return
        
        productos = res_inv.json().get("products", [])
        for p in productos:
            print(f"ID: {p['id']} | {p['nombre']} | Precio: {p['precio']} | Stock: {p['stock']}")
    except:
        print("Error de conexión con inventario.")
        return

    # Proceso de armado de "carrito"
    items = []
    print("\n(Escribí 'fin' en el ID para terminar de agregar items)")
    while True:
        prod_id = input("ID del producto a comprar: ")
        if prod_id.lower() == 'fin': break
        
        cantidad = input(f"Cantidad para el ID {prod_id}: ")
        try:
            items.append({"producto_id": prod_id, "cantidad": int(cantidad)})
        except ValueError:
            print("Cantidad inválida.")

    if not items:
        print("Pedido cancelado: carrito vacío.")
        return

    # Envío al servicio de pedidos
    try:
        res = requests.post(f"{PEDIDOS_URL}/pedidos", json={"items": items}, headers=headers)
        # En lugar de print(f"❌ Error: {res.json().get('error')}")
        if res.status_code != 201:
            try:
                msg = res.json().get('error', 'Error desconocido')
            except:
                msg = "El servidor devolvió un error interno (no es JSON)"
            print(f"Error al crear pedido: {msg}")
    except requests.exceptions.ConnectionError:
        print("El servicio de pedidos no responde.")

def ver_mis_pedidos(token):
    """
    Muestra los pedidos realizados por el usuario.
    """
    print("\n── Mis Órdenes ──")
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        res = requests.get(f"{PEDIDOS_URL}/pedidos", headers=headers)
        if res.status_code == 200:
            pedidos = res.json().get("pedidos", [])
            if not pedidos:
                print("No tenés pedidos registrados.")
            else:
                for ped in pedidos:
                    print(f"ID Pedido: {ped['id'][:8]}... | Total: ${ped['total']} | Estado: {ped['estado']}")
        else:
            print(f"Error: {res.json().get('error')}")
    except Exception as e:
        print(f"Error de conexión: {e}")
if __name__ == "__main__":
    menu_principal()