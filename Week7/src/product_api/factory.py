import os

from flask import Flask

from .api.health import health_bp
from .api.orders import orders_bp
from .api.products import products_bp
from .config import DefaultConfig
from .errors import register_error_handlers
from .extensions import db, migrate
from .logging_config import configure


def create_app(config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config or os.environ.get("APP_CONFIG", DefaultConfig))
    app.config.from_prefixed_env("APP")
    os.makedirs(app.instance_path, exist_ok=True)
    db.init_app(app)
    migrate.init_app(app, db)
    app.register_blueprint(products_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(health_bp)
    register_error_handlers(app)
    configure(app)
    return app
