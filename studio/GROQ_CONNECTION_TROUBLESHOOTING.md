# Khắc phục lỗi không kết nối GroqCloud từ giao diện TEA AI

## Đã sửa: mã Python dùng Groq SDK chạy được, nhưng phần mềm bị HTTP 403

Vấn đề trước đây: Mars Studio sử dụng `urllib.request`, trong khi chương trình Python thử nghiệm dùng **`from groq import Groq`**, SDK chính thức chạy qua httpx. Phần mềm đã chuyển **toàn bộ các cuộc gọi Groq thật** (CEO/agent, danh sách model, test một câu) sang `Groq(api_key=key)` với SDK, tương tự chương trình mẫu. Không phải dán khóa vào mã nguồn.

**Quan trọng về API key:** Chương trình mẫu có thể sử dụng `GROQ_API_KEY` từ biến môi trường, hoặc rơi về chuỗi mặc định cố định khi biến môi trường không tồn tại. Mars Studio **không** dùng khóa mã hóa cứng hoặc khóa nằm trong biến môi trường; nó đọc API key từ SQLite mã hóa. Vì vậy, chương trình mẫu chạy được KHÔNG xác nhận khóa trong database là cùng khóa. Phải nhập và bấm Lưu cấu hình AI.

Nếu bạn từng dán key ở đoạn mã, chat, screenshot hay kho công khai, **thu hồi khóa đã lộ** tại https://console.groq.com/keys rồi tạo khóa mới. Không ghi khóa vào `.py`, GitHub, `.env` hay tài liệu hướng dẫn.

### Cách cập nhật

Đóng ứng dụng và chạy:

```powershell
cd D:\APhanMem\teabotAI
git pull origin main
cd studio
.\setup_windows.bat
.\start_windows.bat
```

**Phải chạy setup_windows.bat một lần sau bản cập nhật** để cài `groq>=1.7,<2`.

Mở http://127.0.0.1:8765, nhấn Ctrl+Shift+R, chọn Cài đặt AI & Telegram → Gemini & các AI:

1. Dán khóa Groq **mới** vào thẻ GroqCloud, bấm **Lưu cấu hình AI**.
2. Bấm **Thử như mã Python mẫu (GPT-OSS-120B)**: kiểm tra cùng SDK, model `openai/gpt-oss-120b`, câu hỏi `Reply with exactly: GROQ API OK`, `max_completion_tokens=100`; dùng khóa vừa dán nếu có. Có tiêu thụ token, nên chỉ chạy khi bạn đồng ý.
3. Bấm **★ Kiểm tra khóa đã lưu + model AI CEO**: cũng dùng Groq SDK nhưng **bắt buộc** lấy key từ SQLite và model CEO đã lưu, với lời nhắc agent thực tế. Nếu lỗi chỉ khi chạy bước này, so sánh key đã lưu và model CEO; không đưa khóa cho người khác.
4. Nếu hai bước đều OK mà CEO vẫn lỗi, mở Nhiệm vụ → Xem tiến độ/báo cáo, kiểm tra dòng lỗi `Groq/<model> · agent <vai trò>`. Vẫn có thể do độ dài tác vụ, hạn mức token, Gemini đứng đầu chế độ Tự động hoặc lỗi ở agent khác.

Giữ **Gemini làm AI chính**, **Groq dự phòng**, Ollama cuối; chọn `Chỉ Groq` cho CEO nếu muốn thử Groq độc lập, sau đó chuyển lại `Tự động`.



## Khi Groq test key thành công nhưng AI CEO vẫn lỗi

**Kiểm tra key đã nhập và key đang thực sự dùng là hai việc khác nhau.**
Nút `Kiểm tra Groq` dùng khóa đang gõ trong ô nếu có, hoặc khóa trong database nếu ô trống.
Nút `Thử trực tiếp GPT-OSS-20B` dùng GPT-OSS-20B; nhưng mặc định AI CEO chạy `openai/gpt-oss-120b`.

Để xác định đúng nguyên nhân:

1. Mở Cài đặt AI & Telegram → Gemini & các AI.
2. Nếu vừa dán API key mới, **bấm Lưu cấu hình AI**.
3. Nhấn **★ Kiểm tra khóa đã lưu + model AI CEO**. Nút này bắt buộc lấy khóa Groq từ database SQLite mã hóa, sử dụng chính model Groq đã chọn cho AI CEO (mặc định GPT-OSS-120B). Có tạo một câu trả lời ngắn, tiêu thụ token/quota; hệ thống hỏi xác nhận trước.
4. Nếu phép thử này thành công, chọn lại nhà cung cấp cho CEO nếu cần: **Tự động** thử Gemini trước, rồi mới đến Groq nếu Gemini tạm lỗi; chọn **Chỉ Groq** mới bắt buộc CEO gọi Groq.
5. Giao lại nhiệm vụ bị chặn bằng **Thử lại**, xem cột lỗi của nhiệm vụ / log phòng họp. Dòng lỗi ghi rõ `Groq/<model> · agent <vai trò>` nếu lỗi tại Groq.

Đối với các model `openai/gpt-oss-*`, phần mềm hiện đặt `reasoning_effort=low` và `include_reasoning=false` theo hướng dẫn Groq, tăng ngân sách phản hồi vừa phải để tránh hết token dành cho câu trả lời thực tế.

**Nếu chỉ test key nhập tay OK nhưng test khóa đã lưu lỗi:** gần như chắc chắn khóa trong database khác khóa vừa nhập, hoặc model AI CEO khác với model đang thử. Hãy lưu key và model trước khi kiểm tra lại.

**Nếu nút test khóa đã lưu OK nhưng nhiệm vụ dài lỗi:** có thể do độ dài prompt, token/rate limit, bộ định tuyến Gemini/Groq, hoặc bước khác của nhiệm vụ. Gửi thông báo nguyên dòng lỗi mới, không gửi key hoặc dữ liệu khách hàng nhạy cảm.



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
