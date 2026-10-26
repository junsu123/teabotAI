# Khắc phục lỗi không kết nối GroqCloud từ giao diện TEA AI

**Groq** (GroqCloud, API tại `api.groq.com`) và **Grok** (xAI, API tại `api.x.ai`) là hai dịch vụ khác nhau. Phần mềm TEA AI hiện tích hợp **GroqCloud** làm dự phòng sau Gemini, không sử dụng khóa API Grok của xAI.

## Cách kiểm tra sau khi cập nhật

1. Đóng phần mềm trên Windows.
2. Chạy:
   ```powershell
   cd D:\APhanMem\teabotAI
   git pull origin main
   cd studio
   .\start_windows.bat
   ```
3. Truy cập `http://127.0.0.1:8765`, nhấn `Ctrl+Shift+R`.
4. Vào **Cài đặt Gemini / Groq / AI**.
5. Tạo và sao chép API key đúng từ https://console.groq.com/keys .
6. Dán vào **Groq API Key**, bấm **Kiểm tra Groq** trước khi lưu. Hệ thống kiểm tra qua `GET https://api.groq.com/openai/v1/models`, không tạo câu trả lời tính phí.
7. Đọc dòng kết quả ngay dưới hai nút Kiểm tra. Nếu thành công, bấm **Lưu cấu hình AI** để dùng khóa vừa nhập.

**Bản sửa mới** cho phép test khóa đang nhập mà không cần lưu trước, đồng thời chỉ hiện kết quả và mã lỗi an toàn (không hiện API key).

## Phân biệt nguyên nhân

| Thông báo | Hướng xử lý |
|---|---|
| Chưa lưu/chưa nhập Groq API key | Dán khóa vào ô Groq API Key; bấm Kiểm tra Groq |
| Khóa Grok của xAI | Tạo Groq key tại `console.groq.com/keys`, không dùng khóa từ `console.x.ai` |
| HTTP 401 | Khóa sai, bị thu hồi, hoặc dùng nhầm dịch vụ; cấp khóa Groq mới |
| HTTP 403 | Tài khoản/dự án thiếu quyền; kiểm tra mục giới hạn và quyền model trên GroqCloud |
| HTTP 429 | Vượt rate limit/quota; chờ hoặc dùng Gemini / Ollama dự phòng |
| HTTP 404 | Đường dẫn hoặc model không tồn tại; cập nhật phần mềm |
| Lỗi SSL/TLS | Kiểm tra thời gian Windows, phần mềm antivirus chặn HTTPS, proxy/VPN |
| Lỗi DNS | Kiểm tra kết nối Internet và phân giải `api.groq.com` |
| Hết thời gian chờ | Kiểm tra mạng, VPN, proxy và firewall; kiểm tra Groq console có truy cập được không |
| Key hợp lệ nhưng không có model trùng | Kiểm tra quyền model trong GroqCloud; chọn mô hình mà tài khoản có quyền dùng |

**Không gửi ảnh chụp có lộ khóa API hoặc sao chép khóa vào ChatGPT/Telegram.** Chỉ gửi dòng thông báo lỗi đã che khóa.

## Lưu ý

- Kiểm tra bằng danh sách model chứng minh khóa được Groq chấp nhận, **chưa bảo đảm lượt suy luận chat thực tế** luôn thành công hoặc miễn phí.
- Dùng `Tự động` sẽ ưu tiên Gemini → Groq → Ollama, chỉ sử dụng Claude/OpenAI dự phòng nếu bạn cho phép trả phí rõ ràng.
- Nếu kết nối Groq không thành công sau khi cập nhật, xem **mã HTTP** và mô tả ngay trong ô kết quả rồi gửi nguyên dòng lỗi (không gửi API key).

Phần kiểm thử tự động sử dụng Groq API giả lập. Máy Windows của người dùng cần kiểm tra lại bằng khóa thực tế.
