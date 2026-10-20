import json
from pathlib import Path
from flask import Blueprint, request
from jsonschema import Draft202012Validator, FormatChecker
from sqlalchemy import func, select
from werkzeug.exceptions import BadRequest, Conflict, NotFound
from Lab1.models import Author, Book, BookAuthor, Category, Review, User, db

bp = Blueprint("api", __name__, url_prefix="/api/v1")
BOOK_SCHEMA = json.loads((Path(__file__).parents[1] / "schemas/book.json").read_text("utf-8-sig"))


def validate(schema):
    payload = request.get_json(silent=True)
    errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(payload))
    if errors:
        exc = BadRequest(errors[0].message)
        exc.field = list(errors[0].path)
        raise exc
    return payload


def integer_arg(name, default, minimum=0, maximum=None):
    raw = request.args.get(name)
    try:
        value = default if raw is None else int(raw)
    except ValueError:
        raise BadRequest(f"{name} must be an integer") from None
    if value < minimum:
        raise BadRequest(f"{name} must be >= {minimum}")
    return min(value, maximum) if maximum is not None else value


def get_book(book_id):
    if not book_id.startswith("book_") or not book_id[5:].isdigit():
        raise NotFound("Use book_<id>, for example book_1")
    return db.get_or_404(Book, int(book_id[5:]))


@bp.get("/books")
def list_books():
    offset, limit = integer_arg("offset", 0), integer_arg("limit", 20, 1, 100)
    total = db.session.scalar(select(func.count(Book.id)))
    books = db.session.scalars(select(Book).order_by(Book.id).offset(offset).limit(limit)).all()
    return {"data": [b.to_dict() for b in books], "pagination": {
        "offset": offset, "limit": limit, "total": total, "has_next": offset + limit < total}}


@bp.post("/books")
def create_book():
    payload = validate(BOOK_SCHEMA)
    db.get_or_404(Category, payload["category_id"])
    book = Book(**payload)
    db.session.add(book)
    db.session.commit()
    return book.to_dict(), 201, {"Location": f"/api/v1/books/book_{book.id}"}


@bp.route("/books/<book_id>", methods=["GET", "PUT", "DELETE"])
def book_detail(book_id):
    book = get_book(book_id)
    if request.method == "DELETE":
        db.session.delete(book)
        db.session.commit()
        return "", 204
    if request.method == "PUT":
        payload = validate(BOOK_SCHEMA)
        db.get_or_404(Category, payload["category_id"])
        for key, value in payload.items():
            setattr(book, key, value)
        db.session.commit()
    return book.to_dict()


def object_schema(properties):
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


TEXT = {"type": "string", "minLength": 1, "maxLength": 100, "pattern": "\\S"}
RESOURCE_CONFIG = {
    "authors": (Author, object_schema({"name": TEXT, "bio": {"type": "string"}})),
    "categories": (Category, object_schema({"name": TEXT, "slug": {
        "type": "string", "maxLength": 100, "pattern": "^[a-z0-9]+(-[a-z0-9]+)*$"}})),
    "users": (User, object_schema({"email": {"type": "string", "format": "email", "maxLength": 254},
                                  "display_name": TEXT})),
}


@bp.route("/<resource>", methods=["GET", "POST"])
def resources(resource):
    if resource not in RESOURCE_CONFIG:
        raise NotFound()
    model, schema = RESOURCE_CONFIG[resource]
    if request.method == "POST":
        obj = model(**validate(schema))
        db.session.add(obj)
        db.session.commit()
        return obj.to_dict(), 201, {"Location": f"/api/v1/{resource}/{obj.id}"}
    offset, limit = integer_arg("offset", 0), integer_arg("limit", 20, 1, 100)
    rows = db.session.scalars(select(model).order_by(model.id).offset(offset).limit(limit)).all()
    total = db.session.scalar(select(func.count(model.id)))
    return {"data": [r.to_dict() for r in rows], "pagination": {
        "offset": offset, "limit": limit, "total": total}}


@bp.route("/<resource>/<int:resource_id>", methods=["GET", "PUT", "DELETE"])
def resource_detail(resource, resource_id):
    if resource not in RESOURCE_CONFIG:
        raise NotFound()
    model, schema = RESOURCE_CONFIG[resource]
    obj = db.get_or_404(model, resource_id)
    if request.method == "DELETE":
        db.session.delete(obj)
        db.session.commit()
        return "", 204
    if request.method == "PUT":
        for key, value in validate(schema).items():
            setattr(obj, key, value)
        db.session.commit()
    return obj.to_dict()


@bp.route("/books/<book_id>/authors", methods=["GET", "POST"])
def book_authors(book_id):
    book = get_book(book_id)
    if request.method == "GET":
        return {"data": book.to_dict()["authors"]}
    payload = validate(object_schema({"author_id": {"type": "integer", "minimum": 1},
                                      "role": {"enum": ["lead", "co", "ed"]}}))
    db.get_or_404(Author, payload["author_id"])
    if db.session.get(BookAuthor, (book.id, payload["author_id"])) is not None:
        raise Conflict("Author already linked to book")
    db.session.add(BookAuthor(book_id=book.id, **payload))
    db.session.commit()
    return payload, 201


@bp.delete("/books/<book_id>/authors/<int:author_id>")
def remove_author(book_id, author_id):
    book = get_book(book_id)
    link = db.get_or_404(BookAuthor, (book.id, author_id))
    db.session.delete(link)
    db.session.commit()
    return "", 204


@bp.get("/authors/<int:author_id>/books")
def author_books(author_id):
    db.get_or_404(Author, author_id)
    offset, limit = integer_arg("offset", 0), integer_arg("limit", 20, 1, 100)
    query = select(Book).join(BookAuthor).where(BookAuthor.author_id == author_id)
    rows = db.session.scalars(query.order_by(Book.id).offset(offset).limit(limit)).all()
    return {"data": [b.to_dict() for b in rows], "pagination": {"offset": offset, "limit": limit}}


REVIEW_SCHEMA = object_schema({"rating": {"type": "integer", "minimum": 1, "maximum": 5},
                               "comment": {"type": "string"},
                               "user_id": {"type": "integer", "minimum": 1}})


@bp.route("/books/<book_id>/reviews", methods=["GET", "POST"])
def reviews(book_id):
    book = get_book(book_id)
    if request.method == "POST":
        payload = validate(REVIEW_SCHEMA)
        db.get_or_404(User, payload["user_id"])
        review = Review(book_id=book.id, **payload)
        db.session.add(review)
        db.session.commit()
        return review.to_dict(), 201
    offset, limit = integer_arg("offset", 0), integer_arg("limit", 20, 1, 100)
    rows = db.session.scalars(select(Review).where(Review.book_id == book.id)
                             .order_by(Review.id).offset(offset).limit(limit)).all()
    return {"data": [r.to_dict() for r in rows], "pagination": {"offset": offset, "limit": limit}}


@bp.route("/books/<book_id>/reviews/<int:review_id>", methods=["GET", "PUT", "DELETE"])
def review_detail(book_id, review_id):
    book = get_book(book_id)
    review = db.get_or_404(Review, review_id)
    if review.book_id != book.id:
        raise NotFound()
    if request.method == "DELETE":
        db.session.delete(review)
        db.session.commit()
        return "", 204
    if request.method == "PUT":
        payload = validate(REVIEW_SCHEMA)
        db.get_or_404(User, payload["user_id"])
        for key, value in payload.items():
            setattr(review, key, value)
        db.session.commit()
    return review.to_dict()

