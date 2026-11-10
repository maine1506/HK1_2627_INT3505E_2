# Bài tập buổi 7 — Backend Service

## Cấu trúc và đối chiếu yêu cầu

| Bài | Nội dung triển khai                                                                      | Mã nguồn                                                                                 |
| --- | ---------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| 1   | Product CRUD, phân trang, reserve, soft delete                                           | [products.py](src/product_api/api/products.py), [schemas.py](src/product_api/schemas.py) |
| 2   | Order có nhiều OrderItem; mỗi OrderItem liên kết một Product; blueprint `/api/v1/orders` | [models.py](src/product_api/models.py), [orders.py](src/product_api/api/orders.py)       |
| 3   | Docker nhiều stage, user không phải root, PostgreSQL, migration trước khi chạy Gunicorn  | [Dockerfile](Dockerfile), [docker-compose.yml](docker-compose.yml)                       |
| 4   | `/healthz` độc lập DB; `/ready` kiểm tra DB                                              | [health.py](src/product_api/api/health.py)                                               |
| 5   | pytest POST/GET và đếm SELECT để phát hiện N+1                                           | [test_api.py](tests/test_api.py)                                                         |

Ứng dụng dùng application factory, extension tách riêng, SQLAlchemy typed model, Marshmallow schema, Flask-Migrate, biến môi trường và log JSON. Các file chính: [factory.py](src/product_api/factory.py), [extensions.py](src/product_api/extensions.py), [config.py](src/product_api/config.py), [logging_config.py](src/product_api/logging_config.py), [migrations](migrations/), [.env.example](.env.example).

## Bài 1 — Product API

| Method | URL                               | Kết quả                                        |
| ------ | --------------------------------- | ---------------------------------------------- |
| POST   | `/api/v1/products`                | 201; SKU trùng: 409; dữ liệu không hợp lệ: 422 |
| GET    | `/api/v1/products?page=1&size=20` | 200; `items`, `page`, `size`, `total`          |
| GET    | `/api/v1/products/{id}`           | 200; không tồn tại/đã archive: 404             |
| PATCH  | `/api/v1/products/{id}`           | 200; chỉ cập nhật trường gửi lên               |
| POST   | `/api/v1/products/{id}/reserve`   | 200; thiếu hàng: 409                           |
| DELETE | `/api/v1/products/{id}`           | 204; đánh dấu `archived=true`                  |

SKU dài 3–32 ký tự, tên 1–255 ký tự và không trắng, giá nguyên không âm, tồn kho mặc định 0 và không âm. PATCH cho phép tên, mô tả, giá; không cho sửa SKU/tồn kho tùy ý. Phân trang chặn size trong 1–100 theo slide, tham số không phải số trả 400. Reserve nhận `qty >= 1`, giảm tồn kho bằng UPDATE có điều kiện. Các lỗi đều rollback session. List/get loại sản phẩm đã archive.

### Minh chứng 01 — Tạo và đọc sản phẩm

POST tạo bản ghi và trả 201 kèm ID. GET lấy chi tiết; GET danh sách có size=1 cho thấy phân trang và tổng số bản ghi. ORM truy cập DB, schema serialize model thành JSON.

![Tạo sản phẩm HTTP 201](images\01-create.png)
![Tạo sản phẩm HTTP 201](images\02-create.png)

![Danh sách phân trang và chi tiết sản phẩm](images\01-read.png)
![Danh sách phân trang và chi tiết sản phẩm](images\02-read.png)

### Minh chứng 02 — Xử lý lỗi

Gửi lại cùng SKU kích hoạt unique constraint, rollback và trả 409. SKU quá ngắn, tên rỗng, giá âm bị schema từ chối với 422 trước khi ghi DB; `detail` chỉ ra từng trường sai.

![SKU trùng trả 409](images\01-conflict.png)

![Dữ liệu sai trả 422](images\01-validation.png)

### Minh chứng 03 — Reserve và PATCH

Tồn kho ban đầu 5; reserve 2 còn 3. Reserve 99 trả 409 và không trừ kho. PATCH chỉ gửi tên: tên thay đổi, giá và tồn kho vẫn giữ nguyên.

![Reserve thành công và không đủ hàng](images\01-reserve.png)
![Reserve thành công và không đủ hàng](images\02-reserve.png)

![PATCH chỉ thay đổi trường được gửi](images\01-patch.png)

### Minh chứng 04 — Soft delete

DELETE trả 204 không có body. Bản ghi vẫn trong DB với `archived=true`, GET chi tiết trả 404 và danh sách loại sản phẩm đó. Pytest kiểm tra trực tiếp cờ archive để phân biệt với xóa vật lý.

![DELETE 204 và GET 404 sau khi archive](images\01-soft-delete.png)
![DELETE 204 và GET 404 sau khi archive](images\02-soft-delete.png)

![Danh sách loại sản phẩm đã archive](images\03-soft-delete.png)

## Bài 2 — Order và OrderItem

Quan hệ: `Order 1—N OrderItem N—1 Product`. Không đặt một `product_id` duy nhất trong Order. OrderItem có hai khóa ngoại, số lượng dương và đơn giá chụp tại lúc tạo đơn. Đơn giá này giữ lịch sử khi giá Product thay đổi. Một sản phẩm chỉ xuất hiện một lần trong cùng đơn.

Blueprint riêng cung cấp POST/GET `/api/v1/orders` và GET `/api/v1/orders/{id}`. POST nhận `customer_name` và danh sách `items` gồm `product_id`, `qty`. Sản phẩm không tồn tại hoặc archive trả 404; danh sách rỗng hoặc lặp sản phẩm trả 422. Tạo đơn commit một lần cho cả Order và các OrderItem.

Quy ước bổ sung vì đề không mô tả luồng thanh toán: POST Order chỉ ghi đơn và chi tiết, **không tự reserve/trừ kho**; việc giảm kho thuộc endpoint reserve của Lab 1. Không gọi cả hai để giả định đây là quy trình thanh toán hoàn chỉnh. GET đơn vẫn đọc sản phẩm archive để bảo toàn lịch sử.

### Minh chứng 05 — Đơn hàng nhiều sản phẩm

Tạo một Order có 2 OrderItem: bàn phím số lượng 2, đơn giá 150000; chuột số lượng 1, đơn giá 50000. Response 201 có hai sản phẩm và tổng `350000`. GET trả cấu trúc lồng Order → items → product.

![POST Order có hai OrderItem](images\01-order-create.png)

![GET Order và dữ liệu Product lồng nhau](images\01-order-get.png)
![GET Order và dữ liệu Product lồng nhau](images\02-order-get.png)

## Bài 3 — Docker và migration

[Dockerfile](Dockerfile) dùng Python 3.12 slim, cài package trong venv ở builder, copy sang runtime, chạy bằng user `app` và Gunicorn 2 worker. [docker-compose.yml](docker-compose.yml) gồm PostgreSQL 16, tiến trình migration chạy một lần và API. PostgreSQL healthy → migration thành công → API khởi động. Volume `pgdata` giữ dữ liệu qua các lần restart. Không cần sửa địa chỉ DB khi chuyển sang máy khác; cấu hình nội bộ đã có sẵn cho lab, yêu cầu Docker Compose v2 và cổng 5000 trống.

Migration đã được sinh và đọc lại: tạo ba bảng, PK/FK, index SKU unique, các check constraint. Chạy `flask db upgrade`, không dùng `create_all` để thay migration trong vận hành. `create_all` chỉ dùng ở fixture pytest cho DB tạm.

## Bài 4 — Health check tách biệt

`/healthz` trả 200 nếu process phục vụ được request và không truy vấn DB. `/ready` chạy `SELECT 1`: trả 200 với `checks.db=ok`, hoặc 503 với `checks.db=err`. Giống slide, probe này kiểm tra kết nối DB; migration được bảo đảm bằng thứ tự khởi động Compose.

### Minh chứng — Hai trạng thái health check

Khi DB hoạt động, cả hai endpoint trả 200. Khi dừng container DB, liveness vẫn 200, readiness 503; đây là lý do không gộp hai endpoint. Có pytest mô phỏng lỗi DB nếu chưa dùng được Docker.

![Liveness 200 và readiness 200](images\01-health.png)
![Liveness 200 và readiness 200](images\02-health.png)

## Bài 5 — Pytest và eager loading

[tests](tests/) dùng factory với SQLite in-memory riêng cho từng test. Kiểm tra POST Product, duplicate SKU, validation, CRUD/reserve, phân trang, soft delete, POST Order nhiều sản phẩm, đơn giá lịch sử và health check khi DB lỗi.

GET Order dùng `selectinload(Order.items).joinedload(OrderItem.product)`: SELECT đầu lấy Order; SELECT thứ hai lấy OrderItem JOIN Product cho các Order. Test gắn listener `before_cursor_execute` trong đúng request GET, đếm SELECT thật và tháo listener sau khi đo. Test cho cả 1 và 10 Order (3 sản phẩm/đơn), kỳ vọng **2 SELECT** ở mỗi trường hợp. Không suy ra N+1 chỉ từ JSON; ảnh pytest mới là bằng chứng số query. Phân trang tối đa 100 đơn giữ tập ID của ví dụ trong một batch.

### Minh chứng — Kết quả kiểm thử

Kết quả đã chạy ở môi trường thực hiện bài: **8 passed**, Python 3.14.10, SQLite. Hai trường hợp eager loading in `SELECT queries=2`. Migration `upgrade` thành công và `db check` không phát hiện thay đổi còn thiếu. Script demo đã gọi **17 request HTTP thật**, tất cả trả đúng status mong đợi. Docker/PostgreSQL chưa chạy được trong môi trường này vì không tìm thấy Docker CLI; ảnh Docker cần chụp sau khi chạy theo hướng dẫn.

![Pytest toàn bộ thành công](images\11-pytest.png)

![Đếm SELECT: 1 và 10 đơn đều chỉ 2 truy vấn](images\12-eager-loading.png)
