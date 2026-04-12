"""
routes/users.py  –  /api/users
Handles registration, login, logout and session.
"""

from flask import Blueprint, request, jsonify, session
from models.database import get_db
import hashlib, re

users_bp = Blueprint('users', __name__)


def _hash(password: str) -> str:
    """SHA-256 hash (for demo; use bcrypt in production)."""
    return hashlib.sha256(password.encode()).hexdigest()


def _row_to_dict(row):
    return dict(row) if row else None


# ── POST /api/users/register ──────────────────────────────────────────────────
@users_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}
    nombre   = (data.get('nombre')   or '').strip()
    email    = (data.get('email')    or '').strip().lower()
    password = (data.get('password') or '').strip()
    telefono = (data.get('telefono') or '').strip()

    # ── Validations ───────────────────────────────────────────────────────────
    if not nombre or not email or not password:
        return jsonify(error='Nombre, email y contraseña son obligatorios.'), 400
    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        return jsonify(error='Formato de email inválido.'), 400
    if len(password) < 6:
        return jsonify(error='La contraseña debe tener al menos 6 caracteres.'), 400

    db = get_db()
    if db.execute('SELECT id FROM clientes WHERE email = ?', (email,)).fetchone():
        return jsonify(error='El email ya está registrado.'), 409

    cur = db.execute(
        'INSERT INTO clientes (nombre, email, password_hash, telefono) VALUES (?,?,?,?)',
        (nombre, email, _hash(password), telefono or None)
    )
    db.commit()

    cliente_id = cur.lastrowid
    session['user_id']   = cliente_id
    session['user_name'] = nombre

    return jsonify(message='Registro exitoso.', user={
        'id': cliente_id, 'nombre': nombre, 'email': email
    }), 201


# ── POST /api/users/login ─────────────────────────────────────────────────────
@users_bp.route('/login', methods=['POST'])
def login():
    data     = request.get_json(silent=True) or {}
    email    = (data.get('email')    or '').strip().lower()
    password = (data.get('password') or '').strip()

    if not email or not password:
        return jsonify(error='Email y contraseña son obligatorios.'), 400

    db  = get_db()
    row = db.execute(
        'SELECT * FROM clientes WHERE email = ? AND password_hash = ?',
        (email, _hash(password))
    ).fetchone()

    if not row:
        return jsonify(error='Credenciales incorrectas.'), 401

    session['user_id']   = row['id']
    session['user_name'] = row['nombre']

    return jsonify(message='Inicio de sesión exitoso.', user={
        'id': row['id'], 'nombre': row['nombre'], 'email': row['email']
    })


# ── POST /api/users/logout ────────────────────────────────────────────────────
@users_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify(message='Sesión cerrada.')


# ── GET /api/users/me ─────────────────────────────────────────────────────────
@users_bp.route('/me', methods=['GET'])
def me():
    uid = session.get('user_id')
    if not uid:
        return jsonify(error='No autenticado.'), 401
    db  = get_db()
    row = db.execute(
        'SELECT id, nombre, email, telefono, fecha_registro FROM clientes WHERE id = ?',
        (uid,)
    ).fetchone()
    if not row:
        return jsonify(error='Usuario no encontrado.'), 404
    return jsonify(user=_row_to_dict(row))
