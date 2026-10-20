import sys
from pathlib import Path
import click
from flask import Flask
from sqlalchemy import event, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Lab1.models import Author, Book, BookAuthor, Category, Review, User, db
from Lab1.routes.books import bp


@event.listens_for(Engine, "connect")
def enable_foreign_keys(connection, _):
    if connection.__class__.__module__ == "sqlite3":
        connection.execute("PRAGMA foreign_keys=ON")


def seed():
    """Repeatable demo data without deleting existing user data."""
    if db.session.scalar(select(Book.id).limit(1)) is not None:
        return
    if db.session.scalar(select(Category.id).limit(1)) is not None:
        raise click.ClickException("Database already contains data; seed requires a fresh database.")
    db.session.add_all([
        Category(id=1, name="Technology", slug="tech"),
        Category(id=2, name="Fiction", slug="fiction"),
        Category(id=3, name="Science", slug="science"),
        Author(id=1, name="An Nguyen", bio="API author"),
        Author(id=2, name="Binh Tran", bio="Database author"),
        User(id=1, email="an@example.com", display_name="An"),
    ])
    db.session.flush()
    for i in range(1, 31):
        db.session.add(Book(id=i, title=f"Book {(i - 1) // 2 + 1:02d}",
                            isbn=f"978000000{i:04d}", price_vnd=100000 + (i % 5) * 50000,
                            stock=i % 4, category_id=(i - 1) % 3 + 1))
        db.session.flush()
        db.session.add(BookAuthor(book_id=i, author_id=(i % 2) + 1, role="lead"))
    db.session.add(Review(book_id=1, user_id=1, rating=5, comment="Useful book"))
    db.session.commit()


def create_app(config=None, instance_path=None):
    path = Path(instance_path or Path(__file__).parent / "instance").resolve()
    app = Flask(__name__, instance_path=str(path))
    app.config.update(SQLALCHEMY_DATABASE_URI="sqlite:///bookstore.db",
                      SQLALCHEMY_TRACK_MODIFICATIONS=False)
    if config:
        app.config.update(config)
    path.mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    app.register_blueprint(bp)

    @app.errorhandler(HTTPException)
    def http_error(exc):
        return {"error": exc.name.lower().replace(" ", "_"), "message": exc.description,
                "field": getattr(exc, "field", [])}, exc.code

    @app.errorhandler(IntegrityError)
    def conflict(_):
        db.session.rollback()
        return {"error": "conflict", "message": "Duplicate value or resource still referenced"}, 409

    @app.cli.command("init-db")
    def init_db():
        db.create_all()
        click.echo("Database initialized.")

    @app.cli.command("seed")
    def seed_command():
        db.create_all()
        seed()
        click.echo("Seed ready: 30 books (duplicate prices/titles), 3 categories.")

    @app.get("/")
    def index():
        return {"service": "Week5 Bookstore", "books": "/api/v1/books"}

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5001)
