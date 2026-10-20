# Lab2 — Composite Cursor Pagination

### Ảnh 1: Hai trang cursor

![Hai trang cursor](<../images/Lab2(1).jpg>)
![Hai trang cursor](<../images/Lab2(2).jpg>)

_Giải thích: lấy trang đầu category=3, sort=-price, rồi dùng page.next để lấy trang sau; ID không trùng dù các sách có cùng giá._

### Ảnh 2: Request không hợp lệ

![Validation cursor](<../images/Lab2(3).jpg>)
![Validation cursor](<../images/Lab2(4).jpg>)

_Giải thích: sort không nằm trong whitelist, multi-key ở Lab2, đổi sort với cursor cũ hoặc cursor hỏng đều bị từ chối bằng HTTP 400._

### Ảnh 3: Tests

![Test lab 2](<../images/Lab2(5).jpg>)

_Giải thích: 6 test kết thúc OK, bao gồm duyệt hết collection không lặp/mất bản ghi với dữ liệu tĩnh và các tình huống chèn/xóa đã mô tả._
