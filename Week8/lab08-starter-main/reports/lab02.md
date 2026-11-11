# Lab 2 — Lint OpenAPI bằng Spectral

## Ba lỗi đã sửa

1. Bổ sung `operationId: listBooks` cho `GET /books`.
2. Xóa `content` khỏi response `204` của `DELETE /books/{id}`.
3. Đổi `Book.year` từ `string` sang `integer`, giữ `nullable: true` theo model.

## Ruleset

[.spectral.yml](../.spectral.yml) kế thừa `spectral:oas` và kiểm tra:

- `operation-operationId`: bắt operation thiếu `operationId`, mức error.
- `no-content-on-204`: bắt response `204` khai báo body.
- `book-year-integer`: bắt kiểu của `Book.year` khác `integer`.
- `response-200-has-fields`: response `200` phải có `content.application/json.schema`;
  object phải có ít nhất một property; array phải có items là object có ít nhất
  một property. Bắt cả thiếu schema, schema `{}`, `properties: {}` và items rỗng.
  Rule chạy sau khi giải `$ref`, nên kiểm tra được cả schema tham chiếu `Book`.

Các rule về contact, tags và mô tả operation được tắt rõ trong cấu hình vì bài
thực hành này tập trung vào contract. Các rule OAS còn lại vẫn được kế thừa.

Tham khảo: [Spectral rules](https://github.com/stoplightio/spectral/blob/develop/docs/guides/4a-rules.md),
[schema function](https://github.com/stoplightio/spectral/blob/develop/docs/reference/functions.md).

## Khi Spectral pass nhưng Flask trả sai field

Spectral chỉ lint spec, không gọi Flask. Cần contract test lấy JSON thực tế từ
Flask test client rồi validate theo schema trong spec.

[test_lab02.py](../tests/test_lab02.py) kiểm tra POST/GET với `year` integer và
các field nullable. Test cũng xác nhận schema từ chối bản sao response có
`password_hash` lạ hoặc `year` dạng string. Đây là mô phỏng response sai,
không phải bằng chứng backend có field bí mật đó.

OpenAPI 3.0 dùng `nullable: true`; fixture chuyển nó thành union với `null`
trước khi dùng thư viện `jsonschema`, không thay đổi spec gốc.

## Chạy lại

Tại thư mục gốc starter, sau khi cài Node.js/npm:

```powershell
npm install -g @stoplight/spectral-cli@6.15.0
spectral lint openapi.yaml --ruleset .spectral.yml
.\.venv\Scripts\python.exe -m pytest -v
```

## Kết quả thực chạy

- Spectral CLI 6.15.0: bản ban đầu có 3 errors, 0 warnings.
- Bản đã sửa: 0 problems; output JSON là `[]`.
- Custom rule từ chối đủ 5/5 trường hợp schema sai đã thử.
- Toàn bộ pytest: **10 passed trong 1,20 giây**.

Log: [trước sửa](lab02-spectral-before.log), [sau sửa](lab02-spectral-after.log),
[kiểm tra custom rule](lab02-rule-checks.log).
