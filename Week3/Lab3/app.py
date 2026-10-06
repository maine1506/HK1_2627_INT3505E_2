import base64
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

orders = [
    {'id': 1, 'status': 'paid', 'customer_id': 1, 'total': 150000},
    {'id': 2, 'status': 'pending', 'customer_id': 2, 'total': 300000},
    {'id': 3, 'status': 'paid', 'customer_id': 1, 'total': 200000},
    {'id': 4, 'status': 'cancelled', 'customer_id': 3, 'total': 100000},
    {'id': 5, 'status': 'paid', 'customer_id': 2, 'total': 250000},
    {'id': 6, 'status': 'pending', 'customer_id': 1, 'total': 180000},
    {'id': 7, 'status': 'paid', 'customer_id': 3, 'total': 200000},
    {'id': 8, 'status': 'paid', 'customer_id': 1, 'total': 400000}
]


@app.get('/orders')
def get_orders():
    try:
        limit = int(request.args.get('limit', 5))
        customer_id = request.args.get('customer_id')
        if customer_id is not None:
            customer_id = int(customer_id)
            if customer_id <= 0:
                raise ValueError
        if not 1 <= limit <= 100:
            raise ValueError
    except ValueError:
        return jsonify(error='limit phai tu 1 den 100; customer_id phai la so nguyen duong'), 400

    status = request.args.get('status')
    if status is not None and status not in ['paid', 'pending', 'cancelled']:
        return jsonify(error='status khong hop le'), 400

    sort = request.args.get('sort', 'id')
    if sort not in ['id', '-id', 'total', '-total']:
        return jsonify(error='sort chi nhan id, -id, total, -total'), 400
    sort_field = sort.lstrip('-')
    descending = sort.startswith('-')

    fields = request.args.get('fields', 'id,status,customer_id,total').split(',')
    if any(field not in orders[0] for field in fields):
        return jsonify(error='fields chua ten truong khong hop le'), 400

    items = orders.copy()
    if status is not None:
        items = [order for order in items if order['status'] == status]
    if customer_id is not None:
        items = [order for order in items if order['customer_id'] == customer_id]
    items.sort(key=lambda order: (order[sort_field], order['id']), reverse=descending)

    query = [sort, status, customer_id]
    cursor = request.args.get('cursor')
    if cursor is not None:
        try:
            raw = base64.b64decode(cursor, altchars=b'-_', validate=True)
            saved = json.loads(raw)
            key = saved['key']
            if saved['query'] != query or len(key) != 2:
                raise ValueError
            if any(type(value) is not int for value in key):
                raise ValueError
            key = tuple(key)
        except (ValueError, KeyError, TypeError, UnicodeError):
            return jsonify(error='Cursor khong hop le hoac khong khop bo loc/sort'), 400

        if descending:
            items = [order for order in items if (order[sort_field], order['id']) < key]
        else:
            items = [order for order in items if (order[sort_field], order['id']) > key]

    page = items[:limit]
    next_cursor = None
    if len(items) > limit:
        last = page[-1]
        saved = {'key': [last[sort_field], last['id']], 'query': query}
        next_cursor = base64.urlsafe_b64encode(json.dumps(saved).encode()).decode()

    data = [{field: order[field] for field in fields} for order in page]
    return jsonify(data=data, next_cursor=next_cursor), 200
