# Lab1 — Bookstore API: Data Modeling và CRUD

### Ảnh 1: GET và representation

![GET Books](<../images/Lab1(1).jpg>)
![GET Books](<../images/Lab1(2).jpg>)
![GET Books](<../images/Lab1(3).jpg>)

_Giải thích: GET /api/v1/books?limit=2 trả HTTP 200, hai sách, metadata phân trang, giá VND, category và tác giả được nhúng vào JSON._

### Ảnh 2: CRUD

![CRUD](<../images/Lab1(4).jpg>)
![CRUD](<../images/Lab1(5).jpg>)
![CRUD](<../images/Lab1(6).jpg>)
![CRUD](<../images/Lab1(7).jpg>)

_Giải thích: tạo và đọc sách, đổi stock thành 8, xóa nhận 204 rồi đọc lại nhận 404; minh chứng vòng đời resource._

### Ảnh 3: Tests

![Test Lab1](../images/Lab1test.jpg)

_Giải thích: unittest chạy 5 test và kết thúc OK; kiểm tra cả luồng thành công và các lỗi validation/quan hệ dữ liệu._
