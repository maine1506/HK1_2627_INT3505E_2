from marshmallow import Schema, ValidationError, fields, validate, validates_schema


class ProductIn(Schema):
    sku = fields.Str(required=True, validate=validate.Length(min=3, max=32))
    name = fields.Str(required=True, validate=[validate.Length(min=1, max=255), validate.Regexp(r".*\S", error="name must not be blank")])
    description = fields.Str(allow_none=True, validate=validate.Length(max=2000))
    price_cents = fields.Int(required=True, strict=True, validate=validate.Range(min=0))
    qty_in_stock = fields.Int(load_default=0, strict=True, validate=validate.Range(min=0))


class ProductPatch(Schema):
    name = fields.Str(validate=[validate.Length(min=1, max=255), validate.Regexp(r".*\S")])
    description = fields.Str(allow_none=True, validate=validate.Length(max=2000))
    price_cents = fields.Int(strict=True, validate=validate.Range(min=0))


class ProductOut(Schema):
    id = fields.Int()
    sku = fields.Str()
    name = fields.Str()
    description = fields.Str(allow_none=True)
    price_cents = fields.Int()
    qty_in_stock = fields.Int()
    archived = fields.Bool()


class ReserveIn(Schema):
    qty = fields.Int(required=True, strict=True, validate=validate.Range(min=1))


class OrderItemIn(ReserveIn):
    product_id = fields.Int(required=True, strict=True, validate=validate.Range(min=1))


class OrderIn(Schema):
    customer_name = fields.Str(required=True, validate=[validate.Length(min=1, max=255), validate.Regexp(r".*\S")])
    items = fields.List(fields.Nested(OrderItemIn), required=True, validate=validate.Length(min=1, max=100))

    @validates_schema
    def unique_products(self, data, **kwargs):
        ids = [item["product_id"] for item in data["items"]]
        if len(ids) != len(set(ids)):
            raise ValidationError("Each product may appear only once", "items")


class OrderItemOut(Schema):
    id = fields.Int()
    product_id = fields.Int()
    qty = fields.Int()
    unit_price_cents = fields.Int()
    product = fields.Nested(ProductOut)


class OrderOut(Schema):
    id = fields.Int()
    customer_name = fields.Str()
    created_at = fields.DateTime()
    items = fields.List(fields.Nested(OrderItemOut))
    total_cents = fields.Method("total")

    def total(self, obj):
        return sum(item.qty * item.unit_price_cents for item in obj.items)
