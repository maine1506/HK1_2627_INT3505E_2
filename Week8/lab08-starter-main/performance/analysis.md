# Lab 4 — Load test Books API bằng Locust

## Thiết lập

Đo thực tế ngày 17/11/2026, Windows, Python 3.14.10, Locust 2.47.0.
Locust và API chạy cùng máy qua `127.0.0.1:5054`. Runner dùng Werkzeug
development server threaded (cùng server nền của Flask), SQLite file tạm riêng
cho từng kịch bản, seed cùng 50 sách. Baseline cấu hình QueuePool 15 connection,
`max_overflow=0`, `pool_timeout=5s`; bonus giảm pool xuống 5. Cấu hình này chỉ
áp dụng trong runner, không đổi cấu hình mặc định của ứng dụng.

[locustfile.py](locustfile.py) có trọng số list/read/create/search là **3:2:1:1**.
Mỗi user nghỉ ngẫu nhiên 1–3 giây giữa task. Create thêm năm 1996, 2017 hoặc 2021;
search kiểm tra response là array và mọi sách có đúng năm yêu cầu.
`search_by_year(year=None)` nhận năm khi gọi trực tiếp hoặc chọn ngẫu nhiên khi
Locust chạy. HTTP 404 của read được coi là kết quả dự kiến; seed hiện có đủ ID 1–50.

Sau search HTTP 200 hợp lệ, xác suất 1% gọi
`response.failure("SIMULATED_500: client-side injection (actual HTTP 200)")`.
Đây là **lỗi giả lập phía Locust, không phải HTTP 500 thật từ server**.
Biến `LOCUST_SIMULATED_FAILURE_RATE` mặc định `0.01`, có thể đặt `0` cho CI.
Xác suất 1% không bảo đảm đúng 1 lỗi trong mỗi 100 request.

## Kết quả thực chạy

Lấy hàng `Aggregated` của CSV. Failure rate = failures / requests; RPS lấy từ
cột `Requests/s`. p95 là percentile histogram của Locust, có làm tròn.
Khoảng đo bao gồm ramp-up, không tách warm-up.

| Kịch bản | Users | Spawn rate (/s) | Duration | Requests | Failures | p95 (ms) | Failure rate | RPS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A — baseline nhẹ | 10 | 2 | 30s | 134 | 0 | 27 | 0% | 4,73 |
| B — tải thông thường | 50 | 5 | 60s | 1361 | 1 | 29 | 0,0735% | 23,28 |
| C — spike | 200 | 50 | 30s | 2801 | 4 | 290 | 0,1428% | 95,61 |

Báo cáo: [A.html](../reports/A.html), [B.html](../reports/B.html), [C.html](../reports/C.html).
Dữ liệu: [A CSV](../reports/A_stats.csv), [B CSV](../reports/B_stats.csv),
[C CSV](../reports/C_stats.csv), [summary JSON](../reports/lab04-summary.json).

## 1. Kịch bản có p95 cao nhất

**C cao nhất: 290 ms**, khoảng 10 lần B (29 ms), khi RPS tăng từ 23,28 lên 95,61.
p95 tăng ít từ A sang B nhưng tăng mạnh từ B sang C. Điều này phù hợp với giả
thuyết hàng đợi/tranh chấp tài nguyên bắt đầu rõ ở tải cao. Chưa đo CPU, pool wait
hay thời gian lock SQLite nên chưa xác định được bottleneck cụ thể.

| Endpoint | A p95 (ms) | B p95 (ms) | C p95 (ms) |
|---|---:|---:|---:|
| GET `/books` | 19 | 25 | 270 |
| GET `/books/{id}` | 21 | 22 | 270 |
| GET `/books?year` | 90 | 25 | 300 |
| POST `/books` | 76 | 41 | 370 |

POST cao nhất trong C. Code commit mỗi lần tạo sách; SQLite có thể tranh chấp
ghi. Model chưa có index riêng cho year nên query theo năm cũng là hướng cần
kiểm chứng. Đây là giả thuyết dựa trên code, chưa đủ để kết luận nguyên nhân.
A chỉ có 12 search request nên p95 riêng search nhạy với vài request chậm.

## 2. Endpoint có failure rate tăng

Chỉ **GET `/books?year`** có failures:

| Kịch bản | Search requests | Lỗi giả lập | Failure rate riêng search |
|---|---:|---:|---:|
| A | 12 | 0 | 0% |
| B | 198 | 1 | 0,5051% |
| C | 405 | 4 | 0,9877% |

[B failures](../reports/B_failures.csv) và [C failures](../reports/C_failures.csv)
chỉ ghi `SIMULATED_500`, actual HTTP 200. Không ghi nhận HTTP 500 thật, timeout
hay lỗi kiểm tra nội dung trong ba lần chạy.

Số lỗi tăng khi nhiều request hơn nhưng xác suất chèn lỗi vẫn cố định 1%.
Không thể kết luận tăng user làm backend lỗi nhiều hơn từ số liệu này.
Search có trọng số 1/7 nên failure rate toàn workload kỳ vọng khoảng
`1% × 1/7 = 0,1429%`, không phải 1%.

## 3. SLO p95 < 300 ms và CI gate

Nếu áp dụng SLO cho **toàn workload**, cả A, B, C đều đạt trong lần đo này.
C chỉ còn khoảng cách 10 ms. Nếu yêu cầu từng endpoint đều dưới 300 ms,
**C không đạt** vì search = 300 ms và POST = 370 ms; điều kiện là `<`, không phải `<=`.

Đề xuất **B: 50 users, spawn 5/s, 60s** làm CI baseline; A làm smoke test,
C chạy định kỳ hoặc trước release. Khi dùng CI gate:

- Tắt injection bằng `--failure-rate 0`; yêu cầu 0 failure thực.
- Yêu cầu p95 tổng và từng endpoint `< 300 ms`; dùng mốc ban đầu 1000 request
  tổng để tránh gate trên mẫu quá nhỏ.
- Đọc CSV để kiểm tra ngưỡng: exit code Locust chưa tự bắt vi phạm p95 nếu
  không thêm kiểm tra. Lệnh runner bên dưới chỉ đo, chưa triển khai gate tự động.
- Cố định dữ liệu/máy chạy và đo lặp để xác lập độ dao động trước khi dùng gate bắt buộc.

Exit code 1 của B/C do lỗi giả lập là dự kiến. Không bỏ qua exit code 1 chung
trong CI vì lỗi thật cũng có thể trả mã này.

## Bonus — Pool giới hạn 5 connection với 200 user

200 user không đồng nghĩa 200 connection DB đồng thời: mỗi user có think time,
request thường giữ connection ngắn. Khi 5 connection đều bận, request phải chờ;
chờ quá `pool_timeout` có thể gây timeout và HTTP 500 nếu app không xử lý exception.
POST còn có thể chờ lock SQLite.

Đã chạy lại C với pool 5, `max_overflow=0`, `pool_timeout=5s`; giữ nguyên users,
spawn, duration, dữ liệu seed và xác suất chèn lỗi:

| Cấu hình | Requests | p95 (ms) | RPS | Failures |
|---|---:|---:|---:|---:|
| Pool 15 | 2801 | 290 | 95,61 | 4 giả lập |
| Pool 5 | 2773 | 280 | 94,61 | 3 giả lập |

Nguồn: [HTML pool 5](../reports/C_pool5.html), [CSV pool 5](../reports/C_pool5_stats.csv),
[failures](../reports/C_pool5_failures.csv), [server log xác nhận pool](../reports/C_pool5-server.log).

**Chưa quan sát thấy suy giảm p95 do pool 5**: p95 thấp hơn 10 ms, RPS giảm
khoảng 1%, không có pool timeout/HTTP 500 thật. Một lần chạy ngắn, ngẫu nhiên
không chứng minh pool 5 đủ cho mọi tải hoặc nhanh hơn pool 15.
Để xác nhận: lặp các phép đo khi tắt injection, thu thập thời gian chờ checkout,
số checked-out connections, SQL latency, CPU; tăng tải/giảm think time có kiểm soát.
Đối chiếu lỗi `QueuePool timeout` với `database is locked`, không gộp hai nguyên nhân.

## Chạy lại

Từ thư mục gốc starter, runner tự mở API/CSDL tạm, xuất HTML/CSV/log rồi dừng API:

```powershell
.\.venv\Scripts\python.exe performance/run_lab04.py
.\.venv\Scripts\python.exe performance/run_lab04.py --cases C --pool-size 5 --suffix _pool5
```

Đo B không chèn lỗi để chuẩn bị CI baseline:

```powershell
.\.venv\Scripts\python.exe performance/run_lab04.py --cases B --failure-rate 0 --suffix _ci
```

Chạy thủ công như slide: mở API ở terminal khác rồi lần lượt chạy:

```powershell
.\.venv\Scripts\python.exe -m locust -f performance/locustfile.py --headless -H http://127.0.0.1:5000 -u 10 -r 2 -t 30s --html reports/A.html --csv reports/A
.\.venv\Scripts\python.exe -m locust -f performance/locustfile.py --headless -H http://127.0.0.1:5000 -u 50 -r 5 -t 60s --html reports/B.html --csv reports/B
.\.venv\Scripts\python.exe -m locust -f performance/locustfile.py --headless -H http://127.0.0.1:5000 -u 200 -r 50 -t 30s --html reports/C.html --csv reports/C
```

Chạy thủ công dùng dữ liệu/cấu hình của API đang mở; chỉ runner bảo đảm seed và
pool như phép đo trên. Kết quả dao động, không mặc định trùng bảng báo cáo.

## Giới hạn

Development server và SQLite trên máy cá nhân; load generator và API dùng chung
CPU; mỗi cấu hình đo một lần; C chỉ 30s, chưa tách steady-state hoặc đo CPU/IO/pool wait.
Đây là kết quả thực hành, **không chứng minh SLO/công suất production**.
Kiểm thử chức năng sau thay đổi: **10 pytest passed trong 1,42 giây**.

Tham khảo: [Locust configuration](https://docs.locust.io/en/stable/config-options.html),
[Running without Web UI](https://docs.locust.io/en/stable/running-without-web-ui.html).
