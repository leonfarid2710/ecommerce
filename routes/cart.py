"""
routes/cart.py  –  /api/cart
Shopping cart CRUD. Cart is stored in the DB per authenticated user.
Guest users get a session-based cart_id.
"""

from flask import Blueprint, request, jsonify, session
from models.database import get_db

cart_bp = Blueprint('cart', __name__)


def _get_or_create_cart(db):
    """Return the active cart_id for the current user, creating one if needed."""
    user_id = session.get('user_id')
    if not user_id:
        return None, jsonify(error='Debes iniciar sesión para usar el carrito.'), 401

    row = db.execute(
        'SELECT id FROM carrito WHERE cliente_id = ?', (user_id,)
    ).fetchone()

    if row:
        return row['id'], None, None

    cur = db.execute('INSERT INTO carrito (cliente_id) VALUES (?)', (user_id,))
    db.commit()
    return cur.lastrowid, None, None


def _cart_items(db, cart_id):
    return db.execute(
        '''SELECT ic.id AS item_id, ic.cantidad,
                  p.id AS producto_id, p.nombre, p.precio,
                  p.imagen_url, p.existencias,
                  (ic.cantidad * p.precio) AS subtotal
           FROM items_carrito ic
           JOIN productos p ON ic.producto_id = p.id
           WHERE ic.carrito_id = ?''',
        (cart_id,)
    ).fetchall()


# ── GET /api/cart  ────────────────────────────────────────────────────────────
@cart_bp.route('/', methods=['GET'])
def view_cart():
    db = get_db()
    cart_id, err, code = _get_or_create_cart(db)
    if err:
        return err, code

    items = _cart_items(db, cart_id)
    rows  = [dict(i) for i in items]
    total = sum(r['subtotal'] for r in rows)
    return jsonify(cart_id=cart_id, items=rows, total=round(total, 2))


# ── POST /api/cart/add  ───────────────────────────────────────────────────────
@cart_bp.route('/add', methods=['POST'])
def add_to_cart():
    data       = request.get_json(silent=True) or {}
    product_id = data.get('product_id')
    cantidad   = int(data.get('cantidad', 1))

    if not product_id or cantidad < 1:
        return jsonify(error='product_id y cantidad son requeridos.'), 400

    db = get_db()
    cart_id, err, code = _get_or_create_cart(db)
    if err:
        return err, code

    # ── Validate product & stock ──────────────────────────────────────────────
    producto = db.execute(
        'SELECT id, nombre, existencias FROM productos WHERE id = ? AND activo = 1',
        (product_id,)
    ).fetchone()
    if not producto:
        return jsonify(error='Producto no encontrado.'), 404

    # Check existing cart quantity
    existing = db.execute(
        'SELECT id, cantidad FROM items_carrito WHERE carrito_id = ? AND producto_id = ?',
        (cart_id, product_id)
    ).fetchone()

    already_in_cart = existing['cantidad'] if existing else 0
    if already_in_cart + cantidad > producto['existencias']:
        return jsonify(error=f'Stock insuficiente. Disponible: {producto["existencias"]}'), 409

    if existing:
        db.execute(
            'UPDATE items_carrito SET cantidad = cantidad + ? WHERE id = ?',
            (cantidad, existing['id'])
        )
    else:
        db.execute(
            'INSERT INTO items_carrito (carrito_id, producto_id, cantidad) VALUES (?,?,?)',
            (cart_id, product_id, cantidad)
        )
    db.commit()

    return jsonify(message=f'"{producto["nombre"]}" agregado al carrito.'), 201


# ── PUT /api/cart/item/<item_id>  ─────────────────────────────────────────────
@cart_bp.route('/item/<int:item_id>', methods=['PUT'])
def update_item(item_id):
    data     = request.get_json(silent=True) or {}
    cantidad = int(data.get('cantidad', 0))

    if cantidad < 0:
        return jsonify(error='Cantidad inválida.'), 400

    db = get_db()
    cart_id, err, code = _get_or_create_cart(db)
    if err:
        return err, code

    item = db.execute(
        '''SELECT ic.id, ic.producto_id, p.existencias
           FROM items_carrito ic JOIN productos p ON ic.producto_id = p.id
           WHERE ic.id = ? AND ic.carrito_id = ?''',
        (item_id, cart_id)
    ).fetchone()

    if not item:
        return jsonify(error='Ítem no encontrado en el carrito.'), 404

    if cantidad == 0:
        db.execute('DELETE FROM items_carrito WHERE id = ?', (item_id,))
    elif cantidad > item['existencias']:
        return jsonify(error=f'Stock insuficiente. Disponible: {item["existencias"]}'), 409
    else:
        db.execute('UPDATE items_carrito SET cantidad = ? WHERE id = ?', (cantidad, item_id))

    db.commit()
    return jsonify(message='Carrito actualizado.')


# ── DELETE /api/cart/item/<item_id>  ──────────────────────────────────────────
@cart_bp.route('/item/<int:item_id>', methods=['DELETE'])
def remove_item(item_id):
    db = get_db()
    cart_id, err, code = _get_or_create_cart(db)
    if err:
        return err, code

    result = db.execute(
        'DELETE FROM items_carrito WHERE id = ? AND carrito_id = ?',
        (item_id, cart_id)
    )
    db.commit()

    if result.rowcount == 0:
        return jsonify(error='Ítem no encontrado.'), 404
    return jsonify(message='Producto eliminado del carrito.')


# ── DELETE /api/cart/clear  ───────────────────────────────────────────────────
@cart_bp.route('/clear', methods=['DELETE'])
def clear_cart():
    db = get_db()
    cart_id, err, code = _get_or_create_cart(db)
    if err:
        return err, code

    db.execute('DELETE FROM items_carrito WHERE carrito_id = ?', (cart_id,))
    db.commit()
    return jsonify(message='Carrito vaciado.')
