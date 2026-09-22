## App1

![Anh minh hoa app1](./images/app1-1.png)
Dùng GET /books để lấy danh sách các sách, bao gồm data (thông tin các sách) và total (tổng số sách).

![Anh minh hoa app1](./images/app1-2.png)
Dùng POST /books để thêm sách mới.

![Anh minh hoa app2](./images/app2-1.png)
Dùng GET /books/bid để xem thông tin sách có id = bid, cache 60s.

![Anh minh hoa app2](./images/app2-2.png)
Dùng PATCH /books/bid để chỉnh sửa giá tiền của sách có id = bid.

![Anh minh hoa app2](./images/app2-3.png)
Dùng PUT /books/bid để thay thế toàn bộ các trường của cuốn sách có id = bid thành cuốn sách mới.

![Anh minh hoa app2](./images/app2-4.png)
Dùng DELETE /books/bid để xóa cuốn sách có id = bid.

![Anh minh hoa app2](./images/app2-5.png)
Dùng DELETE /books/bid một lần nữa, sách không còn trong database nên báo lỗi 404 NOT FOUND.

![Anh minh hoa app3](./images/app3-1.png)
Xem danh sách các sách ở trang 2 với size = 10. Khi đó data = [] do chỉ có 5 cuốn sách trong DB. Không có liên kết đến trang sau.

![Anh minh hoa app3](./images/app3-2.png)
Xem danh sách các sách ở trang 2 với size = 2. Khi đó sẽ có tổng cộng 3 trang, có liên kết đến trang trước và trang sau.

![Anh minh hoa app3](./images/app3-3.png)
Xem các sách của tác giả Orwell.

![Anh minh hoa app3](./images/app3-4.png)
Xem các sách có chứa từ "clean" trong tiêu đề.

![Anh minh hoa app3](./images/app3-5.png)
Xem các sách của Martin có chữ "clean", lấy trang 1, size 1.

![Anh minh hoa app3](./images/app3-6.png)
Yêu cầu trả về định dạng JSON.
