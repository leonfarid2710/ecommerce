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
from flask import Flask, request, jsonify, session, send_from_directory, Response

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
