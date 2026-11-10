from flask import jsonify
from marshmallow import ValidationError
from werkzeug.exceptions import HTTPException

from .extensions import db


class ApiError(Exception):
    status_code = 500
    code = "internal_error"

    def __init__(self, message):
        super().__init__(message)
        self.message = message


class NotFound(ApiError):
    status_code = 404
    code = "not_found"


class Conflict(ApiError):
    status_code = 409
    code = "conflict"


class OutOfStock(Conflict):
    code = "out_of_stock"


def register_error_handlers(app):
    def response(code, message, status, detail=None):
        db.session.rollback()
        return jsonify(code=code, message=message, error=code,
                       detail=message if detail is None else detail), status

    @app.errorhandler(ApiError)
    def business(err):
        return response(err.code, err.message, err.status_code)

    @app.errorhandler(ValidationError)
    def validation(err):
        return response("validation_error", "Invalid input", 422, err.messages)

    @app.errorhandler(HTTPException)
    def http(err):
        return response(err.name.lower().replace(" ", "_"), err.description, err.code)

    @app.errorhandler(Exception)
    def unexpected(err):
        app.logger.exception("unhandled")
        return response("internal_error", "Unexpected server error", 500)
