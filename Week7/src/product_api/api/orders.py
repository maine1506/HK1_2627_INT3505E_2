from flask import Blueprint
from sqlalchemy.orm import selectinload

from ..errors import NotFound
from ..extensions import db
from ..models import Order, OrderItem, Product
from ..schemas import OrderIn, OrderOut
from .common import json_body, pagination

orders_bp = Blueprint("orders", __name__, url_prefix="/api/v1/orders")


def orders_query():
    # To-many dùng selectinload; to-one dùng joinedload: tổng 2 SELECT.
    return db.select(Order).options(selectinload(Order.items).joinedload(OrderItem.product))


@orders_bp.post("")
def create_order():
    data = OrderIn().load(json_body())
    ids = [item["product_id"] for item in data["items"]]
    products = {p.id: p for p in db.session.scalars(
        db.select(Product).where(Product.id.in_(ids), Product.archived.is_(False))
    )}
    if len(products) != len(ids):
        raise NotFound("One or more products do not exist or are archived")
    order = Order(customer_name=data["customer_name"])
    order.items = [OrderItem(product=products[item["product_id"]], qty=item["qty"],
                            unit_price_cents=products[item["product_id"]].price_cents)
                   for item in data["items"]]
    db.session.add(order)
    db.session.commit()
    loaded = db.session.scalar(orders_query().where(Order.id == order.id))
    return OrderOut().dump(loaded), 201


@orders_bp.get("")
def list_orders():
    page, size = pagination()
    orders = db.session.scalars(orders_query().order_by(Order.id).offset((page - 1) * size).limit(size)).all()
    return {"items": OrderOut(many=True).dump(orders), "page": page, "size": size}


@orders_bp.get("/<int:id>")
def get_order(id):
    order = db.session.scalar(orders_query().where(Order.id == id))
    if order is None:
        raise NotFound("Order not found")
    return OrderOut().dump(order)
