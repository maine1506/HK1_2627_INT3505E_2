from flask import Flask, request, jsonify

app = Flask(__name__)

BOOKS = [
    {"id": "b1", "t": "Python co ban"},
    {"id": "b2", "t": "Lap trinh React nang cao"},
    {"id": "b3", "t": "Phan tich du lieu Python"}
]

def find_by_id(book_id):
    for b in BOOKS:
        if b["id"] == book_id:
            return b
    return None

@app.route("/books/<book_id>", methods=["GET"])
def get_book(book_id):
    book = find_by_id(book_id)
    if book is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(book), 200

@app.route("/items/<int:item_id>")
def get_item(item_id):
    return jsonify({"id": item_id}), 200

@app.route("/books", methods=["GET"])
def list_books():
    limit = int(request.args.get("limit", 20))
    q = request.args.get("q", "").strip().lower()

    items = [b for b in BOOKS if q in b["t"].lower()]

    items = items[:limit]

    return jsonify({"items": items}), 200

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)