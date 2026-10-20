"""Whitelisted sorting and signed, context-bound composite cursors."""
from flask import current_app, request
from itsdangerous import BadData, URLSafeSerializer
from sqlalchemy import and_, or_, select, func
from werkzeug.exceptions import BadRequest
from Lab1.models import Book, Category, db
from Lab1.routes.books import integer_arg

SORT = {"id": Book.id, "price": Book.price_vnd, "title": Book.title, "stock": Book.stock}


def parse_sort(raw, multi=False):
    tokens = raw.split(",")
    allowed = SORT if multi else {"id": Book.id, "price": Book.price_vnd}
    if not multi and len(tokens) != 1:
        raise BadRequest("bad_sort: Lab2 accepts one sort field")
    result, seen = [], set()
    for token in tokens:
        desc = token.startswith("-")
        name = token[1:] if desc else token
        if name not in allowed or name in seen:
            raise BadRequest("bad_sort: unknown or duplicate sort field")
        seen.add(name)
        result.append((name, allowed[name], desc))
    if "id" in seen and result[-1][0] != "id":
        raise BadRequest("bad_sort: id must be the final tie-breaker")
    if "id" not in seen:
        result.append(("id", Book.id, result[-1][2]))
    return result


def signer():
    return URLSafeSerializer(current_app.config["SECRET_KEY"], salt="week5-cursor-v1")


def apply_cursor(query, raw, sort, filters, keys):
    if raw is None:
        return query
    if not raw or len(raw) > 4096:
        raise BadRequest("bad_cursor")
    try:
        state = signer().loads(raw)
    except BadData:
        raise BadRequest("bad_cursor: malformed token or invalid signature") from None
    if not isinstance(state, dict) or state.get("version") != 1:
        raise BadRequest("bad_cursor: unsupported version")
    if state.get("s") != sort:
        raise BadRequest("sort_chg: restart pagination after changing sort")
    if state.get("filters") != filters:
        raise BadRequest("filter_chg: restart pagination after changing filters")
    values = state.get("values")
    if not isinstance(values, list) or len(values) != len(keys):
        raise BadRequest("bad_cursor: wrong key count")
    for (name, _, _), value in zip(keys, values):
        expected = str if name == "title" else int
        if type(value) is not expected or (expected is int and not 0 <= value <= 9223372036854775807):
            raise BadRequest("bad_cursor: wrong key type or range")
    # Lexicographic comparison handles mixed ASC/DESC, unlike one tuple operator.
    alternatives = []
    for index, (_, column, desc) in enumerate(keys):
        prefix = [keys[j][1] == values[j] for j in range(index)]
        comparison = column < values[index] if desc else column > values[index]
        alternatives.append(and_(*prefix, comparison))
    return query.where(or_(*alternatives))


def build_response(items, limit, sort, filters, keys, more):
    next_cursor = None
    if items and more:
        last = items[-1]
        next_cursor = signer().dumps({"version": 1, "s": sort, "filters": filters,
                                      "values": [getattr(last, col.key) for _, col, _ in keys]})
    return {"data": [b.to_dict() for b in items],
            "page": {"next": next_cursor, "more": more, "limit": limit}}


def list_page(multi=False):
    allowed = {"sort", "category", "limit", "cursor"}
    if multi:
        allowed |= {"strategy", "offset", "genre"}
    if set(request.args) - allowed:
        raise BadRequest("Unknown query parameter")
    if any(len(request.args.getlist(k)) != 1 for k in request.args):
        raise BadRequest("Repeated query parameter")
    strategy = request.args.get("strategy", "cursor")
    if strategy not in {"cursor", "offset"}:
        raise BadRequest("strategy must be offset or cursor")
    if strategy == "offset" and "cursor" in request.args:
        raise BadRequest("cursor is not allowed with offset strategy")
    if strategy == "cursor" and "offset" in request.args:
        raise BadRequest("offset is not allowed with cursor strategy")
    limit = integer_arg("limit", 20, 1, 100)
    sort = request.args.get("sort", "-id")
    keys = parse_sort(sort, multi)
    filters = {}
    query = select(Book)
    if "category" in request.args:
        category = integer_arg("category", 0, 1)
        filters["category"] = category
        query = query.where(Book.category_id == category)
    if "genre" in request.args:
        genre = request.args["genre"]
        if not genre or len(genre) > 100:
            raise BadRequest("genre must be a nonempty category slug")
        filters["genre"] = genre
        query = query.join(Category).where(Category.slug == genre)
    if strategy == "offset":
        offset = integer_arg("offset", 0)
        total = db.session.scalar(select(func.count()).select_from(query.subquery()))
        query = query.order_by(*[col.desc() if desc else col.asc() for _, col, desc in keys])
        rows = db.session.scalars(query.offset(offset).limit(limit)).all()
        return {"data": [b.to_dict() for b in rows], "pagination": {
            "strategy": "offset", "offset": offset, "limit": limit, "total": total,
            "has_next": offset + limit < total}}
    query = apply_cursor(query, request.args.get("cursor"), sort, filters, keys)
    query = query.order_by(*[col.desc() if desc else col.asc() for _, col, desc in keys])
    rows = db.session.scalars(query.limit(limit + 1)).all()
    return build_response(rows[:limit], limit, sort, filters, keys, len(rows) > limit)
