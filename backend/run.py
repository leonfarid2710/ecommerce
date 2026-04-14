"""
STAR UP E-COMMERCE — run.py
Archivo unico para correr en Windows sin problemas de modulos.
Ejecutar: python run.py
"""

import os
import sys
import sqlite3
import hashlib
import re
from flask import Flask, request, jsonify, session, send_from_directory, Response, redirect

# ─────────────────────────────────────────────────────────────────────────────
#  RUTAS DE ARCHIVOS
# ─────────────────────────────────────────────────────────────────────────────
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
# En Render usa /tmp para la DB (el filesystem es efimero)
# Para persistencia real en produccion usa PostgreSQL
DB_PATH      = os.environ.get('DB_PATH', os.path.join(BASE_DIR, 'ecommerce.db'))
FRONTEND_DIR = os.path.join(BASE_DIR, '..', 'frontend')

# ─────────────────────────────────────────────────────────────────────────────
#  FLASK APP
# ─────────────────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'starUp_dev_secret_2025!')
# Cookies seguras en produccion
if os.environ.get('RENDER'):
    app.config['SESSION_COOKIE_SECURE']   = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'None'
    app.config['SESSION_COOKIE_HTTPONLY'] = True

# ─────────────────────────────────────────────────────────────────────────────
#  BASE DE DATOS
# ─────────────────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def init_db():
    if os.path.exists(DB_PATH):
        return
    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS clientes (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre         TEXT NOT NULL,
            email          TEXT NOT NULL UNIQUE,
            password_hash  TEXT NOT NULL,
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
            nombre       TEXT NOT NULL,
            descripcion  TEXT,
            precio       REAL NOT NULL CHECK (precio >= 0),
            existencias  INTEGER NOT NULL DEFAULT 0,
            proveedor_id INTEGER REFERENCES proveedores(id),
            categoria    TEXT DEFAULT 'General',
            imagen_url   TEXT,
            activo       INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS ventas (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id  INTEGER NOT NULL REFERENCES clientes(id),
            fecha       DATETIME DEFAULT CURRENT_TIMESTAMP,
            total       REAL NOT NULL DEFAULT 0,
            estado      TEXT DEFAULT 'pagado',
            metodo_pago TEXT DEFAULT 'tarjeta'
        );
        CREATE TABLE IF NOT EXISTS detalle_venta (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            venta_id        INTEGER NOT NULL REFERENCES ventas(id),
            producto_id     INTEGER NOT NULL REFERENCES productos(id),
            cantidad        INTEGER NOT NULL,
            precio_unitario REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS carrito (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL REFERENCES clientes(id),
            creado     DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS items_carrito (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            carrito_id  INTEGER NOT NULL REFERENCES carrito(id),
            producto_id INTEGER NOT NULL REFERENCES productos(id),
            cantidad    INTEGER NOT NULL DEFAULT 1
        );

        INSERT INTO proveedores (nombre, contacto, email, telefono) VALUES
            ('TechSupply MX',        'Laura Gomez', 'laura@techsupply.mx',      '9811234567'),
            ('Moda Campeche',        'Pedro Dzul',  'pedro@modacampeche.mx',    '9819876543'),
            ('Artesanias del Sureste','Ana Canul',  'ana@artesaniassureste.mx', '9817654321');

        INSERT INTO productos (nombre, descripcion, precio, existencias, proveedor_id, categoria, imagen_url) VALUES
            ('Laptop Ultrabook Pro',    'Procesador i7, 16GB RAM, 512GB SSD, pantalla 14 FHD',       18500.00, 12, 1, 'Electronica', 'https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=400'),
            ('Smartphone Nova X',       'Pantalla AMOLED 6.5, camara 108MP, bateria 5000mAh',         8900.00, 25, 1, 'Electronica', 'https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=400'),
            ('Audifonos Bluetooth Pro', 'Cancelacion de ruido activa, 30h de bateria',                1250.00, 40, 1, 'Electronica', 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400'),
            ('Teclado Mecanico RGB',    'Switches Cherry MX Red, retroiluminacion RGB',                950.00, 18, 1, 'Electronica', 'https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=400'),
            ('Playera Lino Premium',    'Tela de lino 100%, corte slim',                               350.00, 60, 2, 'Ropa',        'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=400'),
            ('Mochila Ejecutiva',       'Material impermeable, compartimento laptop 15, USB port',     780.00, 30, 2, 'Accesorios',  'https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=400'),
            ('Artesania Jicara Maya',   'Jicara tallada a mano, disenos tradicionales mayas',          420.00, 15, 3, 'Artesanias',  'https://images.unsplash.com/photo-1606722590583-6951b5ea92ad?w=400'),
            ('Hamaca Yucateca',         'Algodon 100%, tejido artesanal, tamano matrimonial',          1100.00,  8, 3, 'Artesanias',  'https://images.unsplash.com/photo-1560448205-4d9b3e6bb6db?w=400'),
            ('Mouse Ergonomico',        'Diseno vertical, 6 botones, inalambrico',                     680.00, 22, 1, 'Electronica', 'https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=400'),
            ('Agenda Ejecutiva 2025',   'Pasta dura, papel 90g, formato A5',                           195.00, 50, 2, 'Papeleria',   'https://images.unsplash.com/photo-1517842645767-c639042777db?w=400'),
            ('Camara Mirrorless',       'Sensor APS-C 24MP, video 4K, Wi-Fi, kit 18-55mm',           15000.00,  5, 1, 'Electronica', 'https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=400'),
            ('Huaraches Artesanales',   'Cuero genuino, suela resistente, hecho a mano',               550.00, 20, 3, 'Calzado',     'https://images.unsplash.com/photo-1603808033192-082d6919d3e1?w=400');
    ''')
    conn.commit()
    conn.close()
    print('✅ Base de datos creada con datos de ejemplo')


# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def hsh(p): return hashlib.sha256(p.encode()).hexdigest()
def row(r):  return dict(r) if r else None


# ─────────────────────────────────────────────────────────────────────────────
#  USUARIOS
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/api/users/register', methods=['POST'])
def register():
    d = request.get_json(silent=True) or {}
    nombre   = (d.get('nombre')   or '').strip()
    email    = (d.get('email')    or '').strip().lower()
    password = (d.get('password') or '').strip()
    telefono = (d.get('telefono') or '').strip()
    if not nombre or not email or not password:
        return jsonify(error='Nombre, email y contrasena son obligatorios.'), 400
    if len(password) < 6:
        return jsonify(error='La contrasena debe tener al menos 6 caracteres.'), 400
    db = get_db()
    if db.execute('SELECT id FROM clientes WHERE email=?', (email,)).fetchone():
        db.close(); return jsonify(error='El email ya esta registrado.'), 409
    cur = db.execute('INSERT INTO clientes (nombre,email,password_hash,telefono) VALUES (?,?,?,?)',
                     (nombre, email, hsh(password), telefono or None))
    db.commit()
    uid = cur.lastrowid
    db.close()
    session['user_id']   = uid
    session['user_name'] = nombre
    return jsonify(message='Registro exitoso.', user={'id':uid,'nombre':nombre,'email':email}), 201


@app.route('/api/users/login', methods=['POST'])
def login():
    d = request.get_json(silent=True) or {}
    email    = (d.get('email')    or '').strip().lower()
    password = (d.get('password') or '').strip()
    if not email or not password:
        return jsonify(error='Email y contrasena son obligatorios.'), 400
    db  = get_db()
    r   = db.execute('SELECT * FROM clientes WHERE email=? AND password_hash=?',
                     (email, hsh(password))).fetchone()
    db.close()
    if not r:
        return jsonify(error='Credenciales incorrectas.'), 401
    session['user_id']   = r['id']
    session['user_name'] = r['nombre']
    return jsonify(message='Inicio de sesion exitoso.', user={'id':r['id'],'nombre':r['nombre'],'email':r['email']})


@app.route('/api/users/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify(message='Sesion cerrada.')


@app.route('/api/users/me', methods=['GET'])
def me():
    uid = session.get('user_id')
    if not uid:
        return jsonify(error='No autenticado.'), 401
    db  = get_db()
    r   = db.execute('SELECT id,nombre,email,telefono,fecha_registro FROM clientes WHERE id=?', (uid,)).fetchone()
    db.close()
    return jsonify(user=row(r)) if r else (jsonify(error='No encontrado.'), 404)


# ─────────────────────────────────────────────────────────────────────────────
#  PRODUCTOS
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/api/products/', methods=['GET'])
def list_products():
    search   = request.args.get('q','').strip()
    category = request.args.get('category','').strip()
    db  = get_db()
    sql = 'SELECT p.*,pr.nombre AS proveedor_nombre FROM productos p LEFT JOIN proveedores pr ON p.proveedor_id=pr.id WHERE p.activo=1'
    params = []
    if search:
        sql += ' AND (p.nombre LIKE ? OR p.descripcion LIKE ?)'
        params += [f'%{search}%', f'%{search}%']
    if category:
        sql += ' AND p.categoria=?'
        params.append(category)
    sql += ' ORDER BY p.id'
    rows = db.execute(sql, params).fetchall()
    db.close()
    return jsonify(products=[dict(r) for r in rows])


@app.route('/api/products/categories', methods=['GET'])
def categories():
    db   = get_db()
    rows = db.execute('SELECT DISTINCT categoria FROM productos WHERE activo=1 ORDER BY categoria').fetchall()
    db.close()
    return jsonify(categories=[r['categoria'] for r in rows])


@app.route('/api/products/<int:pid>', methods=['GET'])
def get_product(pid):
    db  = get_db()
    r   = db.execute('SELECT p.*,pr.nombre AS proveedor_nombre FROM productos p LEFT JOIN proveedores pr ON p.proveedor_id=pr.id WHERE p.id=? AND p.activo=1', (pid,)).fetchone()
    db.close()
    return jsonify(product=dict(r)) if r else (jsonify(error='No encontrado.'), 404)


# ─────────────────────────────────────────────────────────────────────────────
#  CARRITO
# ─────────────────────────────────────────────────────────────────────────────
def get_or_create_cart(db):
    uid = session.get('user_id')
    if not uid:
        return None
    r = db.execute('SELECT id FROM carrito WHERE cliente_id=?', (uid,)).fetchone()
    if r:
        return r['id']
    cur = db.execute('INSERT INTO carrito (cliente_id) VALUES (?)', (uid,))
    db.commit()
    return cur.lastrowid


@app.route('/api/cart/', methods=['GET'])
def view_cart():
    if not session.get('user_id'):
        return jsonify(error='Debes iniciar sesion.'), 401
    db = get_db()
    cid = get_or_create_cart(db)
    items = db.execute('''SELECT ic.id AS item_id, ic.cantidad,
                          p.id AS producto_id, p.nombre, p.precio, p.imagen_url, p.existencias,
                          (ic.cantidad * p.precio) AS subtotal
                          FROM items_carrito ic JOIN productos p ON ic.producto_id=p.id
                          WHERE ic.carrito_id=?''', (cid,)).fetchall()
    rows  = [dict(i) for i in items]
    total = sum(r['subtotal'] for r in rows)
    db.close()
    return jsonify(cart_id=cid, items=rows, total=round(total,2))


@app.route('/api/cart/add', methods=['POST'])
def add_to_cart():
    if not session.get('user_id'):
        return jsonify(error='Debes iniciar sesion.'), 401
    d   = request.get_json(silent=True) or {}
    pid = d.get('product_id')
    qty = int(d.get('cantidad', 1))
    if not pid or qty < 1:
        return jsonify(error='product_id y cantidad son requeridos.'), 400
    db  = get_db()
    p   = db.execute('SELECT id,nombre,existencias FROM productos WHERE id=? AND activo=1', (pid,)).fetchone()
    if not p:
        db.close(); return jsonify(error='Producto no encontrado.'), 404
    cid = get_or_create_cart(db)
    ex  = db.execute('SELECT id,cantidad FROM items_carrito WHERE carrito_id=? AND producto_id=?', (cid,pid)).fetchone()
    already = ex['cantidad'] if ex else 0
    if already + qty > p['existencias']:
        db.close(); return jsonify(error=f'Stock insuficiente. Disponible: {p["existencias"]}'), 409
    if ex:
        db.execute('UPDATE items_carrito SET cantidad=cantidad+? WHERE id=?', (qty, ex['id']))
    else:
        db.execute('INSERT INTO items_carrito (carrito_id,producto_id,cantidad) VALUES (?,?,?)', (cid,pid,qty))
    db.commit(); db.close()
    return jsonify(message=f'"{p["nombre"]}" agregado al carrito.'), 201


@app.route('/api/cart/item/<int:iid>', methods=['PUT'])
def update_item(iid):
    if not session.get('user_id'):
        return jsonify(error='Debes iniciar sesion.'), 401
    d   = request.get_json(silent=True) or {}
    qty = int(d.get('cantidad', 0))
    db  = get_db()
    cid = get_or_create_cart(db)
    item = db.execute('''SELECT ic.id, p.existencias FROM items_carrito ic
                         JOIN productos p ON ic.producto_id=p.id
                         WHERE ic.id=? AND ic.carrito_id=?''', (iid, cid)).fetchone()
    if not item:
        db.close(); return jsonify(error='Item no encontrado.'), 404
    if qty == 0:
        db.execute('DELETE FROM items_carrito WHERE id=?', (iid,))
    elif qty > item['existencias']:
        db.close(); return jsonify(error=f'Stock insuficiente.'), 409
    else:
        db.execute('UPDATE items_carrito SET cantidad=? WHERE id=?', (qty, iid))
    db.commit(); db.close()
    return jsonify(message='Carrito actualizado.')


@app.route('/api/cart/item/<int:iid>', methods=['DELETE'])
def remove_item(iid):
    if not session.get('user_id'):
        return jsonify(error='Debes iniciar sesion.'), 401
    db  = get_db()
    cid = get_or_create_cart(db)
    res = db.execute('DELETE FROM items_carrito WHERE id=? AND carrito_id=?', (iid, cid))
    db.commit(); db.close()
    return jsonify(message='Eliminado.') if res.rowcount else (jsonify(error='No encontrado.'), 404)


@app.route('/api/cart/clear', methods=['DELETE'])
def clear_cart():
    if not session.get('user_id'):
        return jsonify(error='Debes iniciar sesion.'), 401
    db  = get_db()
    cid = get_or_create_cart(db)
    db.execute('DELETE FROM items_carrito WHERE carrito_id=?', (cid,))
    db.commit(); db.close()
    return jsonify(message='Carrito vaciado.')


# ─────────────────────────────────────────────────────────────────────────────
#  CHECKOUT
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/api/checkout/', methods=['POST'])
def checkout():
    uid = session.get('user_id')
    if not uid:
        return jsonify(error='Debes iniciar sesion.'), 401
    d   = request.get_json(silent=True) or {}
    mp  = d.get('metodo_pago', 'tarjeta')
    db  = get_db()
    cart = db.execute('SELECT id FROM carrito WHERE cliente_id=?', (uid,)).fetchone()
    if not cart:
        db.close(); return jsonify(error='Carrito vacio.'), 400
    cid   = cart['id']
    items = db.execute('''SELECT ic.cantidad, p.id AS producto_id,
                          p.nombre, p.precio, p.existencias
                          FROM items_carrito ic JOIN productos p ON ic.producto_id=p.id
                          WHERE ic.carrito_id=?''', (cid,)).fetchall()
    if not items:
        db.close(); return jsonify(error='El carrito esta vacio.'), 400
    for i in items:
        if i['cantidad'] > i['existencias']:
            db.close()
            return jsonify(error=f'Stock insuficiente para "{i["nombre"]}". Disponible: {i["existencias"]}'), 409
    total = sum(i['cantidad'] * i['precio'] for i in items)
    vid   = db.execute('INSERT INTO ventas (cliente_id,total,estado,metodo_pago) VALUES (?,?,?,?)',
                       (uid, round(total,2), 'pagado', mp)).lastrowid
    for i in items:
        db.execute('INSERT INTO detalle_venta (venta_id,producto_id,cantidad,precio_unitario) VALUES (?,?,?,?)',
                   (vid, i['producto_id'], i['cantidad'], i['precio']))
        db.execute('UPDATE productos SET existencias=existencias-? WHERE id=?', (i['cantidad'], i['producto_id']))
    db.execute('DELETE FROM items_carrito WHERE carrito_id=?', (cid,))
    db.commit(); db.close()
    return jsonify(message='Compra realizada con exito!', venta_id=vid,
                   total=round(total,2), items_count=len(items)), 201


@app.route('/api/checkout/orders', methods=['GET'])
def orders():
    uid = session.get('user_id')
    if not uid:
        return jsonify(error='No autenticado.'), 401
    db   = get_db()
    rows = db.execute('SELECT * FROM ventas WHERE cliente_id=? ORDER BY fecha DESC', (uid,)).fetchall()
    result = []
    for v in rows:
        details = db.execute('''SELECT dv.cantidad, dv.precio_unitario, p.nombre, p.imagen_url
                                FROM detalle_venta dv JOIN productos p ON dv.producto_id=p.id
                                WHERE dv.venta_id=?''', (v['id'],)).fetchall()
        result.append({**dict(v), 'detalles': [dict(d) for d in details]})
    db.close()
    return jsonify(orders=result)



# ─────────────────────────────────────────────────────────────────────────────
#  ADMIN PANEL
# ─────────────────────────────────────────────────────────────────────────────
from functools import wraps

ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin1234')

# ── Shared layout pieces ─────────────────────────────────────────────────────
def _page(title, body, active=''):
    nav_items = [
        ('Dashboard',    '/admin',            'dashboard'),
        ('Productos',    '/admin/productos',  'productos'),
        ('Usuarios',     '/admin/usuarios',   'usuarios'),
        ('Proveedores',  '/admin/proveedores','proveedores'),
        ('Ventas',       '/admin/ventas',     'ventas'),
    ]
    nav_html = ''
    for label, href, key in nav_items:
        style = 'background:#d4541a;color:#fff' if key == active else 'color:#9a9088'
        nav_html += f'<a href="{href}" style="padding:.4rem .9rem;border-radius:6px;font-size:.85rem;text-decoration:none;{style}">{label}</a>'
    return (
        '<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{title} — Star Up Admin</title>'
        '<style>'
        '*{box-sizing:border-box;margin:0;padding:0}'
        'body{font-family:system-ui,sans-serif;background:#0f0e0d;color:#faf8f4;min-height:100vh}'
        '.container{max-width:1280px;margin:0 auto;padding:2rem 1.5rem}'
        'h1{font-size:1.5rem;font-weight:800;margin-bottom:.2rem}'
        '.sub{color:#7a7167;font-size:.85rem;margin-bottom:1.75rem}'
        'table{width:100%;border-collapse:collapse;background:#1a1917;border-radius:14px;overflow:hidden;font-size:.88rem}'
        'th{background:#252320;padding:.8rem 1rem;text-align:left;font-size:.72rem;text-transform:uppercase;letter-spacing:.07em;color:#6a6560;font-weight:600}'
        'td{padding:.8rem 1rem;border-bottom:1px solid #252320;vertical-align:middle}'
        'tr:last-child td{border-bottom:none}'
        'tr:hover>td{background:#1f1e1b}'
        'input[type=text],input[type=email],input[type=number],input[type=tel]{padding:.35rem .6rem;background:#0f0e0d;border:1px solid #3a3835;border-radius:7px;color:#faf8f4;font-size:.82rem;font-family:inherit}'
        'input:focus{outline:none;border-color:#d4541a}'
        '.btn-save{padding:.35rem .8rem;background:#d4541a;color:#fff;border:none;border-radius:7px;cursor:pointer;font-size:.8rem;font-weight:600}'
        '.btn-save:hover{background:#bf4a16}'
        '.btn-del{padding:.35rem .8rem;background:#3a1a1a;color:#e74c3c;border:1px solid #5a2a2a;border-radius:7px;cursor:pointer;font-size:.8rem;font-weight:600}'
        '.btn-del:hover{background:#c0392b;color:#fff;border-color:#c0392b}'
        '.btn-add{padding:.5rem 1rem;background:#1a3a2a;color:#6fcf97;border:1px solid #2a5a3a;border-radius:8px;cursor:pointer;font-size:.85rem;font-weight:600;text-decoration:none;display:inline-flex;align-items:center;gap:.4rem}'
        '.btn-add:hover{background:#2a5a3a}'
        '.msg-ok{background:#1a3a2a;border:1px solid #2e7d5a;color:#6fcf97;padding:.65rem 1.1rem;border-radius:9px;margin-bottom:1.25rem;font-size:.88rem}'
        '.msg-err{background:#3a1a1a;border:1px solid #7d2e2e;color:#f97;padding:.65rem 1.1rem;border-radius:9px;margin-bottom:1.25rem;font-size:.88rem}'
        '.stat-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:1rem;margin-bottom:2rem}'
        '.stat{background:#1a1917;border:1px solid #2a2825;border-radius:14px;padding:1.25rem}'
        '.stat-icon{font-size:1.4rem;margin-bottom:.5rem}'
        '.stat-val{font-size:1.75rem;font-weight:800;line-height:1}'
        '.stat-lbl{font-size:.75rem;color:#7a7167;margin-top:.3rem}'
        '.add-form{background:#1a1917;border:1px solid #2a2825;border-radius:14px;padding:1.5rem;margin-bottom:1.75rem}'
        '.add-form h3{font-size:1rem;font-weight:700;margin-bottom:1rem;color:#faf8f4}'
        '.form-row{display:flex;gap:.75rem;flex-wrap:wrap;align-items:flex-end}'
        '.form-field{display:flex;flex-direction:column;gap:.3rem}'
        '.form-field label{font-size:.75rem;color:#9a9088;font-weight:500}'
        '.form-field input{padding:.55rem .8rem;font-size:.9rem}'
        '</style></head><body>'
        f'<nav style="background:#1a1917;border-bottom:1px solid #252320;padding:.9rem 1.5rem;display:flex;align-items:center;justify-content:space-between">'
        '<span style="font-weight:800;font-size:1.1rem;color:#f0c14b">★ Star Up Admin</span>'
        f'<div style="display:flex;gap:.4rem">{nav_html}'
        '<a href="/admin/logout" style="padding:.4rem .9rem;border-radius:6px;font-size:.85rem;text-decoration:none;background:#2a2825;color:#9a9088;margin-left:.5rem">Salir</a>'
        '</div></nav>'
        f'<div class="container">{body}</div></body></html>'
    )


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect('/admin/login')
        return f(*args, **kwargs)
    return decorated


# ── Login ────────────────────────────────────────────────────────────────────
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = ''
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['is_admin'] = True
            return redirect('/admin')
        error = 'Contraseña incorrecta'
    err = f'<p style="color:#e74c3c;font-size:.83rem;margin-bottom:.75rem">{error}</p>' if error else ''
    return (
        '<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Admin Login — Star Up</title>'
        '<style>*{box-sizing:border-box;margin:0;padding:0}body{font-family:system-ui,sans-serif;background:#0f0e0d;display:flex;align-items:center;justify-content:center;min-height:100vh}'
        '.box{background:#1a1917;border:1px solid #2a2825;border-radius:18px;padding:2.5rem;width:360px}'
        'label{display:block;font-size:.78rem;color:#9a9088;margin-bottom:.4rem;font-weight:500}'
        'input{width:100%;padding:.75rem 1rem;background:#0f0e0d;border:1px solid #2a2825;border-radius:9px;color:#faf8f4;font-size:.95rem;margin-bottom:1rem;font-family:inherit}'
        'input:focus{outline:none;border-color:#d4541a}'
        'button{width:100%;padding:.85rem;background:#d4541a;color:#fff;border:none;border-radius:9px;font-weight:700;font-size:1rem;cursor:pointer;font-family:inherit}'
        'button:hover{background:#bf4a16}</style></head><body>'
        '<div class="box">'
        '<div style="font-size:1.4rem;font-weight:800;color:#f0c14b;margin-bottom:.2rem">★ Star Up</div>'
        '<div style="font-size:.85rem;color:#7a7167;margin-bottom:2rem">Panel de administración</div>'
        + err +
        '<form method="POST"><label>Contraseña</label>'
        '<input type="password" name="password" placeholder="••••••••" autofocus/>'
        '<button>Entrar al panel</button></form>'
        '</div></body></html>'
    )


@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    return redirect('/admin/login')


# ── Dashboard ────────────────────────────────────────────────────────────────
@app.route('/admin')
@admin_required
def admin_dashboard():
    db = get_db()
    tu = db.execute('SELECT COUNT(*) FROM clientes').fetchone()[0]
    tp = db.execute('SELECT COUNT(*) FROM productos WHERE activo=1').fetchone()[0]
    tv = db.execute('SELECT COUNT(*) FROM ventas').fetchone()[0]
    ti = db.execute('SELECT COALESCE(SUM(total),0) FROM ventas WHERE estado="pagado"').fetchone()[0]
    oo = db.execute('SELECT COUNT(*) FROM productos WHERE existencias=0 AND activo=1').fetchone()[0]
    lo = db.execute('SELECT COUNT(*) FROM productos WHERE existencias>0 AND existencias<=5 AND activo=1').fetchone()[0]
    db.close()
    stats = [
        ('👥', tu,            'Usuarios',         '#6fcf97'),
        ('📦', tp,            'Productos activos', '#faf8f4'),
        ('🛒', tv,            'Ventas',            '#6fcf97'),
        ('💰', f'${ti:,.0f}', 'Ingresos MXN',     '#6fcf97'),
        ('⚡', lo,           'Stock bajo',        '#f0c14b'),
        ('❌', oo,           'Agotados',          '#e74c3c'),
    ]
    cards = ''.join(
        f'<div class="stat"><div class="stat-icon">{i}</div>'
        f'<div class="stat-val" style="color:{c}">{v}</div>'
        f'<div class="stat-lbl">{l}</div></div>'
        for i,v,l,c in stats
    )
    links = (
        '<div style="display:flex;gap:.75rem;flex-wrap:wrap">'
        '<a href="/admin/productos" style="padding:.55rem 1.1rem;background:#d4541a;color:#fff;border-radius:9px;text-decoration:none;font-size:.88rem;font-weight:600">📦 Productos</a>'
        '<a href="/admin/usuarios" style="padding:.55rem 1.1rem;background:#2a2825;color:#faf8f4;border-radius:9px;text-decoration:none;font-size:.88rem;font-weight:600">👥 Usuarios</a>'
        '<a href="/admin/proveedores" style="padding:.55rem 1.1rem;background:#2a2825;color:#faf8f4;border-radius:9px;text-decoration:none;font-size:.88rem;font-weight:600">🏭 Proveedores</a>'
        '<a href="/admin/ventas" style="padding:.55rem 1.1rem;background:#2a2825;color:#faf8f4;border-radius:9px;text-decoration:none;font-size:.88rem;font-weight:600">🛒 Ventas</a>'
        '</div>'
    )
    body = (
        '<h1>Dashboard</h1><p class="sub">Resumen general de la tienda</p>'
        f'<div class="stat-grid">{cards}</div>{links}'
    )
    return _page('Dashboard', body, 'dashboard')


# ── Productos ────────────────────────────────────────────────────────────────
@app.route('/admin/productos')
@admin_required
def admin_productos():
    db   = get_db()
    rows = db.execute(
        'SELECT p.*, pr.nombre AS prov FROM productos p '
        'LEFT JOIN proveedores pr ON p.proveedor_id=pr.id '
        'ORDER BY p.existencias ASC, p.nombre'
    ).fetchall()
    db.close()
    msg = request.args.get('msg','')

    tbody = ''
    for p in rows:
        sc = '#e74c3c' if p['existencias']==0 else ('#f0c14b' if p['existencias']<=5 else '#6fcf97')
        tbody += (
            '<tr>'
            '<td style="color:#6a6560">' + str(p['id']) + '</td>'
            '<td><strong style="font-size:.9rem">' + p['nombre'] + '</strong><br>'
            '<small style="color:#7a7167">' + p['categoria'] + ((' · ' + p['prov']) if p['prov'] else '') + '</small></td>'
            '<td style="color:' + sc + ';font-weight:700">' + str(p['existencias']) + '</td>'
            '<td style="font-weight:600">$' + f'{p["precio"]:,.2f}' + '</td>'
            '<td>' + ('✅ Activo' if p['activo'] else '⏸ Inactivo') + '</td>'
            '<td>'
            '<form method="POST" action="/admin/productos/editar" style="display:inline-flex;gap:.4rem;align-items:center;flex-wrap:wrap">'
            '<input type="hidden" name="id" value="' + str(p['id']) + '"/>'
            '<input type="number" name="precio" value="' + str(p['precio']) + '" step="0.01" min="0" style="width:88px" title="Nuevo precio"/>'
            '<input type="number" name="existencias" value="' + str(p['existencias']) + '" min="0" style="width:68px" title="Stock"/>'
            '<button type="submit" class="btn-save">Guardar</button>'
            '</form>'
            '</td></tr>'
        )

    msg_html = '<div class="msg-ok">✅ Producto actualizado correctamente</div>' if msg else ''
    body = (
        '<h1>Productos</h1><p class="sub">Edita precio y stock. Los cambios se aplican de inmediato.</p>'
        + msg_html +
        '<table><thead><tr>'
        '<th>ID</th><th>Producto</th><th>Stock</th><th>Precio</th><th>Estado</th><th>Editar precio / stock</th>'
        '</tr></thead><tbody>' + tbody + '</tbody></table>'
    )
    return _page('Productos', body, 'productos')


@app.route('/admin/productos/editar', methods=['POST'])
@admin_required
def admin_editar_producto():
    pid  = int(request.form.get('id'))
    precio = float(request.form.get('precio', 0))
    existencias = int(request.form.get('existencias', 0))
    db = get_db()
    db.execute('UPDATE productos SET precio=?, existencias=? WHERE id=?', (precio, existencias, pid))
    db.commit(); db.close()
    return redirect('/admin/productos?msg=1')


# ── Usuarios ─────────────────────────────────────────────────────────────────
@app.route('/admin/usuarios')
@admin_required
def admin_usuarios():
    db   = get_db()
    rows = db.execute(
        'SELECT c.id, c.nombre, c.email, c.telefono, c.fecha_registro, '
        'COUNT(v.id) AS compras, COALESCE(SUM(v.total),0) AS gastado '
        'FROM clientes c LEFT JOIN ventas v ON v.cliente_id=c.id '
        'GROUP BY c.id ORDER BY c.fecha_registro DESC'
    ).fetchall()
    db.close()
    msg  = request.args.get('msg','')
    tipo = request.args.get('tipo','')

    tbody = ''
    for u in rows:
        confirm_txt = 'Eliminar a ' + u['nombre'] + '? Esta accion no se puede deshacer.'
        tbody += (
            '<tr>'
            '<td style="color:#6a6560">' + str(u['id']) + '</td>'
            '<td style="font-size:.78rem;color:#7a7167">' + str(u['fecha_registro'])[:10] + '</td>'
            '<td style="color:#f0c14b;font-weight:700">' + str(u['compras']) + '</td>'
            '<td style="color:#6fcf97;font-weight:700">$' + f'{u["gastado"]:,.2f}' + '</td>'
            '<td>'
            '<form method="POST" action="/admin/usuarios/editar" style="display:flex;gap:.4rem;flex-wrap:wrap;margin-bottom:.4rem;align-items:center">'
            '<input type="hidden" name="id" value="' + str(u['id']) + '"/>'
            '<input type="text" name="nombre" value="' + u['nombre'] + '" style="width:130px" title="Nombre"/>'
            '<input type="email" name="email" value="' + u['email'] + '" style="width:165px" title="Email"/>'
            '<input type="tel" name="telefono" value="' + (u['telefono'] or '') + '" placeholder="Teléfono" style="width:110px"/>'
            '<button type="submit" class="btn-save">Guardar</button>'
            '</form>'
            '<form method="POST" action="/admin/usuarios/eliminar" onsubmit="return confirm(\'' + confirm_txt + '\')"  style="display:inline">'
            '<input type="hidden" name="id" value="' + str(u['id']) + '"/>'
            '<button type="submit" class="btn-del">🗑 Eliminar usuario</button>'
            '</form>'
            '</td></tr>'
        )

    msg_html = ''
    if msg:
        ok = tipo != 'del'
        msg_html = '<div class="msg-' + ('ok' if ok else 'ok') + '">' + ('✅ ' if ok else '🗑 ') + msg.replace('+',' ') + '</div>'

    body = (
        '<h1>Usuarios</h1>'
        '<p class="sub">' + str(len(rows)) + ' usuario' + ('s' if len(rows)!=1 else '') + ' registrados en la plataforma</p>'
        + msg_html +
        '<table><thead><tr>'
        '<th>ID</th><th>Registro</th><th>Compras</th><th>Total gastado</th><th>Editar / Eliminar</th>'
        '</tr></thead><tbody>' + tbody + '</tbody></table>'
    )
    return _page('Usuarios', body, 'usuarios')


@app.route('/admin/usuarios/editar', methods=['POST'])
@admin_required
def admin_editar_usuario():
    uid  = int(request.form.get('id'))
    nom  = request.form.get('nombre','').strip()
    eml  = request.form.get('email','').strip().lower()
    tel  = request.form.get('telefono','').strip()
    db   = get_db()
    db.execute('UPDATE clientes SET nombre=?, email=?, telefono=? WHERE id=?', (nom, eml, tel or None, uid))
    db.commit(); db.close()
    return redirect('/admin/usuarios?msg=Usuario+actualizado+correctamente')


@app.route('/admin/usuarios/eliminar', methods=['POST'])
@admin_required
def admin_eliminar_usuario():
    uid = int(request.form.get('id'))
    db  = get_db()
    db.execute('DELETE FROM items_carrito WHERE carrito_id IN (SELECT id FROM carrito WHERE cliente_id=?)', (uid,))
    db.execute('DELETE FROM carrito WHERE cliente_id=?', (uid,))
    db.execute('DELETE FROM clientes WHERE id=?', (uid,))
    db.commit(); db.close()
    return redirect('/admin/usuarios?msg=Usuario+eliminado&tipo=del')


# ── Proveedores ───────────────────────────────────────────────────────────────
@app.route('/admin/proveedores')
@admin_required
def admin_proveedores():
    db   = get_db()
    rows = db.execute(
        'SELECT p.id, p.nombre, p.contacto, p.email, p.telefono, COUNT(pr.id) AS total_productos '
        'FROM proveedores p LEFT JOIN productos pr ON pr.proveedor_id=p.id '
        'GROUP BY p.id ORDER BY p.nombre'
    ).fetchall()
    db.close()
    msg = request.args.get('msg','')

    add_form = (
        '<div class="add-form">'
        '<h3>➕ Agregar nuevo proveedor</h3>'
        '<form method="POST" action="/admin/proveedores/agregar">'
        '<div class="form-row">'
        '<div class="form-field"><label>Nombre *</label><input type="text" name="nombre" placeholder="Nombre del proveedor" required style="width:180px"/></div>'
        '<div class="form-field"><label>Contacto</label><input type="text" name="contacto" placeholder="Nombre del contacto" style="width:160px"/></div>'
        '<div class="form-field"><label>Email</label><input type="email" name="email" placeholder="correo@proveedor.com" style="width:180px"/></div>'
        '<div class="form-field"><label>Teléfono</label><input type="tel" name="telefono" placeholder="981 234 5678" style="width:140px"/></div>'
        '<div class="form-field"><label>&nbsp;</label><button type="submit" class="btn-save" style="padding:.55rem 1.1rem;font-size:.88rem">Agregar</button></div>'
        '</div></form></div>'
    )

    tbody = ''
    for p in rows:
        confirm_txt = 'Eliminar al proveedor ' + p['nombre'] + '? Sus productos quedaran sin proveedor asignado.'
        tbody += (
            '<tr>'
            '<td style="color:#6a6560">' + str(p['id']) + '</td>'
            '<td style="color:#f0c14b;font-weight:700;text-align:center">' + str(p['total_productos']) + '</td>'
            '<td colspan="4">'
            '<form method="POST" action="/admin/proveedores/editar" style="display:flex;gap:.4rem;flex-wrap:wrap;align-items:center">'
            '<input type="hidden" name="id" value="' + str(p['id']) + '"/>'
            '<input type="text" name="nombre" value="' + p['nombre'] + '" style="width:150px" title="Nombre"/>'
            '<input type="text" name="contacto" value="' + (p['contacto'] or '') + '" placeholder="Contacto" style="width:130px"/>'
            '<input type="email" name="email" value="' + (p['email'] or '') + '" placeholder="Email" style="width:175px"/>'
            '<input type="tel" name="telefono" value="' + (p['telefono'] or '') + '" placeholder="Teléfono" style="width:120px"/>'
            '<button type="submit" class="btn-save">Guardar</button>'
            '</form>'
            '</td>'
            '<td>'
            '<form method="POST" action="/admin/proveedores/eliminar" onsubmit="return confirm(\'' + confirm_txt + '\')" style="display:inline">'
            '<input type="hidden" name="id" value="' + str(p['id']) + '"/>'
            '<button type="submit" class="btn-del">🗑 Eliminar</button>'
            '</form>'
            '</td></tr>'
        )

    msg_html = '<div class="msg-ok">✅ ' + msg.replace('+',' ') + '</div>' if msg else ''
    body = (
        '<h1>Proveedores</h1>'
        '<p class="sub">' + str(len(rows)) + ' proveedor' + ('es' if len(rows)!=1 else '') + ' registrados</p>'
        + msg_html + add_form +
        '<table><thead><tr>'
        '<th>ID</th><th>Productos</th><th>Nombre</th><th>Contacto</th><th>Email</th><th>Teléfono</th><th>Eliminar</th>'
        '</tr></thead><tbody>' + tbody + '</tbody></table>'
    )
    return _page('Proveedores', body, 'proveedores')


@app.route('/admin/proveedores/agregar', methods=['POST'])
@admin_required
def admin_agregar_proveedor():
    nombre   = request.form.get('nombre','').strip()
    contacto = request.form.get('contacto','').strip()
    email    = request.form.get('email','').strip()
    telefono = request.form.get('telefono','').strip()
    if not nombre:
        return redirect('/admin/proveedores')
    db = get_db()
    db.execute('INSERT INTO proveedores (nombre, contacto, email, telefono) VALUES (?,?,?,?)',
               (nombre, contacto or None, email or None, telefono or None))
    db.commit(); db.close()
    return redirect('/admin/proveedores?msg=Proveedor+agregado+correctamente')


@app.route('/admin/proveedores/editar', methods=['POST'])
@admin_required
def admin_editar_proveedor():
    pid      = int(request.form.get('id'))
    nombre   = request.form.get('nombre','').strip()
    contacto = request.form.get('contacto','').strip()
    email    = request.form.get('email','').strip()
    telefono = request.form.get('telefono','').strip()
    db = get_db()
    db.execute('UPDATE proveedores SET nombre=?, contacto=?, email=?, telefono=? WHERE id=?',
               (nombre, contacto or None, email or None, telefono or None, pid))
    db.commit(); db.close()
    return redirect('/admin/proveedores?msg=Proveedor+actualizado+correctamente')


@app.route('/admin/proveedores/eliminar', methods=['POST'])
@admin_required
def admin_eliminar_proveedor():
    pid = int(request.form.get('id'))
    db  = get_db()
    db.execute('UPDATE productos SET proveedor_id=NULL WHERE proveedor_id=?', (pid,))
    db.execute('DELETE FROM proveedores WHERE id=?', (pid,))
    db.commit(); db.close()
    return redirect('/admin/proveedores?msg=Proveedor+eliminado')


# ── Ventas ────────────────────────────────────────────────────────────────────
@app.route('/admin/ventas')
@admin_required
def admin_ventas():
    db  = get_db()
    ventas = db.execute(
        'SELECT v.id, v.fecha, v.total, v.estado, v.metodo_pago, '
        'c.nombre AS cnombre, c.email AS cemail '
        'FROM ventas v JOIN clientes c ON v.cliente_id=c.id '
        'ORDER BY v.fecha DESC'
    ).fetchall()

    tbody = ''
    total_ingresos = 0
    for v in ventas:
        detalles = db.execute(
            'SELECT dv.cantidad, p.nombre FROM detalle_venta dv '
            'JOIN productos p ON dv.producto_id=p.id WHERE dv.venta_id=?', (v['id'],)
        ).fetchall()
        items = ', '.join(d['nombre'] + ' ×' + str(d['cantidad']) for d in detalles)
        if v['estado'] == 'pagado':
            total_ingresos += v['total']
        sc = '#6fcf97' if v['estado']=='pagado' else '#e74c3c'
        tbody += (
            '<tr>'
            '<td style="font-weight:700;color:#f0c14b">#' + str(v['id']) + '</td>'
            '<td style="font-size:.78rem;color:#7a7167">' + str(v['fecha'])[:16] + '</td>'
            '<td><strong style="font-size:.88rem">' + v['cnombre'] + '</strong><br>'
            '<small style="color:#7a7167">' + v['cemail'] + '</small></td>'
            '<td style="font-size:.82rem;color:#9a9088;max-width:240px">' + items + '</td>'
            '<td style="font-weight:700;color:#faf8f4">$' + f'{v["total"]:,.2f}' + '</td>'
            '<td style="color:' + sc + ';font-weight:600">' + v['estado'].upper() + '</td>'
            '<td style="font-size:.82rem;color:#7a7167">' + v['metodo_pago'] + '</td>'
            '</tr>'
        )
    db.close()

    banner = (
        '<div style="background:#1a3a2a;border:1px solid #2e7d5a;border-radius:10px;'
        'padding:.85rem 1.25rem;margin-bottom:1.5rem;display:inline-block">'
        '<span style="font-size:.82rem;color:#7a7167">Ingresos totales: </span>'
        '<strong style="font-size:1.2rem;color:#6fcf97;font-weight:800">$' + f'{total_ingresos:,.2f}' + ' MXN</strong></div>'
    )
    body = (
        '<h1>Ventas</h1>'
        '<p class="sub">' + str(len(ventas)) + ' venta' + ('s' if len(ventas)!=1 else '') + ' registradas</p>'
        + banner +
        '<table><thead><tr>'
        '<th>Pedido</th><th>Fecha</th><th>Cliente</th><th>Productos</th><th>Total</th><th>Estado</th><th>Pago</th>'
        '</tr></thead><tbody>' + tbody + '</tbody></table>'
    )
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
    print('✅ Base de datos lista')
    print('🚀 Servidor corriendo en http://localhost:5000')
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
