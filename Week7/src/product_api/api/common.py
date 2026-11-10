from flask import request
from werkzeug.exceptions import BadRequest


def json_body():
    if not request.is_json:
        raise BadRequest("Content-Type must be application/json")
    return request.get_json()


def pagination():
    try:
        page = max(1, int(request.args.get("page", 1)))
        size = min(100, max(1, int(request.args.get("size", 20))))
    except ValueError:
        raise BadRequest("page and size must be integers") from None
    return page, size
