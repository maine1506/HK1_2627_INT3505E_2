"""Gọi HTTP thật và dừng sau từng minh chứng nếu có --pause."""
import argparse
import json
import time
import urllib.error
import urllib.request


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:5000")
    parser.add_argument("--pause", action="store_true")
    args = parser.parse_args()

    def call(title, method, path, expected, body=None):
        print(f"\n{'=' * 65}\n{title}\n{method} {path}")
        if body is not None:
            print("Request:", json.dumps(body, ensure_ascii=False))
        req = urllib.request.Request(args.base_url + path, method=method,
                                     data=None if body is None else json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            response = urllib.request.urlopen(req, timeout=15)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            status = response.status
            raw = response.read().decode()
        result = json.loads(raw) if raw else None
        print(f"HTTP {status}")
        print(json.dumps(result, indent=2, ensure_ascii=False) if result is not None else "(empty body)")
        assert status == expected, f"Expected {expected}, got {status}"
        if args.pause:
            input("Chup man hinh, sau do nhan Enter de tiep tuc...")
        return result

    prefix = "/api/v1/products"
    sku = "DEMO-" + str(time.time_ns())
    body = {"sku": sku, "name": "Keyboard", "price_cents": 150000, "qty_in_stock": 5}
    first = call("01 - Tao san pham", "POST", prefix, 201, body)
    id = first["id"]
    second = call("02 - Tao san pham thu hai", "POST", prefix, 201,
                  {**body, "sku": sku + "B", "name": "Mouse", "price_cents": 50000})
    call("03 - Phan trang", "GET", prefix + "?page=1&size=1", 200)
    call("04 - Chi tiet", "GET", f"{prefix}/{id}", 200)
    call("05 - SKU trung", "POST", prefix, 409, body)
    call("06 - Validation", "POST", prefix, 422, {"sku": "X", "name": "", "price_cents": -1})
    call("07 - Reserve thanh cong: con 3", "POST", f"{prefix}/{id}/reserve", 200, {"qty": 2})
    call("08 - Reserve vuot ton kho", "POST", f"{prefix}/{id}/reserve", 409, {"qty": 99})
    call("09 - PATCH: chi doi ten", "PATCH", f"{prefix}/{id}", 200, {"name": "Keyboard Pro"})
    order = call("10 - Order gom hai OrderItem", "POST", "/api/v1/orders", 201,
                 {"customer_name": "Mai Phuong", "items": [
                     {"product_id": id, "qty": 2}, {"product_id": second["id"], "qty": 1}]})
    call("11 - GET orders eager loading", "GET", "/api/v1/orders?size=100", 200)
    call("12 - GET chi tiet order", "GET", f'/api/v1/orders/{order["id"]}', 200)
    call("13 - Soft delete", "DELETE", f"{prefix}/{id}", 204)
    call("14 - San pham da an", "GET", f"{prefix}/{id}", 404)
    call("15 - Danh sach sau xoa", "GET", prefix + "?size=100", 200)
    call("16 - Liveness", "GET", "/healthz", 200)
    call("17 - Readiness", "GET", "/ready", 200)
    print("\nPASS: all 17 HTTP requests returned expected statuses.")


if __name__ == "__main__":
    main()
