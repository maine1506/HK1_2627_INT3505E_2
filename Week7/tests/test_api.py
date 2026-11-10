import pytest
from sqlalchemy import event
from sqlalchemy.exc import OperationalError

from product_api.extensions import db
from product_api.models import Product


def product(client, sku="SP-001", stock=10):
    response = client.post("/api/v1/products", json={
        "sku": sku, "name": "Keyboard", "price_cents": 150000, "qty_in_stock": stock})
    assert response.status_code == 201
    return response.json


def test_post_product_duplicate_and_validation(client):
    p = product(client)
    assert p["qty_in_stock"] == 10
    duplicate = client.post("/api/v1/products", json={"sku": p["sku"], "name": "Other", "price_cents": 0})
    assert duplicate.status_code == 409
    assert duplicate.json["error"] == "conflict"
    invalid = client.post("/api/v1/products", json={"sku": "X", "name": "", "price_cents": -1})
    assert invalid.status_code == 422
    assert set(invalid.json["detail"]) == {"sku", "name", "price_cents"}
    product(client, "SP-002")  # rollback sau conflict không làm hỏng request tiếp theo.


def test_product_crud_reserve_and_soft_delete(client, app):
    p = product(client, stock=3)
    url = f'/api/v1/products/{p["id"]}'
    assert client.get(url).status_code == 200
    assert client.post(url + "/reserve", json={"qty": 2}).json["qty_in_stock"] == 1
    assert client.post(url + "/reserve", json={"qty": 2}).status_code == 409
    assert client.get(url).json["qty_in_stock"] == 1
    assert client.post(url + "/reserve", json={"qty": 0}).status_code == 422
    changed = client.patch(url, json={"name": "New name"})
    assert changed.json["name"] == "New name"
    assert changed.json["price_cents"] == p["price_cents"]
    assert client.delete(url).status_code == 204
    for response in (client.get(url), client.patch(url, json={"name": "x"}),
                     client.post(url + "/reserve", json={"qty": 1})):
        assert response.status_code == 404
    assert client.get("/api/v1/products").json["total"] == 0
    with app.app_context():
        assert db.session.get(Product, p["id"]).archived is True


def test_pagination_and_bad_requests(client):
    product(client)
    product(client, "SP-002")
    page = client.get("/api/v1/products?page=2&size=1").json
    assert page["total"] == 2 and len(page["items"]) == 1
    assert page["items"][0]["sku"] == "SP-002"
    assert client.get("/api/v1/products?page=abc").status_code == 400
    assert client.post("/api/v1/products", data="{bad", content_type="application/json").status_code == 400
    assert client.post("/api/v1/products", data="text").status_code == 400
    assert client.get("/api/v1/products/9999").status_code == 404


def test_post_order_multiple_products_and_price_snapshot(client):
    first = product(client)
    second = product(client, "SP-002")
    response = client.post("/api/v1/orders", json={"customer_name": "Phuong", "items": [
        {"product_id": first["id"], "qty": 2}, {"product_id": second["id"], "qty": 1}]})
    assert response.status_code == 201
    assert len(response.json["items"]) == 2
    assert response.json["total_cents"] == 450000
    client.patch(f'/api/v1/products/{first["id"]}', json={"price_cents": 1})
    client.delete(f'/api/v1/products/{second["id"]}')
    saved = client.get(f'/api/v1/orders/{response.json["id"]}')
    assert saved.status_code == 200 and saved.json["total_cents"] == 450000
    assert len(saved.json["items"]) == 2  # Vẫn đọc được lịch sử sản phẩm đã archive.


@pytest.mark.parametrize("count", [1, 10])
def test_get_orders_eager_loading_two_selects(client, app, count):
    ids = [product(client, f"SP-{i:03}")["id"] for i in range(3)]
    for _ in range(count):
        assert client.post("/api/v1/orders", json={"customer_name": "Test", "items": [
            {"product_id": id, "qty": 1} for id in ids]}).status_code == 201
    selects = []

    def record(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            selects.append(statement)

    with app.app_context():
        engine = db.engine
    event.listen(engine, "before_cursor_execute", record)
    try:
        response = client.get("/api/v1/orders?size=100")
    finally:
        event.remove(engine, "before_cursor_execute", record)
    assert response.status_code == 200
    assert len(response.json["items"]) == count
    assert all(len(order["items"]) == 3 for order in response.json["items"])
    assert response.json["items"][0]["items"][0]["product"]["sku"]
    print(f"orders={count}; products/order=3; SELECT queries={len(selects)}")
    assert len(selects) == 2


def test_invalid_orders_are_not_saved(client):
    p = product(client)
    for items, status in [([], 422), ([{"product_id": 9999, "qty": 1}], 404),
                          ([{"product_id": p["id"], "qty": 1}] * 2, 422)]:
        assert client.post("/api/v1/orders", json={"customer_name": "Test", "items": items}).status_code == status
    assert client.get("/api/v1/orders").json["items"] == []


def test_health_checks_and_database_failure(client, monkeypatch):
    assert client.get("/healthz").status_code == 200
    assert client.get("/ready").json == {"status": "ok", "checks": {"db": "ok"}}

    def unavailable(*args, **kwargs):
        raise OperationalError("SELECT 1", {}, Exception("DB unavailable"))

    monkeypatch.setattr(db.session, "execute", unavailable)
    assert client.get("/healthz").status_code == 200
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json["checks"]["db"] == "err"
