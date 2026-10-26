# Lưu API Key trong database SQLite và xem lại bằng nút Hiện

Cập nhật cho **TEA AI Mars Studio**.

## Lưu trữ

- API keys của **Gemini, Groq, Claude và OpenAI** cùng token Telegram được lưu trong `studio/data/integrations.secrets.sqlite3`.
- **Không lưu plaintext** trong database: mỗi giá trị được mã hóa Fernet (AES-128-CBC + HMAC-SHA256 do thư viện cryptography cung cấp).
- **Khóa mã hóa chính** tiếp tục nằm trong Windows Credential Manager của **tài khoản Windows đang chạy phần mềm**. Đây không phải nơi lưu API key nữa.
- `studio/data/integrations.local.json` tiếp tục lưu các lựa chọn model, danh sách agent, ngân sách, hạn mức; không chứa key.
- File SQLite được `.gitignore` loại trừ, không đẩy lên GitHub.
- Những key/tokens trước đây lưu trong Windows Credential Manager được chuyển sang SQLite tự động ở lần truy cập đầu tiên và chỉ xóa bản cũ khi đã lưu/giải mã kiểm chứng thành công. Không cần nhập lại nếu tài khoản Windows và kho mật khẩu cũ còn hoạt động.

**Quan trọng:** Khi sao chép database sang máy hoặc tài khoản Windows khác, bạn cũng cần bản sao lưu khóa mã hóa chính. Nếu không, khóa đã mã hóa **không thể giải mã**. Cách đơn giản nhất khi chuyển máy là nhập lại API key tại giao diện; không sao chép database chứa dữ liệu nhạy cảm sang người khác.

## Cập nhật và cài thư viện một lần

Đóng ứng dụng và mở PowerShell:

```powershell
cd D:\APhanMem\teabotAI
git pull origin main
cd studio
.\setup_windows.bat
.\start_windows.bat
```

`setup_windows.bat` cài thêm `cryptography` để mã hóa database (có thể chạy lại an toàn). Những lần sau chỉ cần `start_windows.bat`.

Truy cập `http://127.0.0.1:8765`, nhấn `Ctrl+Shift+R`, vào **Cài đặt AI & Telegram**.

## Sử dụng nút Hiện / Ẩn

1. Nhập một API key, sau đó bấm **Lưu cấu hình AI** để lưu vào database.
2. Khi quay lại hoặc mở phần mềm lần sau, ô nhập chỉ có ghi chú **Đã lưu** và bị che, không chứa plaintext.
3. Nhấn **Hiện** ở thẻ Gemini/Groq. Trình duyệt hỏi xác nhận để bảo đảm không có người khác đang nhìn màn hình.
4. Sau khi xác nhận, khóa được giải mã từ SQLite và **hiển thị nguyên vẹn ngay trong ô**. Không bị tự gửi sang ChatGPT hoặc Telegram.
5. Nhấn **Ẩn** để che và xóa giá trị khỏi ô; khóa vẫn tồn tại trong database. Nếu bạn không thao tác, khóa đang hiển thị sẽ tự ẩn sau 60 giây.
6. Để **thay đổi** khóa, ẩn khóa đang xem, nhập khóa mới và bấm Lưu cấu hình AI.

Claude/OpenAI có nút Hiện trong phần tùy chọn nâng cao. Telegram Token có nút Hiện trong tab Telegram Bot.

Không nên nhấn Hiện khi chia sẻ màn hình hoặc chụp ảnh; nếu nghi ngờ API key đã lộ, hãy **thu hồi/đổi khóa tại nhà cung cấp**. Việc xóa một API key trong database không tự thu hồi khóa tại Google, Groq hay nhà cung cấp.

## Quyền truy cập

Nút Hiện sử dụng một yêu cầu POST riêng từ trang local, yêu cầu Origin hợp lệ, header JavaScript tùy chỉnh và xác nhận người dùng. Đường GET/status/overview không bao giờ trả về plaintext. Phần mềm không có cơ chế đăng nhập đa người dùng; vì vậy **bất kỳ ai có quyền điều khiển phiên Windows/máy tính và trình duyệt đang mở có thể xem khóa**. Không mở cổng 8765 ra Internet, không chia sẻ màn hình khi xem khóa.

Phần mềm chỉ hoạt động trên localhost, và phản hồi API được đánh dấu không lưu cache. Kiểm thử tự động chỉ xác nhận logic, chưa thử chạy thực tế trên Windows.
