# Bài 2 — Offset / Cursor, Genre Filter và Multi-key Sort

### Ảnh 1: Offset + filter + multi-sort

![Offset](<../images/Bai2(1).jpg>)
![Offset](<../images/Bai2(2).jpg>)
![Offset](<../images/Bai2(3).jpg>)

_Giải thích: trả danh sách genre=tech theo giá giảm, tên tăng; metadata có offset, limit và total=10 sau khi lọc._

### Ảnh 2: Tests

> **[Chèn ảnh bai2-03-tests.png tại đây]**

![Test bài 2](<../images/Bai2(5).jpg>)

_Giải thích: 8 test kết thúc OK; xác minh phân trang, dữ liệu trùng khóa, sort nhiều chiều và các tham số không hợp lệ._
