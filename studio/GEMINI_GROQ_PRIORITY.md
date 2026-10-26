# Thiết lập AI theo thứ tự: Gemini → Groq → Claude → OpenAI → Ollama

**Đã chốt nguyên tắc:** Bạn chỉ giao nhiệm vụ cho AI CEO; CEO điều phối nội bộ, các agent tranh luận bằng tiếng Việt, và CEO chốt phương án cuối cùng.

## Thứ tự ưu tiên khi chạy TỰ ĐỘNG

1. **Google Gemini API** – mặc định `gemini-3.8-flash` cho CEO/Strategy/Compliance/Research, `gemini-3.5-flash-lite` cho Creative/Analyst.
2. **GroqCloud API** – dự phòng, `openai/gpt-oss-120b` và `openai/gpt-oss-20b` tương ứng.
3. **Claude API** – chỉ khi bật rõ ràng tùy chọn **Cho phép dự phòng trả phí** và đã có key.
4. **OpenAI API** – cùng điều kiện.
5. **Ollama cục bộ** – không mất phí API khi chạy trên máy, là bước cuối mặc định nếu Gemini/Groq không truy cập được. Nếu Ollama không chạy thì nhiệm vụ chuyển `blocked`.

**Quan trọng:** Thứ tự xử lý cố định ở phiên bản này, nhưng người dùng có thể chọn riêng một nhà cung cấp cụ thể cho từng agent. Chế độ chọn nhà cung cấp trực tiếp **không tự dự phòng**; hãy chọn `auto` để kích hoạt ưu tiên trên.

**Chỉ chuyển tự động khi** Gemini hoặc Groq gặp lỗi tạm thời, bị giới hạn tốc độ/quota (HTTP 429), lỗi HTTP 5xx hoặc mất kết nối. Khi API key không hợp lệ, bị từ chối quyền hay model sai (401/403/400), phần mềm **báo lỗi trực tiếp**, không che lỗi bằng dịch vụ dự phòng. Không tự thực hiện đăng bài, thay đổi giá hoặc mua dịch vụ.

## Cài đặt hoàn toàn bằng giao diện Windows

1. Đóng TEA AI Mars Studio hiện đang chạy.
2. Cập nhật mã nguồn:
   ```powershell
   cd D:\APhanMem\teabotAI
   git pull origin main
   cd studio
   .\start_windows.bat
   ```
3. Mở `http://127.0.0.1:8765`, nhấn `Ctrl+Shift+R`.
4. Chọn **⚙ Cài đặt Gemini / Groq / AI**.
5. Tạo Gemini API key tại [Google AI Studio](https://aistudio.google.com/api-keys) và dán vào ô **Gemini API Key**.
6. Tạo GroqCloud API key tại [GroqCloud](https://console.groq.com/keys) và dán vào ô **Groq API Key**.
7. Nhấn nút **Áp dụng Gemini → Groq cho tất cả agent**. Tùy chọn dự phòng trả phí sẽ tự bỏ chọn.
8. Nhấn **Lưu cấu hình AI** rồi lần lượt nhấn **Kiểm tra Gemini**, **Kiểm tra Groq**. Các nút kiểm tra chỉ đọc danh sách mô hình, **không tạo nội dung và không phát sinh token suy luận**.
9. Mở **Giao nhiệm vụ cho CEO**; mọi agent đặt **Tự động** sẽ sử dụng tuyến ưu tiên mới.

Những máy đã lưu cấu hình Claude/OpenAI hoặc Ollama từ phiên bản trước **không bị tự ghi đè nhà cung cấp** khi nâng cấp. Bạn cần bấm **Áp dụng Gemini → Groq cho tất cả agent** một lần để kích hoạt thứ tự ưu tiên cho các agent trước đây.

API key lưu bằng `keyring` trong kho mật khẩu Windows, không lưu giá trị khóa vào GitHub, `.env`, `integrations.local.json` hoặc Telegram. Không bao giờ dán key vào phần Giao nhiệm vụ CEO.

## Giới hạn miễn phí và quyền riêng tư

**Không bảo đảm luôn miễn phí.** Gemini API và Groq có các hạn mức miễn phí theo tài khoản, model, nơi đăng ký và quota. Nếu bạn dùng tài khoản có kích hoạt thanh toán, các yêu cầu có thể phát sinh chi phí theo chính sách của nhà cung cấp. Hãy kiểm tra bảng giá, quota và cài đặt billing ngay tại console:

- [Gemini Pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [Groq Rate Limits](https://console.groq.com/docs/rate-limits)
- [Groq Model Catalog](https://console.groq.com/docs/models)

Đặc biệt, chính sách Gemini **Free Tier** có thể cho phép Google sử dụng nội dung gửi qua API để cải thiện sản phẩm. Tránh gửi bí mật kinh doanh, số liệu nhạy cảm, thông tin khách hàng, cookie, mật khẩu hoặc OTP qua tầng miễn phí.

Bản này ghi nhà cung cấp đã thật sự xử lý từng lượt AI vào `studio/data/openai_usage.sqlite3` (bảng `model_routes`, không chứa key hoặc prompt). Điều này giúp kiểm tra nếu Groq hoặc Ollama đã được dùng làm dự phòng.

## Đánh giá và giới hạn

CI chạy kiểm thử giả lập cho các kịch bản Gemini thành công, Gemini HTTP 429 chuyển Groq, hai API lỗi tạm thời chuyển Ollama, key lỗi HTTP 401 không tự che lỗi, và không tự gọi API trả phí. **Chưa thử trực tiếp với Gemini/Groq key thật trên máy Windows của bạn**.

Mô hình mạnh không thay thế bằng chứng thực tế. Research phải có nguồn công khai đáng tin cậy; Analyst cần báo cáo số liệu thật; Compliance cần nhãn/hồ sơ sản phẩm và văn bản pháp lý.
