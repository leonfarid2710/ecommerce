"""
models/database.py
Lightweight SQLite connection helper (swap to PostgreSQL via DATABASE_URL).
"""

import sqlite3
import os
from flask import g, current_app


def get_db():
    """Open a new DB connection if not already open for this request."""
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row   # columns accessible by name
        g.db.execute('PRAGMA foreign_keys = ON')
    return g.db


def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db(app):
    """Create tables and seed data if the DB file doesn't exist yet."""
    schema_path = os.path.join(os.path.dirname(__file__), '..', 'schema.sql')
    db_path     = app.config['DATABASE']

    app.teardown_appcontext(close_db)

    # Only run schema if DB is brand new
    if not os.path.exists(db_path):
        with app.app_context():
            db = get_db()
            with open(schema_path, 'r', encoding='utf-8') as f:
                db.executescript(f.read())
            db.commit()
