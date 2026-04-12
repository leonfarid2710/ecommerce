"""
wsgi.py - Punto de entrada para Render/Gunicorn
"""
import sys
import os

# Agrega la carpeta al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from run import app, init_db

# Inicializa la base de datos al arrancar
init_db()

if __name__ == '__main__':
    app.run()
