from flask import Flask, request, jsonify, make_response

app = Flask(__name__)

BOOKS = [
    {"id": 11, "title": "Clean Code", "author": "Martin"},
    {"id": 12, "title": "Clean Architecture", "author": "Martin"},
    {"id": 13, "title": "1984", "author": "Orwell"},
    {"id": 14, "title": "Animal Farm", "author": "Orwell"},
    {"id": 15, "title": "The Pragmatic Programmer", "author": "Thomas"}
]

DEFAULT_SIZE, MAX_SIZE = 20, 100

# ─── list + filter + paginate + links
@app.get("/books")
def list_books():
    try:
        page = int(request.args.get("page", 1))
        size = int(request.args.get("size", DEFAULT_SIZE))
    except ValueError:
        return jsonify(error="page and size must be int"), 400
    
    page = max(page, 1)
    size = max(min(size, MAX_SIZE), 1)

    # filter: author chính xác, q tìm trong title
    flt = BOOKS
    a = request.args.get("author", "").lower()
    if a:
        flt = [b for b in flt if b["author"].lower() == a]

    q = request.args.get("q", "").lower()
    if q:
        flt = [b for b in flt if q in b["title"].lower()]

    # paginate
    total = len(flt)                     # tong so sach sau khi filtered
    last = (total + size - 1) // size    # tong so trang/trang cuoi cung
    start = (page - 1) * size            # STT cua quyen sach dau tien o trang = page
    end = start + size                   # STT cua quyen sach cuoi cung o trang = page
    items = flt[start:end]               # loc ra cac quyen sach tu vi tri start toi end

    # HATEOAS links
    def u(p):
        return f"/books?page={p}&size={size}"

    links = {
        "self": {"href": u(page)},
        "first": {"href": u(1)},
        "last": {"href": u(max(last, 1))}
    }

    if page > 1:
        links["prev"] = {"href": u(page - 1)}
    if end < total:
        links["next"] = {"href": u(page + 1)}

    body = {
        "data": items,
        "pagination": {
            "page": page,
            "size": size,
            "total": total,
            "total_pages": last
        },
        "_links": links
    }

    resp = make_response(jsonify(body), 200)
    resp.headers["Cache-Control"] = "public, max-age=30"
    return resp