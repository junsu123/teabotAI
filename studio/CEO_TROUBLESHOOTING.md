# Khắc phục nhiệm vụ CEO luôn ở trạng thái PENDING

## Nguyên nhân

Ở các phiên bản Mars Studio cũ, phần mềm chỉ **lưu** nhiệm vụ vào bảng `missions`, không có tiến trình AI CEO xử lý. Bản hiện tại đã thêm `studio/ceo_engine.py` và tiến trình nền chạy khi khởi động `studio/run.py`.

## Cập nhật trên Windows

1. Đóng cửa sổ đang chạy TEA AI Mars Studio (dừng máy chủ ở cổng 8765).
2. Mở PowerShell và chạy:

```powershell
cd teabotAI
git pull origin main
ollama pull qwen3:4b
cd studio
.\start_windows.bat
```

3. Mở **Giao nhiệm vụ CEO** ở `http://127.0.0.1:8765`.
4. Kiểm tra dòng trạng thái Ollama: **ĐÃ KẾT NỐI** và model có sẵn.
5. Những nhiệm vụ `pending` được tiếp nhận lần lượt. Xem chi tiết từ nút **Xem tiến độ / báo cáo**.
6. Nếu hiện `blocked`, đọc lý do, sửa lỗi, rồi bấm **Thử lại**.

Nếu lệnh `ollama` chưa nhận diện được, cài Ollama ở https://ollama.com/download rồi mở ứng dụng. Ollama trên Windows thường chạy nền; chỉ chạy `ollama serve` nếu chưa có tiến trình Ollama đang chạy.

Kiểm tra cục bộ bằng PowerShell:

```powershell
Invoke-RestMethod http://127.0.0.1:11434/api/tags
```

Nếu máy yếu và muốn dùng model nhỏ hơn:

```powershell
ollama pull qwen3:1.7b
$env:OLLAMA_MODEL="qwen3:1.7b"
cd teabotAI\studio
.\start_windows.bat
```

Chạy biến môi trường này trong cùng cửa sổ PowerShell khởi chạy ứng dụng.

## Trạng thái

- `pending`: đang xếp hàng chờ CEO.
- `in_progress`: CEO đang lên kế hoạch, phân công và tổng hợp.
- `done`: CEO đã lưu báo cáo/bản nháp. **Không có nghĩa đã đăng hàng.**
- `blocked`: có lỗi (thường là Ollama hoặc model chưa sẵn sàng). Có thông báo và nút thử lại.

## Giới hạn và nguyên tắc điều hành

- Chủ doanh nghiệp chỉ giao nhiệm vụ cho **AI CEO**.
- CEO phân công nội bộ cho Research, Strategy, Creative, Analyst, Compliance; phòng ban không báo cáo thẳng cho chủ.
- Nhân viên AI hiện viết bản nháp/báo cáo từ dữ liệu và mô hình cục bộ; không truy cập web hay gian hàng nếu chưa cấu hình dữ liệu/công cụ được phép. Không tự đăng sản phẩm, chỉnh giá, chi tiền hoặc điều khiển trình duyệt từ cơ chế CEO này.
- Hệ thống không tự huấn luyện trọng số mô hình và không thay thế kiểm duyệt người dùng.
- Dữ liệu nhiệm vụ được lưu trong `studio/data/studio.sqlite3`; không xóa tệp này để sửa lỗi `pending`.

## Kiểm thử tự động

```powershell
python -m unittest discover -s studio/tests -v
```

Các bài kiểm thử dùng hàm gọi AI giả lập, **không chứng minh Ollama thực tế trên máy người dùng chạy được**.
