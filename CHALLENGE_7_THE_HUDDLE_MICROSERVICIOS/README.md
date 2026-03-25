# Microservicios E-commerce

Este proyecto implementa una arquitectura de microservicios para un sistema de e-commerce básico, compuesto por tres servicios principales: Usuarios, Inventario y Pedidos. Utiliza Docker Compose para la orquestación de contenedores y Flask como framework web para cada servicio.

## Arquitectura

La aplicación sigue una arquitectura de microservicios con un API Gateway que enruta las solicitudes a los servicios correspondientes:

- **API Gateway** (`main.py`): Punto de entrada único que distribuye las solicitudes a los microservicios
- **Servicio de Usuarios** (`servicios/usuarios/`): Maneja registro y autenticación de usuarios
- **Servicio de Inventario** (`servicios/inventario/`): Gestiona el catálogo de productos y stock
- **Servicio de Pedidos** (`servicios/pedidos/`): Procesa órdenes de compra

## Servicios

### Servicio de Usuarios (Puerto 5000)
- **POST /registro**: Registra un nuevo usuario
- **POST /login**: Autentica un usuario y devuelve un token JWT

### Servicio de Inventario (Puerto 5001)
- **POST /productos**: Crea un nuevo producto (requiere autenticación)
- **GET /productos**: Obtiene la lista de productos (requiere autenticación)
- **GET /productos/{id}**: Obtiene detalles de un producto específico
- **GET /productos/{id}/stock**: Consulta el stock de un producto
- **PUT /productos/{id}/stock**: Actualiza el stock de un producto

### Servicio de Pedidos (Puerto 5002)
- **POST /pedidos**: Crea una nueva orden (requiere autenticación)
- **GET /pedidos**: Obtiene las órdenes del usuario autenticado

## Requisitos

- Docker
- Docker Compose

## Instalación y Ejecución

1. Clona el repositorio:
   ```bash
   git clone <url-del-repositorio>
   cd challenge-7-the-huddle-microservicios
   ```

2. Construye y ejecuta los contenedores:
   ```bash
   docker compose up --build
   ```

3. La aplicación estará disponible en:
   - API Gateway: http://localhost:5003
   - Usuarios: http://localhost:5000
   - Inventario: http://localhost:5001
   - Pedidos: http://localhost:5002

## Uso

### Registro de Usuario
```bash
curl -X POST http://localhost:5003/registro \
  -H "Content-Type: application/json" \
  -d '{"nombre": "usuario", "password": "contraseña"}'
```

### Login
```bash
curl -X POST http://localhost:5003/login \
  -H "Content-Type: application/json" \
  -d '{"nombre": "usuario", "password": "contraseña"}'
```

### Crear Producto (requiere token)
```bash
curl -X POST http://localhost:5003/productos \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"nombre": "Producto A", "precio": 10.99, "cantidad": 100}'
```

### Crear Pedido (requiere token)
```bash
curl -X POST http://localhost:5003/pedidos \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"productos": [{"id": 1, "cantidad": 2}]}'
```

## Tecnologías Utilizadas

- **Python 3.9**: Lenguaje de programación
- **Flask**: Framework web para los microservicios
- **SQLite**: Base de datos para persistencia de datos
- **JWT**: Autenticación basada en tokens
- **Docker**: Contenedorización
- **Docker Compose**: Orquestación de contenedores

## Base de Datos

Cada servicio utiliza su propia base de datos SQLite:
- `usuarios.db`: Almacena información de usuarios
- `inventario.db`: Gestiona productos y stock
- `pedidos.db`: Registra órdenes y detalles

Las bases de datos se inicializan automáticamente al construir las imágenes Docker.

## Desarrollo

Para desarrollo local, puedes ejecutar cada servicio individualmente:

```bash
# Servicio de Usuarios
cd servicios/usuarios
pip install -r requirements.txt
python usuario.py

# Servicio de Inventario
cd servicios/inventario
pip install -r requirements.txt
python inventario.py

# Servicio de Pedidos
cd servicios/pedidos
pip install -r requirements.txt
python pedidos.py

# API Gateway con modo interactivo
python main.py cli
```

## Modo Interactivo

El API Gateway incluye un modo interactivo por terminal para facilitar las pruebas:

```bash
python main.py cli
```

Esto mostrará un menú para registrar usuarios, iniciar sesión, gestionar productos y pedidos sin necesidad de usar curl.

## Contribución

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -am 'Agrega nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

## Licencia

Este proyecto es parte del Challenge 7 - The Huddle.