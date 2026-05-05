"""
STAR UP E-COMMERCE — run.py
Archivo unico. Ejecutar: python run.py
Produccion en Render: gunicorn wsgi:app
"""

import os
import re
import sys
import hashlib
from flask import Flask, request, jsonify, session, send_from_directory, Response, redirect

# ─────────────────────────────────────────────────────────────────────────────
#  RUTAS
# ─────────────────────────────────────────────────────────────────────────────
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, '..', 'frontend')

# Disco persistente en Render (/var/data) o local
if os.path.isdir('/var/data'):
    DB_PATH = '/var/data/ecommerce.db'
else:
    DB_PATH = os.path.join(BASE_DIR, 'ecommerce.db')

# ─────────────────────────────────────────────────────────────────────────────
#  FLASK
# ─────────────────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'starUp_dev_secret_2025!')

if os.environ.get('RENDER'):
    app.config['SESSION_COOKIE_SECURE']   = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'None'
    app.config['SESSION_COOKIE_HTTPONLY'] = True

# ─────────────────────────────────────────────────────────────────────────────
#  BASE DE DATOS — SQLite puro (funciona en cualquier version de Python)
# ─────────────────────────────────────────────────────────────────────────────
def get_db():
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    conn.execute('PRAGMA journal_mode = WAL')
    return conn

def fetchone(conn, sql, params=()):
    r = conn.execute(sql, params).fetchone()
    return dict(r) if r else None

def fetchall(conn, sql, params=()):
    return [dict(r) for r in conn.execute(sql, params).fetchall()]

def mutate(conn, sql, params=()):
    """INSERT / UPDATE / DELETE — devuelve el cursor."""
    return conn.execute(sql, params)

# ─────────────────────────────────────────────────────────────────────────────
#  INIT DB
# ─────────────────────────────────────────────────────────────────────────────
def init_db():
    new_db = not os.path.exists(DB_PATH)
    conn   = get_db()
    if new_db:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS clientes (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre         TEXT    NOT NULL,
                email          TEXT    NOT NULL UNIQUE,
                password_hash  TEXT    NOT NULL,
                telefono       TEXT,
                fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS proveedores (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre   TEXT NOT NULL,
                contacto TEXT,
                email    TEXT,
                telefono TEXT
            );
            CREATE TABLE IF NOT EXISTS productos (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre       TEXT    NOT NULL,
                descripcion  TEXT,
                precio       REAL    NOT NULL CHECK(precio >= 0),
                existencias  INTEGER NOT NULL DEFAULT 0,
                proveedor_id INTEGER REFERENCES proveedores(id) ON DELETE SET NULL,
                categoria    TEXT    DEFAULT 'General',
                imagen_url   TEXT,
                activo       INTEGER DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS ventas (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id  INTEGER NOT NULL REFERENCES clientes(id),
                fecha       DATETIME DEFAULT CURRENT_TIMESTAMP,
                total       REAL    NOT NULL DEFAULT 0,
                estado      TEXT    DEFAULT 'pagado',
                metodo_pago TEXT    DEFAULT 'tarjeta'
            );
            CREATE TABLE IF NOT EXISTS detalle_venta (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                venta_id        INTEGER NOT NULL REFERENCES ventas(id)    ON DELETE CASCADE,
                producto_id     INTEGER NOT NULL REFERENCES productos(id),
                cantidad        INTEGER NOT NULL,
                precio_unitario REAL    NOT NULL
            );
            CREATE TABLE IF NOT EXISTS carrito (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
                creado     DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS items_carrito (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                carrito_id  INTEGER NOT NULL REFERENCES carrito(id)   ON DELETE CASCADE,
                producto_id INTEGER NOT NULL REFERENCES productos(id),
                cantidad    INTEGER NOT NULL DEFAULT 1
            );

            INSERT INTO proveedores (nombre, contacto, email, telefono) VALUES
                ('TechSupply MX',         'Laura Gomez', 'laura@techsupply.mx',       '9811234567'),
                ('Moda Campeche',         'Pedro Dzul',  'pedro@modacampeche.mx',     '9819876543'),
                ('Artesanias del Sureste','Ana Canul',   'ana@artesaniassureste.mx',  '9817654321');

            INSERT INTO productos (nombre, descripcion, precio, existencias, proveedor_id, categoria, imagen_url) VALUES
                ('Laptop Ultrabook Pro',    'Procesador i7, 16GB RAM, 512GB SSD, pantalla 14 FHD', 18500, 12, 1, 'Electronica', 'https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=400'),
                ('Smartphone Nova X',       'Pantalla AMOLED 6.5, camara 108MP, bateria 5000mAh',   8900, 25, 1, 'Electronica', 'https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=400'),
                ('Audifonos Bluetooth Pro', 'Cancelacion de ruido activa, 30h de bateria',           1250, 40, 1, 'Electronica', 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400'),
                ('Teclado Mecanico RGB',    'Switches Cherry MX Red, retroiluminacion RGB',            950, 18, 1, 'Electronica', 'https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=400'),
                ('Playera Lino Premium',    'Tela de lino 100%, corte slim, colores variados',         350, 60, 2, 'Ropa',        'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=400'),
                ('Mochila Ejecutiva',       'Material impermeable, compartimento laptop 15',           780, 30, 2, 'Accesorios',  'https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=400'),
                ('Artesania Jicara Maya',   'Jicara tallada a mano, disenos tradicionales mayas',      420, 15, 3, 'Artesanias',  'https://images.unsplash.com/photo-1606722590583-6951b5ea92ad?w=400'),
                ('Hamaca Yucateca',         'Algodon 100%, tejido artesanal, tamano matrimonial',     1100,  8, 3, 'Artesanias',  'https://images.unsplash.com/photo-1560448205-4d9b3e6bb6db?w=400'),
                ('Mouse Ergonomico',        'Diseno vertical, 6 botones programables, inalambrico',    680, 22, 1, 'Electronica', 'https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=400'),
                ('Agenda Ejecutiva 2025',   'Pasta dura, papel 90g, marcapaginas, formato A5',         195, 50, 2, 'Papeleria',   'https://images.unsplash.com/photo-1517842645767-c639042777db?w=400'),
                ('Camara Mirrorless',       'Sensor APS-C 24MP, video 4K, Wi-Fi, kit 18-55mm',      15000,  5, 1, 'Electronica', 'https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=400'),
                ('Huaraches Artesanales',   'Cuero genuino, suela resistente, hecho a mano',           550, 20, 3, 'Calzado',     'https://images.unsplash.com/photo-1603808033192-082d6919d3e1?w=400');
        """)
        conn.commit()
        print(f'✅ Base de datos creada en: {DB_PATH}')
    conn.close()

# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def hsh(p):
    return hashlib.sha256(p.encode()).hexdigest()

def get_or_create_cart(db):
    uid = session.get('user_id')
    if not uid:
        return None
    r = fetchone(db, 'SELECT id FROM carrito WHERE cliente_id = ?', (uid,))
    if r:
        return r['id']
    cur = mutate(db, 'INSERT INTO carrito (cliente_id) VALUES (?)', (uid,))
    db.commit()
    return cur.lastrowid

# ─────────────────────────────────────────────────────────────────────────────
#  USUARIOS  /api/users
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/api/users/register', methods=['POST'])
def register():
    d        = request.get_json(silent=True) or {}
    nombre   = (d.get('nombre')   or '').strip()
    email    = (d.get('email')    or '').strip().lower()
    password = (d.get('password') or '').strip()
    telefono = (d.get('telefono') or '').strip()
    if not nombre or not email or not password:
        return jsonify(error='Nombre, email y contrasena son obligatorios.'), 400
    if len(password) < 6:
        return jsonify(error='La contrasena debe tener al menos 6 caracteres.'), 400
    db = get_db()
    if fetchone(db, 'SELECT id FROM clientes WHERE email = ?', (email,)):
        db.close()
        return jsonify(error='El email ya esta registrado.'), 409
    cur = mutate(db, 'INSERT INTO clientes (nombre, email, password_hash, telefono) VALUES (?,?,?,?)',
                 (nombre, email, hsh(password), telefono or None))
    db.commit()
    uid = cur.lastrowid
    db.close()
    session['user_id']   = uid
    session['user_name'] = nombre
    return jsonify(message='Registro exitoso.', user={'id': uid, 'nombre': nombre, 'email': email}), 201


@app.route('/api/users/login', methods=['POST'])
def login():
    d        = request.get_json(silent=True) or {}
    email    = (d.get('email')    or '').strip().lower()
    password = (d.get('password') or '').strip()
    if not email or not password:
        return jsonify(error='Email y contrasena son obligatorios.'), 400
    db = get_db()
    r  = fetchone(db, 'SELECT * FROM clientes WHERE email = ? AND password_hash = ?',
                  (email, hsh(password)))
    db.close()
    if not r:
        return jsonify(error='Credenciales incorrectas.'), 401
    session['user_id']   = r['id']
    session['user_name'] = r['nombre']
    return jsonify(message='Inicio de sesion exitoso.',
                   user={'id': r['id'], 'nombre': r['nombre'], 'email': r['email']})


@app.route('/api/users/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify(message='Sesion cerrada.')


@app.route('/api/users/me', methods=['GET'])
def me():
    uid = session.get('user_id')
    if not uid:
        return jsonify(error='No autenticado.'), 401
    db = get_db()
    r  = fetchone(db, 'SELECT id, nombre, email, telefono, fecha_registro FROM clientes WHERE id = ?', (uid,))
    db.close()
    return jsonify(user=r) if r else (jsonify(error='No encontrado.'), 404)

# ─────────────────────────────────────────────────────────────────────────────
#  PRODUCTOS  /api/products
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/api/products/', methods=['GET'])
def list_products():
    search   = request.args.get('q',        '').strip()
    category = request.args.get('category', '').strip()
    db     = get_db()
    sql    = ('SELECT p.*, pr.nombre AS proveedor_nombre '
              'FROM productos p '
              'LEFT JOIN proveedores pr ON p.proveedor_id = pr.id '
              'WHERE p.activo = 1')
    params = []
    if search:
        sql += ' AND (p.nombre LIKE ? OR p.descripcion LIKE ?)'
        params += [f'%{search}%', f'%{search}%']
    if category:
        sql += ' AND p.categoria = ?'
        params.append(category)
    sql += ' ORDER BY p.id'
    rows = fetchall(db, sql, params)
    db.close()
    return jsonify(products=rows)


@app.route('/api/products/categories', methods=['GET'])
def get_categories():
    db   = get_db()
    rows = fetchall(db, 'SELECT DISTINCT categoria FROM productos WHERE activo = 1 ORDER BY categoria')
    db.close()
    return jsonify(categories=[r['categoria'] for r in rows])


@app.route('/api/products/<int:pid>', methods=['GET'])
def get_product(pid):
    db = get_db()
    r  = fetchone(db,
                  'SELECT p.*, pr.nombre AS proveedor_nombre '
                  'FROM productos p '
                  'LEFT JOIN proveedores pr ON p.proveedor_id = pr.id '
                  'WHERE p.id = ? AND p.activo = 1', (pid,))
    db.close()
    return jsonify(product=r) if r else (jsonify(error='No encontrado.'), 404)

# ─────────────────────────────────────────────────────────────────────────────
#  CARRITO  /api/cart
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/api/cart/', methods=['GET'])
def view_cart():
    if not session.get('user_id'):
        return jsonify(error='Debes iniciar sesion.'), 401
    db    = get_db()
    cid   = get_or_create_cart(db)
    items = fetchall(db,
                     'SELECT ic.id AS item_id, ic.cantidad, '
                     'p.id AS producto_id, p.nombre, p.precio, '
                     'p.imagen_url, p.existencias, '
                     '(ic.cantidad * p.precio) AS subtotal '
                     'FROM items_carrito ic '
                     'JOIN productos p ON ic.producto_id = p.id '
                     'WHERE ic.carrito_id = ?', (cid,))
    total = sum(r['subtotal'] for r in items)
    db.close()
    return jsonify(cart_id=cid, items=items, total=round(total, 2))


@app.route('/api/cart/add', methods=['POST'])
def add_to_cart():
    if not session.get('user_id'):
        return jsonify(error='Debes iniciar sesion.'), 401
    d   = request.get_json(silent=True) or {}
    pid = d.get('product_id')
    qty = int(d.get('cantidad', 1))
    if not pid or qty < 1:
        return jsonify(error='product_id y cantidad son requeridos.'), 400
    db = get_db()
    p  = fetchone(db, 'SELECT id, nombre, existencias FROM productos WHERE id = ? AND activo = 1', (pid,))
    if not p:
        db.close()
        return jsonify(error='Producto no encontrado.'), 404
    cid = get_or_create_cart(db)
    ex  = fetchone(db, 'SELECT id, cantidad FROM items_carrito WHERE carrito_id = ? AND producto_id = ?',
                   (cid, pid))
    already = ex['cantidad'] if ex else 0
    if already + qty > p['existencias']:
        db.close()
        return jsonify(error=f'Stock insuficiente. Disponible: {p["existencias"]}'), 409
    if ex:
        mutate(db, 'UPDATE items_carrito SET cantidad = cantidad + ? WHERE id = ?', (qty, ex['id']))
    else:
        mutate(db, 'INSERT INTO items_carrito (carrito_id, producto_id, cantidad) VALUES (?,?,?)',
               (cid, pid, qty))
    db.commit()
    db.close()
    return jsonify(message=f'"{p["nombre"]}" agregado al carrito.'), 201


@app.route('/api/cart/item/<int:iid>', methods=['PUT'])
def update_item(iid):
    if not session.get('user_id'):
        return jsonify(error='Debes iniciar sesion.'), 401
    d   = request.get_json(silent=True) or {}
    qty = int(d.get('cantidad', 0))
    db  = get_db()
    cid = get_or_create_cart(db)
    item = fetchone(db,
                    'SELECT ic.id, p.existencias FROM items_carrito ic '
                    'JOIN productos p ON ic.producto_id = p.id '
                    'WHERE ic.id = ? AND ic.carrito_id = ?', (iid, cid))
    if not item:
        db.close()
        return jsonify(error='Item no encontrado.'), 404
    if qty == 0:
        mutate(db, 'DELETE FROM items_carrito WHERE id = ?', (iid,))
    elif qty > item['existencias']:
        db.close()
        return jsonify(error='Stock insuficiente.'), 409
    else:
        mutate(db, 'UPDATE items_carrito SET cantidad = ? WHERE id = ?', (qty, iid))
    db.commit()
    db.close()
    return jsonify(message='Carrito actualizado.')


@app.route('/api/cart/item/<int:iid>', methods=['DELETE'])
def remove_item(iid):
    if not session.get('user_id'):
        return jsonify(error='Debes iniciar sesion.'), 401
    db  = get_db()
    cid = get_or_create_cart(db)
    cur = mutate(db, 'DELETE FROM items_carrito WHERE id = ? AND carrito_id = ?', (iid, cid))
    db.commit()
    db.close()
    return jsonify(message='Eliminado.') if cur.rowcount else (jsonify(error='No encontrado.'), 404)


@app.route('/api/cart/clear', methods=['DELETE'])
def clear_cart():
    if not session.get('user_id'):
        return jsonify(error='Debes iniciar sesion.'), 401
    db  = get_db()
    cid = get_or_create_cart(db)
    mutate(db, 'DELETE FROM items_carrito WHERE carrito_id = ?', (cid,))
    db.commit()
    db.close()
    return jsonify(message='Carrito vaciado.')

# ─────────────────────────────────────────────────────────────────────────────
#  CHECKOUT  /api/checkout
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/api/checkout/', methods=['POST'])
def checkout():
    uid = session.get('user_id')
    if not uid:
        return jsonify(error='Debes iniciar sesion.'), 401
    d   = request.get_json(silent=True) or {}
    mp  = d.get('metodo_pago', 'tarjeta')
    db  = get_db()
    cart = fetchone(db, 'SELECT id FROM carrito WHERE cliente_id = ?', (uid,))
    if not cart:
        db.close()
        return jsonify(error='Carrito vacio.'), 400
    cid   = cart['id']
    items = fetchall(db,
                     'SELECT ic.cantidad, p.id AS producto_id, '
                     'p.nombre, p.precio, p.existencias '
                     'FROM items_carrito ic '
                     'JOIN productos p ON ic.producto_id = p.id '
                     'WHERE ic.carrito_id = ?', (cid,))
    if not items:
        db.close()
        return jsonify(error='El carrito esta vacio.'), 400
    for i in items:
        if i['cantidad'] > i['existencias']:
            db.close()
            return jsonify(error=f'Stock insuficiente para "{i["nombre"]}". '
                                 f'Disponible: {i["existencias"]}'), 409
    total = sum(i['cantidad'] * i['precio'] for i in items)
    cur   = mutate(db,
                   'INSERT INTO ventas (cliente_id, total, estado, metodo_pago) VALUES (?,?,?,?)',
                   (uid, round(total, 2), 'pagado', mp))
    vid = cur.lastrowid
    for i in items:
        mutate(db,
               'INSERT INTO detalle_venta (venta_id, producto_id, cantidad, precio_unitario) '
               'VALUES (?,?,?,?)', (vid, i['producto_id'], i['cantidad'], i['precio']))
        mutate(db, 'UPDATE productos SET existencias = existencias - ? WHERE id = ?',
               (i['cantidad'], i['producto_id']))
    mutate(db, 'DELETE FROM items_carrito WHERE carrito_id = ?', (cid,))
    db.commit()
    db.close()
    return jsonify(message='Compra realizada con exito!',
                   venta_id=vid, total=round(total, 2), items_count=len(items)), 201


@app.route('/api/checkout/orders', methods=['GET'])
def orders():
    uid = session.get('user_id')
    if not uid:
        return jsonify(error='No autenticado.'), 401
    db     = get_db()
    ventas = fetchall(db, 'SELECT * FROM ventas WHERE cliente_id = ? ORDER BY fecha DESC', (uid,))
    result = []
    for v in ventas:
        details = fetchall(db,
                           'SELECT dv.cantidad, dv.precio_unitario, p.nombre, p.imagen_url '
                           'FROM detalle_venta dv '
                           'JOIN productos p ON dv.producto_id = p.id '
                           'WHERE dv.venta_id = ?', (v['id'],))
        result.append({**v, 'detalles': details})
    db.close()
    return jsonify(orders=result)

# ─────────────────────────────────────────────────────────────────────────────
#  ADMIN PANEL
# ─────────────────────────────────────────────────────────────────────────────
from functools import wraps

ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin1234')


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect('/admin/login')
        return f(*args, **kwargs)
    return decorated


def _page(title, body, active=''):
    nav_items = [
        ('Dashboard',   '/admin',             'dashboard'),
        ('Productos',   '/admin/productos',   'productos'),
        ('Usuarios',    '/admin/usuarios',    'usuarios'),
        ('Proveedores', '/admin/proveedores', 'proveedores'),
        ('Ventas',      '/admin/ventas',      'ventas'),
    ]
    nav_html = ''
    for label, href, key in nav_items:
        bg = '#d4541a' if key == active else 'transparent'
        cl = '#fff'    if key == active else '#9a9088'
        nav_html += (f'<a href="{href}" style="padding:.4rem .9rem;border-radius:6px;'
                     f'font-size:.85rem;text-decoration:none;background:{bg};color:{cl}">'
                     f'{label}</a>')
    css = '''
    <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:system-ui,sans-serif;background:#0f0e0d;color:#faf8f4;min-height:100vh}
    .container{max-width:1280px;margin:0 auto;padding:2rem 1.5rem}
    h1{font-size:1.4rem;font-weight:800;margin-bottom:.2rem}
    .sub{color:#7a7167;font-size:.85rem;margin-bottom:1.75rem}
    table{width:100%;border-collapse:collapse;background:#1a1917;border-radius:14px;overflow:hidden;font-size:.88rem}
    th{background:#252320;padding:.8rem 1rem;text-align:left;font-size:.72rem;text-transform:uppercase;letter-spacing:.07em;color:#6a6560;font-weight:600}
    td{padding:.8rem 1rem;border-bottom:1px solid #252320;vertical-align:middle}
    tr:last-child td{border-bottom:none}
    tr:hover>td{background:#1f1e1b}
    input[type=text],input[type=email],input[type=number],input[type=tel]
        {padding:.35rem .6rem;background:#0f0e0d;border:1px solid #3a3835;
         border-radius:7px;color:#faf8f4;font-size:.82rem;font-family:inherit}
    input:focus{outline:none;border-color:#d4541a}
    .btn-save{padding:.35rem .8rem;background:#d4541a;color:#fff;border:none;
              border-radius:7px;cursor:pointer;font-size:.8rem;font-weight:600}
    .btn-save:hover{background:#bf4a16}
    .btn-del{padding:.35rem .8rem;background:#3a1a1a;color:#e74c3c;
             border:1px solid #5a2a2a;border-radius:7px;cursor:pointer;font-size:.8rem;font-weight:600}
    .btn-del:hover{background:#c0392b;color:#fff;border-color:#c0392b}
    .msg-ok{background:#1a3a2a;border:1px solid #2e7d5a;color:#6fcf97;
            padding:.65rem 1.1rem;border-radius:9px;margin-bottom:1.25rem;font-size:.88rem}
    .stat-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:1rem;margin-bottom:2rem}
    .stat{background:#1a1917;border:1px solid #2a2825;border-radius:14px;padding:1.25rem}
    .stat-icon{font-size:1.4rem;margin-bottom:.5rem}
    .stat-val{font-size:1.75rem;font-weight:800;line-height:1}
    .stat-lbl{font-size:.75rem;color:#7a7167;margin-top:.3rem}
    .add-form{background:#1a1917;border:1px solid #2a2825;border-radius:14px;padding:1.5rem;margin-bottom:1.75rem}
    .add-form h3{font-size:1rem;font-weight:700;margin-bottom:1rem}
    .form-row{display:flex;gap:.75rem;flex-wrap:wrap;align-items:flex-end}
    .form-field{display:flex;flex-direction:column;gap:.3rem}
    .form-field label{font-size:.75rem;color:#9a9088;font-weight:500}
    .form-field input{padding:.55rem .8rem;font-size:.9rem}
    </style>'''
    nav = (f'<nav style="background:#1a1917;border-bottom:1px solid #252320;padding:.9rem 1.5rem;'
           f'display:flex;align-items:center;justify-content:space-between">'
           f'<span style="font-weight:800;font-size:1.1rem;color:#f0c14b">★ Star Up Admin</span>'
           f'<div style="display:flex;gap:.4rem">{nav_html}'
           f'<a href="/admin/logout" style="padding:.4rem .9rem;border-radius:6px;font-size:.85rem;'
           f'text-decoration:none;background:#2a2825;color:#9a9088;margin-left:.5rem">Salir</a>'
           f'</div></nav>')
    return (f'<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{title} — Star Up Admin</title>{css}</head>'
            f'<body>{nav}<div class="container">{body}</div></body></html>')


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = ''
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['is_admin'] = True
            return redirect('/admin')
        error = 'Contrasena incorrecta'
    err = f'<p style="color:#e74c3c;font-size:.83rem;margin-bottom:.75rem">{error}</p>' if error else ''
    return (
        '<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Admin Login</title>'
        '<style>*{box-sizing:border-box;margin:0;padding:0}'
        'body{font-family:system-ui,sans-serif;background:#0f0e0d;'
        'display:flex;align-items:center;justify-content:center;min-height:100vh}'
        '.box{background:#1a1917;border:1px solid #2a2825;border-radius:18px;padding:2.5rem;width:360px}'
        'label{display:block;font-size:.78rem;color:#9a9088;margin-bottom:.4rem;font-weight:500}'
        'input{width:100%;padding:.75rem 1rem;background:#0f0e0d;border:1px solid #2a2825;'
        'border-radius:9px;color:#faf8f4;font-size:.95rem;margin-bottom:1rem;font-family:inherit}'
        'input:focus{outline:none;border-color:#d4541a}'
        'button{width:100%;padding:.85rem;background:#d4541a;color:#fff;border:none;'
        'border-radius:9px;font-weight:700;font-size:1rem;cursor:pointer;font-family:inherit}'
        'button:hover{background:#bf4a16}</style></head><body>'
        '<div class="box">'
        '<div style="font-size:1.4rem;font-weight:800;color:#f0c14b;margin-bottom:.2rem">★ Star Up</div>'
        '<div style="font-size:.85rem;color:#7a7167;margin-bottom:2rem">Panel de administracion</div>'
        + err +
        '<form method="POST"><label>Contrasena</label>'
        '<input type="password" name="password" placeholder="••••••••" autofocus/>'
        '<button>Entrar al panel</button></form>'
        '</div></body></html>'
    )


@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    return redirect('/admin/login')


@app.route('/admin')
@admin_required
def admin_dashboard():
    db = get_db()
    tu = fetchone(db, 'SELECT COUNT(*) AS n FROM clientes')['n']
    tp = fetchone(db, 'SELECT COUNT(*) AS n FROM productos WHERE activo=1')['n']
    tv = fetchone(db, 'SELECT COUNT(*) AS n FROM ventas')['n']
    ti = fetchone(db, 'SELECT COALESCE(SUM(total),0) AS n FROM ventas WHERE estado="pagado"')['n']
    oo = fetchone(db, 'SELECT COUNT(*) AS n FROM productos WHERE existencias=0 AND activo=1')['n']
    lo = fetchone(db, 'SELECT COUNT(*) AS n FROM productos WHERE existencias>0 AND existencias<=5 AND activo=1')['n']
    db.close()
    stats = [('👥', tu,             'Usuarios',        '#6fcf97'),
             ('📦', tp,             'Productos activos','#faf8f4'),
             ('🛒', tv,             'Ventas',           '#6fcf97'),
             ('💰', f'${ti:,.0f}',  'Ingresos MXN',    '#6fcf97'),
             ('⚡', lo,             'Stock bajo',       '#f0c14b'),
             ('❌', oo,             'Agotados',         '#e74c3c')]
    cards = ''.join(
        f'<div class="stat"><div class="stat-icon">{i}</div>'
        f'<div class="stat-val" style="color:{c}">{v}</div>'
        f'<div class="stat-lbl">{l}</div></div>'
        for i, v, l, c in stats)
    links = (''.join([
        '<div style="display:flex;gap:.75rem;flex-wrap:wrap">',
        '<a href="/admin/productos"   style="padding:.55rem 1.1rem;background:#d4541a;color:#fff;border-radius:9px;text-decoration:none;font-size:.88rem;font-weight:600">📦 Productos</a>',
        '<a href="/admin/usuarios"    style="padding:.55rem 1.1rem;background:#2a2825;color:#faf8f4;border-radius:9px;text-decoration:none;font-size:.88rem;font-weight:600">👥 Usuarios</a>',
        '<a href="/admin/proveedores" style="padding:.55rem 1.1rem;background:#2a2825;color:#faf8f4;border-radius:9px;text-decoration:none;font-size:.88rem;font-weight:600">🏭 Proveedores</a>',
        '<a href="/admin/ventas"      style="padding:.55rem 1.1rem;background:#2a2825;color:#faf8f4;border-radius:9px;text-decoration:none;font-size:.88rem;font-weight:600">🛒 Ventas</a>',
        '</div>']))
    body = (f'<h1>Dashboard</h1><p class="sub">Resumen general de la tienda</p>'
            f'<div class="stat-grid">{cards}</div>{links}')
    return _page('Dashboard', body, 'dashboard')


@app.route('/admin/productos')
@admin_required
def admin_productos():
    db   = get_db()
    rows = fetchall(db,
                    'SELECT p.*, pr.nombre AS prov FROM productos p '
                    'LEFT JOIN proveedores pr ON p.proveedor_id = pr.id '
                    'ORDER BY p.existencias ASC, p.nombre')
    db.close()
    msg = request.args.get('msg', '')
    tbody = ''
    for p in rows:
        sc = '#e74c3c' if p['existencias'] == 0 else ('#f0c14b' if p['existencias'] <= 5 else '#6fcf97')
        prov = (p['prov'] or '-')
        tbody += (
            '<tr>'
            f'<td style="color:#6a6560">{p["id"]}</td>'
            f'<td><strong style="font-size:.9rem">{p["nombre"]}</strong><br>'
            f'<small style="color:#7a7167">{p["categoria"]} · {prov}</small></td>'
            f'<td style="color:{sc};font-weight:700">{p["existencias"]}</td>'
            f'<td style="font-weight:600">${p["precio"]:,.2f}</td>'
            f'<td>{"✅ Activo" if p["activo"] else "⏸ Inactivo"}</td>'
            '<td>'
            f'<form method="POST" action="/admin/productos/editar" '
            f'style="display:inline-flex;gap:.4rem;align-items:center;flex-wrap:wrap">'
            f'<input type="hidden" name="id" value="{p["id"]}"/>'
            f'<input type="number" name="precio" value="{p["precio"]}" step="0.01" min="0" style="width:88px" title="Precio"/>'
            f'<input type="number" name="existencias" value="{p["existencias"]}" min="0" style="width:68px" title="Stock"/>'
            '<button type="submit" class="btn-save">Guardar</button>'
            '</form>'
            '</td></tr>')
    msg_html = '<div class="msg-ok">✅ Producto actualizado correctamente</div>' if msg else ''
    body = (f'<h1>Productos</h1><p class="sub">Edita precio y stock. Los cambios se aplican de inmediato.</p>'
            + msg_html +
            '<table><thead><tr>'
            '<th>ID</th><th>Producto</th><th>Stock</th><th>Precio</th><th>Estado</th><th>Editar</th>'
            f'</tr></thead><tbody>{tbody}</tbody></table>')
    return _page('Productos', body, 'productos')


@app.route('/admin/productos/editar', methods=['POST'])
@admin_required
def admin_editar_producto():
    pid         = int(request.form.get('id'))
    precio      = float(request.form.get('precio', 0))
    existencias = int(request.form.get('existencias', 0))
    db = get_db()
    mutate(db, 'UPDATE productos SET precio=?, existencias=? WHERE id=?', (precio, existencias, pid))
    db.commit()
    db.close()
    return redirect('/admin/productos?msg=1')


@app.route('/admin/usuarios')
@admin_required
def admin_usuarios():
    db   = get_db()
    rows = fetchall(db,
                    'SELECT c.id, c.nombre, c.email, c.telefono, c.fecha_registro, '
                    'COUNT(v.id) AS compras, COALESCE(SUM(v.total),0) AS gastado '
                    'FROM clientes c LEFT JOIN ventas v ON v.cliente_id = c.id '
                    'GROUP BY c.id ORDER BY c.fecha_registro DESC')
    db.close()
    msg = request.args.get('msg', '')
    tbody = ''
    for u in rows:
        ctxt = 'Eliminar a ' + u['nombre'] + '? Esta accion no se puede deshacer.'
        tbody += (
            '<tr>'
            f'<td style="color:#6a6560">{u["id"]}</td>'
            f'<td style="font-size:.78rem;color:#7a7167">{str(u["fecha_registro"])[:10]}</td>'
            f'<td style="color:#f0c14b;font-weight:700">{u["compras"]}</td>'
            f'<td style="color:#6fcf97;font-weight:700">${u["gastado"]:,.2f}</td>'
            '<td>'
            '<form method="POST" action="/admin/usuarios/editar" '
            'style="display:flex;gap:.4rem;flex-wrap:wrap;margin-bottom:.4rem;align-items:center">'
            f'<input type="hidden" name="id" value="{u["id"]}"/>'
            f'<input type="text"  name="nombre"   value="{u["nombre"]}"        style="width:130px"/>'
            f'<input type="email" name="email"    value="{u["email"]}"         style="width:165px"/>'
            f'<input type="tel"   name="telefono" value="{u["telefono"] or ""}" placeholder="Telefono" style="width:110px"/>'
            '<button type="submit" class="btn-save">Guardar</button>'
            '</form>'
            f'<form method="POST" action="/admin/usuarios/eliminar" style="display:inline" '
            f'onsubmit="return confirm(\'{ctxt}\')">'
            f'<input type="hidden" name="id" value="{u["id"]}"/>'
            '<button type="submit" class="btn-del">🗑 Eliminar</button>'
            '</form>'
            '</td></tr>')
    msg_html = '<div class="msg-ok">✅ ' + msg.replace('+', ' ') + '</div>' if msg else ''
    body = (f'<h1>Usuarios</h1>'
            f'<p class="sub">{len(rows)} usuario{"s" if len(rows)!=1 else ""} registrados</p>'
            + msg_html +
            '<table><thead><tr>'
            '<th>ID</th><th>Registro</th><th>Compras</th><th>Gastado</th><th>Editar / Eliminar</th>'
            f'</tr></thead><tbody>{tbody}</tbody></table>')
    return _page('Usuarios', body, 'usuarios')


@app.route('/admin/usuarios/editar', methods=['POST'])
@admin_required
def admin_editar_usuario():
    uid  = int(request.form.get('id'))
    nom  = request.form.get('nombre',   '').strip()
    eml  = request.form.get('email',    '').strip().lower()
    tel  = request.form.get('telefono', '').strip()
    db   = get_db()
    mutate(db, 'UPDATE clientes SET nombre=?, email=?, telefono=? WHERE id=?',
           (nom, eml, tel or None, uid))
    db.commit()
    db.close()
    return redirect('/admin/usuarios?msg=Usuario+actualizado+correctamente')


@app.route('/admin/usuarios/eliminar', methods=['POST'])
@admin_required
def admin_eliminar_usuario():
    uid = int(request.form.get('id'))
    db  = get_db()
    mutate(db, 'DELETE FROM items_carrito WHERE carrito_id IN (SELECT id FROM carrito WHERE cliente_id=?)', (uid,))
    mutate(db, 'DELETE FROM carrito WHERE cliente_id=?', (uid,))
    mutate(db, 'DELETE FROM clientes WHERE id=?', (uid,))
    db.commit()
    db.close()
    return redirect('/admin/usuarios?msg=Usuario+eliminado')


@app.route('/admin/proveedores')
@admin_required
def admin_proveedores():
    db   = get_db()
    rows = fetchall(db,
                    'SELECT p.id, p.nombre, p.contacto, p.email, p.telefono, '
                    'COUNT(pr.id) AS total_productos '
                    'FROM proveedores p '
                    'LEFT JOIN productos pr ON pr.proveedor_id = p.id '
                    'GROUP BY p.id ORDER BY p.nombre')
    db.close()
    msg = request.args.get('msg', '')
    add_form = (
        '<div class="add-form"><h3>➕ Agregar nuevo proveedor</h3>'
        '<form method="POST" action="/admin/proveedores/agregar">'
        '<div class="form-row">'
        '<div class="form-field"><label>Nombre *</label>'
        '<input type="text" name="nombre" placeholder="Nombre del proveedor" required style="width:180px"/></div>'
        '<div class="form-field"><label>Contacto</label>'
        '<input type="text" name="contacto" placeholder="Nombre del contacto" style="width:160px"/></div>'
        '<div class="form-field"><label>Email</label>'
        '<input type="email" name="email" placeholder="correo@proveedor.com" style="width:180px"/></div>'
        '<div class="form-field"><label>Telefono</label>'
        '<input type="tel" name="telefono" placeholder="981 234 5678" style="width:140px"/></div>'
        '<div class="form-field"><label>&nbsp;</label>'
        '<button type="submit" class="btn-save" style="padding:.55rem 1.1rem;font-size:.88rem">Agregar</button></div>'
        '</div></form></div>')
    tbody = ''
    for p in rows:
        ctxt = 'Eliminar al proveedor ' + p['nombre'] + '? Sus productos quedaran sin proveedor.'
        tbody += (
            '<tr>'
            f'<td style="color:#6a6560">{p["id"]}</td>'
            f'<td style="color:#f0c14b;font-weight:700;text-align:center">{p["total_productos"]}</td>'
            '<td colspan="4">'
            '<form method="POST" action="/admin/proveedores/editar" '
            'style="display:flex;gap:.4rem;flex-wrap:wrap;align-items:center">'
            f'<input type="hidden" name="id" value="{p["id"]}"/>'
            f'<input type="text"  name="nombre"   value="{p["nombre"]}"          style="width:150px"/>'
            f'<input type="text"  name="contacto" value="{p["contacto"] or ""}"  placeholder="Contacto" style="width:130px"/>'
            f'<input type="email" name="email"    value="{p["email"] or ""}"     placeholder="Email"    style="width:175px"/>'
            f'<input type="tel"   name="telefono" value="{p["telefono"] or ""}"  placeholder="Telefono" style="width:120px"/>'
            '<button type="submit" class="btn-save">Guardar</button>'
            '</form>'
            '</td>'
            '<td>'
            f'<form method="POST" action="/admin/proveedores/eliminar" style="display:inline" '
            f'onsubmit="return confirm(\'{ctxt}\')">'
            f'<input type="hidden" name="id" value="{p["id"]}"/>'
            '<button type="submit" class="btn-del">🗑 Eliminar</button>'
            '</form>'
            '</td></tr>')
    msg_html = '<div class="msg-ok">✅ ' + msg.replace('+', ' ') + '</div>' if msg else ''
    body = (f'<h1>Proveedores</h1>'
            f'<p class="sub">{len(rows)} proveedor{"es" if len(rows)!=1 else ""} registrados</p>'
            + msg_html + add_form +
            '<table><thead><tr>'
            '<th>ID</th><th>Productos</th><th>Nombre</th><th>Contacto</th>'
            '<th>Email</th><th>Telefono</th><th>Eliminar</th>'
            f'</tr></thead><tbody>{tbody}</tbody></table>')
    return _page('Proveedores', body, 'proveedores')


@app.route('/admin/proveedores/agregar', methods=['POST'])
@admin_required
def admin_agregar_proveedor():
    nombre   = request.form.get('nombre',   '').strip()
    contacto = request.form.get('contacto', '').strip()
    email    = request.form.get('email',    '').strip()
    telefono = request.form.get('telefono', '').strip()
    if not nombre:
        return redirect('/admin/proveedores')
    db = get_db()
    mutate(db, 'INSERT INTO proveedores (nombre, contacto, email, telefono) VALUES (?,?,?,?)',
           (nombre, contacto or None, email or None, telefono or None))
    db.commit()
    db.close()
    return redirect('/admin/proveedores?msg=Proveedor+agregado+correctamente')


@app.route('/admin/proveedores/editar', methods=['POST'])
@admin_required
def admin_editar_proveedor():
    pid      = int(request.form.get('id'))
    nombre   = request.form.get('nombre',   '').strip()
    contacto = request.form.get('contacto', '').strip()
    email    = request.form.get('email',    '').strip()
    telefono = request.form.get('telefono', '').strip()
    db = get_db()
    mutate(db, 'UPDATE proveedores SET nombre=?, contacto=?, email=?, telefono=? WHERE id=?',
           (nombre, contacto or None, email or None, telefono or None, pid))
    db.commit()
    db.close()
    return redirect('/admin/proveedores?msg=Proveedor+actualizado+correctamente')


@app.route('/admin/proveedores/eliminar', methods=['POST'])
@admin_required
def admin_eliminar_proveedor():
    pid = int(request.form.get('id'))
    db  = get_db()
    mutate(db, 'UPDATE productos SET proveedor_id = NULL WHERE proveedor_id = ?', (pid,))
    mutate(db, 'DELETE FROM proveedores WHERE id = ?', (pid,))
    db.commit()
    db.close()
    return redirect('/admin/proveedores?msg=Proveedor+eliminado')


@app.route('/admin/ventas')
@admin_required
def admin_ventas():
    db     = get_db()
    ventas = fetchall(db,
                      'SELECT v.id, v.fecha, v.total, v.estado, v.metodo_pago, '
                      'c.nombre AS cnombre, c.email AS cemail '
                      'FROM ventas v JOIN clientes c ON v.cliente_id = c.id '
                      'ORDER BY v.fecha DESC')
    tbody          = ''
    total_ingresos = 0
    for v in ventas:
        detalles = fetchall(db,
                            'SELECT dv.cantidad, p.nombre FROM detalle_venta dv '
                            'JOIN productos p ON dv.producto_id = p.id '
                            'WHERE dv.venta_id = ?', (v['id'],))
        items = ', '.join(d['nombre'] + ' ×' + str(d['cantidad']) for d in detalles)
        if v['estado'] == 'pagado':
            total_ingresos += v['total']
        sc = '#6fcf97' if v['estado'] == 'pagado' else '#e74c3c'
        tbody += (
            '<tr>'
            f'<td style="font-weight:700;color:#f0c14b">#{v["id"]}</td>'
            f'<td style="font-size:.78rem;color:#7a7167">{str(v["fecha"])[:16]}</td>'
            f'<td><strong style="font-size:.88rem">{v["cnombre"]}</strong><br>'
            f'<small style="color:#7a7167">{v["cemail"]}</small></td>'
            f'<td style="font-size:.82rem;color:#9a9088;max-width:240px">{items}</td>'
            f'<td style="font-weight:700;color:#faf8f4">${v["total"]:,.2f}</td>'
            f'<td style="color:{sc};font-weight:600">{v["estado"].upper()}</td>'
            f'<td style="font-size:.82rem;color:#7a7167">{v["metodo_pago"]}</td>'
            '</tr>')
    db.close()
    banner = (f'<div style="background:#1a3a2a;border:1px solid #2e7d5a;border-radius:10px;'
              f'padding:.85rem 1.25rem;margin-bottom:1.5rem;display:inline-block">'
              f'<span style="font-size:.82rem;color:#7a7167">Ingresos totales: </span>'
              f'<strong style="font-size:1.2rem;color:#6fcf97;font-weight:800">'
              f'${total_ingresos:,.2f} MXN</strong></div>')
    body = (f'<h1>Ventas</h1>'
            f'<p class="sub">{len(ventas)} venta{"s" if len(ventas)!=1 else ""} registradas</p>'
            + banner +
            '<table><thead><tr>'
            '<th>Pedido</th><th>Fecha</th><th>Cliente</th>'
            '<th>Productos</th><th>Total</th><th>Estado</th><th>Pago</th>'
            f'</tr></thead><tbody>{tbody}</tbody></table>')
    return _page('Ventas', body, 'ventas')

# ─────────────────────────────────────────────────────────────────────────────
#  FRONTEND
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    target = os.path.join(FRONTEND_DIR, path)
    if path and os.path.exists(target):
        return send_from_directory(FRONTEND_DIR, path)
    return send_from_directory(FRONTEND_DIR, 'index.html')

# ─────────────────────────────────────────────────────────────────────────────
#  INICIO
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    print(f'✅ Base de datos lista: {DB_PATH}')
    print('🚀 Servidor corriendo en http://localhost:5000')
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
