import os
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Lab1.app import create_app as base_app
from Lab2.pagination import list_page


def configure_cursor(app):
    if not app.config.get("SECRET_KEY"):
        key_path = Path(app.instance_path) / "cursor.key"
        if not key_path.exists():
            key_path.write_text(secrets.token_hex(32), encoding="ascii")
        app.config["SECRET_KEY"] = os.environ.get("CURSOR_SECRET") or key_path.read_text("ascii")


def create_app(config=None):
    app = base_app(config, Path(__file__).parent / "instance")
    configure_cursor(app)
    app.view_functions["api.list_books"] = list_page
    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5002)
