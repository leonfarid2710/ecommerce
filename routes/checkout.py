"""
routes/checkout.py  –  /api/checkout
Process purchase: validate stock → create venta → update inventory → clear cart.
"""

from flask import Blueprint, request, jsonify, session
from models.database import get_db

checkout_bp = Blueprint('checkout', __name__)


# ── POST /api/checkout  ───────────────────────────────────────────────────────
@checkout_bp.route('/', methods=['POST'])
def checkout():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify(error='Debes iniciar sesión para comprar.'), 401

    data        = request.get_json(silent=True) or {}
    metodo_pago = data.get('metodo_pago', 'tarjeta')

    db = get_db()

    # ── Get active cart ───────────────────────────────────────────────────────
    cart = db.execute(
        'SELECT id FROM carrito WHERE cliente_id = ?', (user_id,)
    ).fetchone()

    if not cart:
        return jsonify(error='Carrito vacío.'), 400

    cart_id = cart['id']

    items = db.execute(
        '''SELECT ic.id AS item_id, ic.cantidad,
                  p.id AS producto_id, p.nombre, p.precio, p.existencias
           FROM items_carrito ic
           JOIN productos p ON ic.producto_id = p.id
           WHERE ic.carrito_id = ?''',
        (cart_id,)
    ).fetchall()

    if not items:
        return jsonify(error='El carrito está vacío.'), 400

    # ── Validate stock for all items ──────────────────────────────────────────
    for item in items:
        if item['cantidad'] > item['existencias']:
            return jsonify(
                error=f'Stock insuficiente para "{item["nombre"]}". '
                      f'Disponible: {item["existencias"]}, solicitado: {item["cantidad"]}.'
            ), 409

    # ── Calculate total ───────────────────────────────────────────────────────
    total = sum(i['cantidad'] * i['precio'] for i in items)

    # ── Insert venta ──────────────────────────────────────────────────────────
    venta_cur = db.execute(
        'INSERT INTO ventas (cliente_id, total, estado, metodo_pago) VALUES (?,?,?,?)',
        (user_id, round(total, 2), 'pagado', metodo_pago)
    )
    venta_id = venta_cur.lastrowid

    # ── Insert detalle_venta & decrement stock ────────────────────────────────
    for item in items:
        db.execute(
            'INSERT INTO detalle_venta (venta_id, producto_id, cantidad, precio_unitario) '
            'VALUES (?,?,?,?)',
            (venta_id, item['producto_id'], item['cantidad'], item['precio'])
        )
        db.execute(
            'UPDATE productos SET existencias = existencias - ? WHERE id = ?',
            (item['cantidad'], item['producto_id'])
        )

    # ── Clear cart ────────────────────────────────────────────────────────────
    db.execute('DELETE FROM items_carrito WHERE carrito_id = ?', (cart_id,))

    db.commit()

    return jsonify(
        message='¡Compra realizada con éxito!',
        venta_id=venta_id,
        total=round(total, 2),
        items_count=len(items)
    ), 201


# ── GET /api/checkout/orders  ─────────────────────────────────────────────────
@checkout_bp.route('/orders', methods=['GET'])
def my_orders():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify(error='No autenticado.'), 401

    db   = get_db()
    rows = db.execute(
        'SELECT * FROM ventas WHERE cliente_id = ? ORDER BY fecha DESC',
        (user_id,)
    ).fetchall()

    orders = []
    for v in rows:
        details = db.execute(
            '''SELECT dv.cantidad, dv.precio_unitario,
                      p.nombre, p.imagen_url
               FROM detalle_venta dv
               JOIN productos p ON dv.producto_id = p.id
               WHERE dv.venta_id = ?''',
            (v['id'],)
        ).fetchall()
        orders.append({**dict(v), 'detalles': [dict(d) for d in details]})

    return jsonify(orders=orders)
