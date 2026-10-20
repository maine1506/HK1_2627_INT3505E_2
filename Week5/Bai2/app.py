import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Lab1.app import create_app as base_app
from Lab2.app import configure_cursor
from Lab2.pagination import list_page


def create_app(config=None):
    app = base_app(config, Path(__file__).parent / "instance")
    configure_cursor(app)
    app.view_functions["api.list_books"] = lambda: list_page(multi=True)
    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5003)
