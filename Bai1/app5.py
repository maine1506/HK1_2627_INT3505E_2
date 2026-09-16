from flask import Flask, jsonify

app = Flask(__name__)

ORDERS = {
    "ord_001": {"id": "ord_001", "status": "pending", "total": 100000},
    "ord_002": {"id": "ord_002", "status": "shipped", "total": 200000},
    "ord_003": {"id": "ord_003", "status": "delivered", "total": 300000},
}

@app.route("/orders/<order_id>", methods=["DELETE"])
def delete_order(order_id):
    order = ORDERS.get(order_id)

    if order is None:
        return jsonify({"error": "not found"}), 404

    if order["status"] in ("shipped", "delivered"):
        return jsonify({"error": "cannot delete"}), 409

    ORDERS.pop(order_id, None)

    return "", 204

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
