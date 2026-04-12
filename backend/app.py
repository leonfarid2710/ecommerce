import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from flask import Flask, send_from_directory, request
from models.database import init_db
from routes.users    import users_bp
from routes.products import products_bp
from routes.cart     import cart_bp
from routes.checkout import checkout_bp

ALLOWED_ORIGINS = {
    'http://localhost:3000',
    'http://localhost:5173',
    'http://127.0.0.1:5000',
}

def create_app():
    app = Flask(
        __name__,
        static_folder=os.path.join(HERE, '..', 'frontend'),
        static_url_path='/static'
    )

    app.secret_key = os.environ.get('SECRET_KEY', 'starUp_dev_secret_2025!')
    app.config['DATABASE'] = os.path.join(HERE, 'ecommerce.db')

    @app.after_request
    def add_cors(response):
        origin = request.headers.get('Origin', '')
        if origin in ALLOWED_ORIGINS:
            response.headers['Access-Control-Allow-Origin']      = origin
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Access-Control-Allow-Headers']     = 'Content-Type'
            response.headers['Access-Control-Allow-Methods']     = 'GET,POST,PUT,DELETE,OPTIONS'
        return response

    @app.before_request
    def handle_preflight():
        if request.method == 'OPTIONS':
            from flask import Response
            return Response(status=200)

    with app.app_context():
        init_db(app)

    app.register_blueprint(users_bp,    url_prefix='/api/users')
    app.register_blueprint(products_bp, url_prefix='/api/products')
    app.register_blueprint(cart_bp,     url_prefix='/api/cart')
    app.register_blueprint(checkout_bp, url_prefix='/api/checkout')

    frontend_dir = os.path.join(HERE, '..', 'frontend')

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_frontend(path):
        target = os.path.join(frontend_dir, path)
        if path and os.path.exists(target):
            return send_from_directory(frontend_dir, path)
        return send_from_directory(frontend_dir, 'index.html')

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
