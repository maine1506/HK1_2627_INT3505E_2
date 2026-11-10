from flask import Blueprint
from sqlalchemy import func, update
from sqlalchemy.exc import IntegrityError

from ..errors import Conflict, NotFound, OutOfStock
from ..extensions import db
from ..models import Product
from ..schemas import ProductIn, ProductOut, ProductPatch, ReserveIn
from .common import json_body, pagination

products_bp = Blueprint("products", __name__, url_prefix="/api/v1/products")


def active_product(id):
    product = db.session.get(Product, id)
    if product is None or product.archived:
        raise NotFound("Product not found")
    return product


@products_bp.get("")
def list_products():
    page, size = pagination()
    base = db.select(Product).where(Product.archived.is_(False))
    rows = db.session.scalars(base.order_by(Product.id).offset((page - 1) * size).limit(size)).all()
    total = db.session.scalar(db.select(func.count()).select_from(Product).where(Product.archived.is_(False)))
    return {"items": ProductOut(many=True).dump(rows), "page": page, "size": size, "total": total}


@products_bp.get("/<int:id>")
def get_product(id):
    return ProductOut().dump(active_product(id))


@products_bp.post("")
def create_product():
    product = Product(**ProductIn().load(json_body()))
    db.session.add(product)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise Conflict("sku already exists") from None
    return ProductOut().dump(product), 201


@products_bp.patch("/<int:id>")
def patch_product(id):
    data = ProductPatch().load(json_body(), partial=True)
    product = active_product(id)
    for key, value in data.items():
        setattr(product, key, value)
    db.session.commit()
    return ProductOut().dump(product)


@products_bp.delete("/<int:id>")
def delete_product(id):
    product = active_product(id)
    product.archived = True
    db.session.commit()
    return "", 204


@products_bp.post("/<int:id>/reserve")
def reserve_product(id):
    qty = ReserveIn().load(json_body())["qty"]
    active_product(id)
    # UPDATE có điều kiện: hai request đồng thời không thể làm tồn kho âm.
    result = db.session.execute(update(Product).where(
        Product.id == id, Product.archived.is_(False), Product.qty_in_stock >= qty
    ).values(qty_in_stock=Product.qty_in_stock - qty))
    if result.rowcount != 1:
        raise OutOfStock("Not enough stock")
    db.session.commit()
    return ProductOut().dump(active_product(id))
