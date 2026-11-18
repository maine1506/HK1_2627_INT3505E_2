"""Practice 1: URI path versioning with Flask Blueprints."""

from flask import Flask, send_from_directory
from blueprints.v1 import bp as v1_bp
from blueprints.v2 import bp as v2_bp


def create_app():
    app = Flask(__name__)
    app.json.ensure_ascii = False
    app.config['V1_SUNSET'] = 'Thu, 31 Dec 2026 23:59:59 GMT'
    # Registration prefixes override Blueprint prefixes, so include /users here.
    app.register_blueprint(v1_bp, url_prefix='/api/v1/users')
    app.register_blueprint(v2_bp, url_prefix='/api/v2/users')

    @app.get('/openapi.json')
    def openapi():
        return send_from_directory(app.root_path, 'openapi.json')

    return app


app = create_app()

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)
