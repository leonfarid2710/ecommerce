# ★ Star Up E-Commerce — Sistema Completo de Carrito de Compras

Proyecto académico para el Taller de Emprendedores (UAC - 7° Semestre).
Sistema full-stack con Flask, SQLite/PostgreSQL y frontend vanilla moderno.

---

## 1. ARQUITECTURA DEL SISTEMA

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENTE (Browser)                       │
│  HTML + CSS (Syne/DM Sans)  │  JavaScript Vanilla (fetch API)  │
└────────────────────────┬────────────────────────────────────────┘
                         │  HTTP REST (JSON)  /  Cookies de sesión
┌────────────────────────▼────────────────────────────────────────┐
│                     SERVIDOR  (Flask 3.x)                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────┐ │
│  │/api/users│  │/api/prod.│  │/api/cart │  │/api/checkout   │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └───────┬────────┘ │
│       └─────────────┴──────────────┴────────────────┘          │
│                        models/database.py                        │
└────────────────────────┬────────────────────────────────────────┘
                         │  SQLite (dev) / PostgreSQL (prod)
┌────────────────────────▼────────────────────────────────────────┐
│                       BASE DE DATOS                              │
│  clientes · proveedores · productos · ventas                    │
│  detalle_venta · carrito · items_carrito                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. MODELO DE BASE DE DATOS

### Diagrama lógico (relaciones)

```
PROVEEDORES ──< PRODUCTOS >── ITEMS_CARRITO >── CARRITO ──< CLIENTES
                    │                                           │
                    └─────< DETALLE_VENTA >──── VENTAS ────────┘
```

### Tablas y campos clave

| Tabla           | PK  | FKs                          | Descripción                    |
|-----------------|-----|------------------------------|--------------------------------|
| clientes        | id  | —                            | Usuarios del sistema           |
| proveedores     | id  | —                            | Proveedores de productos       |
| productos       | id  | proveedor_id → proveedores   | Catálogo con stock integrado   |
| ventas          | id  | cliente_id → clientes        | Cabecera de cada venta         |
| detalle_venta   | id  | venta_id, producto_id        | Líneas de cada venta           |
| carrito         | id  | cliente_id → clientes        | Sesión de carrito por usuario  |
| items_carrito   | id  | carrito_id, producto_id      | Ítems en el carrito activo     |

---

## 3. ESTRUCTURA DEL PROYECTO

```
ecommerce/
├── backend/
│   ├── app.py                  # Factory de la app Flask
│   ├── schema.sql              # DDL + seed data
│   ├── requirements.txt
│   ├── models/
│   │   ├── __init__.py
│   │   └── database.py         # Conexión SQLite / helpers
│   └── routes/
│       ├── __init__.py
│       ├── users.py            # /api/users
│       ├── products.py         # /api/products
│       ├── cart.py             # /api/cart
│       └── checkout.py         # /api/checkout
└── frontend/
    └── index.html              # SPA completo (HTML + CSS + JS)
```

---

## 4. API REST — ENDPOINTS

### Usuarios `/api/users`
| Método | Ruta        | Descripción               | Auth requerida |
|--------|-------------|---------------------------|----------------|
| POST   | /register   | Registro de cliente       | No             |
| POST   | /login      | Inicio de sesión          | No             |
| POST   | /logout     | Cierre de sesión          | Sí             |
| GET    | /me         | Datos del usuario actual  | Sí             |

### Productos `/api/products`
| Método | Ruta            | Descripción                        | Params         |
|--------|-----------------|------------------------------------|----------------|
| GET    | /               | Listado (búsqueda / filtro cat.)   | ?q= &category= |
| GET    | /categories     | Lista de categorías únicas         |                |
| GET    | /<id>           | Detalle de un producto             |                |

### Carrito `/api/cart`
| Método | Ruta            | Descripción                        | Auth requerida |
|--------|-----------------|------------------------------------|----------------|
| GET    | /               | Ver carrito del usuario            | Sí             |
| POST   | /add            | Agregar producto al carrito        | Sí             |
| PUT    | /item/<id>      | Actualizar cantidad de un ítem     | Sí             |
| DELETE | /item/<id>      | Eliminar ítem del carrito          | Sí             |
| DELETE | /clear          | Vaciar carrito completo            | Sí             |

### Checkout `/api/checkout`
| Método | Ruta     | Descripción                              | Auth requerida |
|--------|----------|------------------------------------------|----------------|
| POST   | /        | Procesar compra (valida stock, crea venta)| Sí            |
| GET    | /orders  | Historial de pedidos del usuario         | Sí             |

---

## 5. CÓMO EJECUTAR EL PROYECTO

### Requisitos
- Python 3.11+
- Navegador moderno

### Instalación

```bash
# 1. Clonar / descomprimir el proyecto
cd ecommerce/backend

# 2. Crear entorno virtual (recomendado)
python3 -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

# 3. Instalar dependencias
pip install flask

# 4. Ejecutar
python app.py
```

### Acceso
Abrir en el navegador: **http://localhost:5000**

> La base de datos `ecommerce.db` se crea automáticamente con datos de prueba
> en el primer inicio.

---

## 6. DESPLIEGUE EN PRODUCCIÓN

### Opción A — Render (recomendado, gratuito)

**Backend:**
1. Crear nuevo "Web Service" en render.com
2. Conectar repositorio GitHub
3. Build command: `pip install flask gunicorn`
4. Start command: `gunicorn --chdir backend app:create_app()`
5. Variables de entorno: `SECRET_KEY`, `DATABASE_URL`

**Base de datos PostgreSQL:**
1. En Render → "New PostgreSQL" (plan gratuito disponible)
2. Copiar la `Internal Database URL` como `DATABASE_URL`

> Para usar PostgreSQL en lugar de SQLite, reemplaza `sqlite3` por `psycopg2`
> en `models/database.py` y adapta las queries (cambiar `AUTOINCREMENT` → `SERIAL`).

**Frontend:**
- Está servido directamente por Flask como SPA.
- Opcionalmente separar a Vercel/Netlify si se convierte a React/Vue.

---

## 7. FLUJO COMPLETO DE COMPRA

```
1. Usuario visita /  →  carga productos desde /api/products/
2. Busca / filtra por categoría
3. Hace clic en "+" → si no está logueado → abre modal de login
4. Agrega producto → POST /api/cart/add (valida stock)
5. Abre carrito lateral → ve ítems, modifica cantidades
6. "Proceder al pago" → abre modal de checkout
7. Selecciona método de pago, confirma
8. POST /api/checkout/ → 
   a. Valida stock de todos los ítems
   b. Crea registro en `ventas`
   c. Crea registros en `detalle_venta`
   d. Decrementa `existencias` en `productos`
   e. Vacía `items_carrito`
9. Modal de éxito con número de pedido
10. Grid de productos se refresca (stock actualizado)
```

---

## 8. FUNCIONALIDADES IMPLEMENTADAS

- ✅ Registro y login de clientes (hash SHA-256)
- ✅ Sesión con Flask session (cookies httpOnly)
- ✅ Catálogo dinámico con búsqueda y filtro por categoría
- ✅ Carrito persistente en base de datos
- ✅ Validación de stock al agregar y al pagar
- ✅ Indicador visual de productos con poco stock / agotados
- ✅ Proceso de checkout con método de pago
- ✅ Actualización automática de existencias tras compra
- ✅ Historial de pedidos por usuario
- ✅ Frontend SPA responsive (mobile-first)
- ✅ Toast notifications
- ✅ Formateo de moneda MXN

---

## 9. SUGERENCIAS DE MEJORA

| Prioridad | Mejora                                                        |
|-----------|---------------------------------------------------------------|
| Alta      | Migrar hash a **bcrypt** o **argon2** para seguridad real     |
| Alta      | Agregar **JWT tokens** para APIs stateless                    |
| Media     | Integrar **Stripe / Conekta** para pagos reales               |
| Media     | WebSockets (Flask-SocketIO) para stock en tiempo real         |
| Media     | Panel de administración de productos/inventario               |
| Baja      | Sistema de reseñas y calificaciones de productos              |
| Baja      | Carrito de invitado (localStorage) con merge al iniciar sesión|
| Baja      | Notificaciones de email con Flask-Mail                        |
| Baja      | Rate limiting con Flask-Limiter                               |

---

## 10. CRÉDITOS

Proyecto: Taller de Emprendedores — Star Up S.A. de C.V.
Universidad Autónoma de Campeche, Facultad de Ingeniería
Ingeniería en Sistemas Computacionales — 7° Semestre Grupo B

Integrantes: Field Leon Jonathan Farid · Chuc Chi Jose Alfredo · Canul Carlos Daniel
#   e c o m m e r c e  
 