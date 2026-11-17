# Lab 3 — Kiểm thử Books API bằng Postman/Newman

## Yêu cầu và phần đã làm

Thực hiện theo mục Lab 3 trong [README](../README.md).

Giữ 5 request CRUD có sẵn: list → create → get → update → delete.
Create lưu `book_id` vào collection variables cho các request tiếp theo.
Thêm folder `error-cases` với các kiểm tra:

| Request                       | Kết quả cần kiểm tra                                                                                                        |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| POST `/books` chỉ có `author` | HTTP 400; `code` là `VALIDATION_ERROR`; `message` là `Invalid book data`; `errors` có field `title` và thông báo không rỗng |
| GET `/books/9999`             | HTTP 404; `code` là `NOT_FOUND`; `message` là `Book not found`                                                              |

Hai request lỗi lần lượt có 4 và 3 `pm.test`, đáp ứng yêu cầu ít nhất 2 test/request.
Đồng bộ [collection gốc](../books-api.postman_collection.json) với
[bản trong postman](../postman/books-api.postman_collection.json).

## Kết quả thực chạy

- Newman 6.2.1, Node.js 22.14.0, API tại `http://127.0.0.1:5000`.
- SQLite trong bộ nhớ, ban đầu rỗng, không thay đổi CSDL đã có.
- **1 iteration, 7 requests, 17 assertions, 0 failures; thời gian 911 ms.**
- [JUnit report](junit.xml) và [log Newman](lab03-newman.log).

HTTP 400 và 404 là kết quả mong đợi của error cases, không phải test failure.
GET `/books/9999` giả định ID 9999 không tồn tại trong CSDL kiểm thử.

## Chạy lại

Chạy từ thư mục gốc starter. Cần Node.js/npm để cài Newman:

```powershell
npm install -g newman@6.2.1
```

Terminal 1 — chạy API dùng CSDL tạm:

```powershell
cd D:\ServiceOrientedArchitecture\Week8\lab08-starter-main
.\.venv\Scripts\python.exe -u -c "from app import create_app; create_app({'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'}).run(host='127.0.0.1', port=5000, debug=False)"
```

Terminal 2 — chạy collection và xuất báo cáo:

```powershell
cd D:\ServiceOrientedArchitecture\Week8\lab08-starter-main
newman run books-api.postman_collection.json -e postman/local.postman_environment.json -r cli,junit --reporter-junit-export reports/junit.xml
```

Chỉ chạy error cases:

```powershell
newman run books-api.postman_collection.json -e postman/local.postman_environment.json --folder error-cases
```

Dừng server bằng `Ctrl+C` khi xong; CSDL trong bộ nhớ mất khi dừng.
Máy hiện chưa có Node.js/npm trong PATH; lần kiểm thử này dùng Node.js portable
và Newman cài trong thư mục tạm.

## Chạy trong Postman

1. Import một trong hai bản collection và [environment Local](../postman/local.postman_environment.json).
2. Chọn environment **Lab08 Local**, có `base_url = http://127.0.0.1:5000`.
3. Khởi động API như trên rồi chạy toàn bộ collection bằng Collection Runner.
4. Xem tab test results: 17 assertion phải pass.
