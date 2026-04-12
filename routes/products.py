"""
routes/products.py  –  /api/products
Product catalog: list, filter, detail.
"""

from flask import Blueprint, request, jsonify
from models.database import get_db

products_bp = Blueprint('products', __name__)


def _row_to_dict(row):
    return dict(row) if row else None


# ── GET /api/products  (list / search / filter by category) ──────────────────
@products_bp.route('/', methods=['GET'])
def list_products():
    search   = request.args.get('q',        '').strip()
    category = request.args.get('category', '').strip()
    in_stock = request.args.get('in_stock', '').strip()  # '1' = only in-stock

    db  = get_db()
    sql = '''SELECT p.*, pr.nombre AS proveedor_nombre
             FROM productos p
             LEFT JOIN proveedores pr ON p.proveedor_id = pr.id
             WHERE p.activo = 1'''
    params = []

    if search:
        sql += ' AND (p.nombre LIKE ? OR p.descripcion LIKE ?)'
        params += [f'%{search}%', f'%{search}%']
    if category:
        sql += ' AND p.categoria = ?'
        params.append(category)
    if in_stock == '1':
        sql += ' AND p.existencias > 0'

    sql += ' ORDER BY p.id'

    rows = db.execute(sql, params).fetchall()
    return jsonify(products=[_row_to_dict(r) for r in rows])


# ── GET /api/products/categories  ────────────────────────────────────────────
@products_bp.route('/categories', methods=['GET'])
def categories():
    db   = get_db()
    rows = db.execute(
        'SELECT DISTINCT categoria FROM productos WHERE activo = 1 ORDER BY categoria'
    ).fetchall()
    return jsonify(categories=[r['categoria'] for r in rows])


# ── GET /api/products/<id>  ───────────────────────────────────────────────────
@products_bp.route('/<int:product_id>', methods=['GET'])
def get_product(product_id):
    db  = get_db()
    row = db.execute(
        '''SELECT p.*, pr.nombre AS proveedor_nombre
           FROM productos p
           LEFT JOIN proveedores pr ON p.proveedor_id = pr.id
           WHERE p.id = ? AND p.activo = 1''',
        (product_id,)
    ).fetchone()
    if not row:
        return jsonify(error='Producto no encontrado.'), 404
    return jsonify(product=_row_to_dict(row))
