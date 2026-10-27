# Security Audit - Social Network API

## Phạm vi

Rà soát thiết kế của `POST /auth/login`, `POST /auth/refresh`, `GET /posts/{id}` trong `openapi.yaml`. Đây là các nguy cơ cần kiểm tra khi triển khai, không phải kết luận đã phát hiện lỗi trong backend đang chạy.

Thiết kế sử dụng JWT access 15 phút và refresh rotation trong phiên có hạn tuyệt đối 30 ngày. GET bài viết cần scope `posts:read`; bài private chỉ chủ sở hữu được đọc. Bài private của người khác được trả về 404 giống bài không tồn tại.

## Các điểm có thể lộ và cách xử lý

| STT | Điểm có thể lộ | Hậu quả | Cách hạn chế | Cách kiểm tra khi có backend |
| --- | --- | --- | --- | --- |
| 1 | Mật khẩu lưu dạng rõ hoặc hash nhanh như MD5/SHA-256 | Lộ DB có thể dẫn đến chiếm tài khoản | Dùng Argon2id với salt riêng do thư viện tạo; không trả password_hash trong API | Kiểm tra dữ liệu lưu và response, bảo đảm không có mật khẩu rõ hoặc hash trong response |
| 2 | Khóa ký JWT nằm trong source, file cấu hình được commit hoặc log | Kẻ tấn công có thể tự ký token | Đọc khóa từ biến môi trường/secret manager, khóa HS256 ngẫu nhiên ít nhất 256 bit; bỏ .env khỏi Git; thu hồi khóa đã lộ | Kiểm tra cả lịch sử Git; nếu từng lộ phải đổi khóa, không chỉ xóa file ở commit mới |
| 3 | Token hoặc mật khẩu đi qua HTTP, query string hay log | Credential bị đọc và dùng lại | Chỉ dùng HTTPS; token qua Authorization; che header và body nhạy cảm trong log; token response có no-store | Kiểm tra đường truyền, URL, log ứng dụng và reverse proxy |
| 4 | Chỉ decode JWT, không kiểm chữ ký/claims hoặc chấp nhận alg=none | Token giả hoặc token của dịch vụ khác được chấp nhận | Allowlist HS256; kiểm chữ ký, exp, iss, aud, sub, type và thu hồi | Sửa payload/chữ ký; gửi token hết hạn, sai iss/aud, alg=none: đều phải nhận 401 |
| 5 | Chỉ kiểm đăng nhập mà không kiểm scope | Người dùng gọi hành động ngoài quyền được cấp | GET bài viết phải kiểm posts:read; quyền do server cấp | Access token hợp lệ nhưng không có posts:read phải nhận 403 |
| 6 | Có scope nhưng không kiểm quyền trên từng bài viết (BOLA) | User A đọc được bài private của B bằng cách đổi ID | Sau kiểm scope, kiểm visibility và owner_id; mặc định từ chối | A đọc bài private của B phải nhận 404, không lộ nội dung; chủ bài đọc được 200 |
| 7 | Refresh token dùng lại được hoặc hai request cùng đổi thành công | Token bị đánh cắp duy trì phiên lâu dài | Rotation nguyên tử, lưu jti/trạng thái phiên; phát hiện replay thì thu hồi cả family và access liên quan | Refresh lần đầu 200; dùng lại token cũ 401; cặp mới của family bị thu hồi cũng không dùng được |
| 8 | Nhầm access token và refresh token | Refresh dài hạn bị dùng để đọc dữ liệu hoặc access tự gia hạn | Kiểm type ở từng endpoint; refresh chỉ dùng tại /auth/refresh | Dùng access để refresh hoặc refresh để GET bài viết đều phải nhận 401 |
| 9 | Thông báo login khác nhau hoặc không giới hạn thử mật khẩu | Dò email, brute force và credential stuffing | Chung lỗi invalid_credentials; giảm chênh lệch thời gian bằng xác minh hash giả khi không có user; rate-limit theo IP và tài khoản | Email sai và mật khẩu sai nhận cùng 401/body; vượt hạn nhận 429 và Retry-After |
| 10 | Lưu token trong localStorage, bị mã JavaScript đọc khi có XSS | Mất token và phiên đăng nhập | Với web cân nhắc BFF và cookie HttpOnly/Secure/SameSite phù hợp; khi chuyển sang cookie phải bổ sung CSRF; vẫn cần chống XSS | Kiểm tra nơi lưu token và nơi render nội dung bài viết; không render HTML không tin cậy trực tiếp |
| 11 | Refresh giữ nguyên quyền cũ hoặc tin role/scopes do client gửi | Người dùng giữ quyền đã bị gỡ hoặc tự nâng quyền | Nạp lại quyền từ DB; giao với quyền đã cấp cho phiên; login chỉ nhận email/password | Gỡ quyền rồi refresh: token mới không được chứa quyền đã gỡ; gửi thêm role/scopes vào login phải nhận 400 |
| 12 | Trả toàn bộ DB row, stack trace hoặc cache dữ liệu riêng tư | Lộ email, hash, thông tin hệ thống hoặc bài private | Chỉ trả các trường trong schema; lỗi 500 chung; response bài viết có no-store | Kiểm tra response không có trường ngoài schema; lỗi nội bộ không có traceback; kiểm Cache-Control |

## Những quyết định chính

Login không cần scope vì người dùng chưa có token. Refresh cũng không cần scope đọc bài viết, nhưng phải có đúng refresh token và phiên hợp lệ. Chỉ GET bài viết yêu cầu `posts:read`. Việc có scope cho phép thực hiện thao tác đọc, nhưng không có nghĩa được đọc mọi bài private.

Chọn 401 khi không xác thực được, 403 khi đã xác thực nhưng thiếu scope và 404 khi không có bài viết hoặc không được phép biết bài private tồn tại. Không cho admin tự động xem mọi bài private vì đề bài chưa yêu cầu quyền đó.

Các quy tắc trong OpenAPI là hợp đồng cần triển khai. Swagger hiển thị security và x-required-scopes không tự tạo middleware xác thực, kiểm quyền hay rotation.
