# Chế độ API miễn phí cho TEA AI Mars Studio

Cập nhật ngày 26/10/2026. Mục tiêu: **ưu tiên các model được nhà cung cấp công bố có tầng sử dụng miễn phí**, và **không tự gọi Claude/OpenAI trả phí**.

> **Ranh giới bảo vệ chi phí:** Chế độ “chỉ model có gói API miễn phí” bảo vệ khỏi việc tự gọi các nhà cung cấp chỉ có API trả phí. Nó KHÔNG thể kiểm tra tài khoản Google/Groq của bạn đang dùng Free Tier hay dự án trả phí chỉ qua model ID/API key. Tài khoản có billing có thể bị tính phí ngay cả với model có Free Tier. Hãy xem trang Billing/Usage của từng nhà cung cấp và sử dụng khóa thuộc dự án Free Tier.

## Model được chọn theo vai trò

| Agent | Gemini chính (Free Tier có hạn mức) | Groq phụ (Free Plan có hạn mức) |
|---|---|---|
| AI CEO | `gemini-3.8-flash` | `openai/gpt-oss-120b` |
| Strategy | `gemini-3.8-flash` | `openai/gpt-oss-120b` |
| Compliance | `gemini-3.8-flash` | `openai/gpt-oss-120b` |
| Research | `gemini-3.8-flash` | `openai/gpt-oss-120b` |
| Creative | `gemini-3.5-flash-lite` | `openai/gpt-oss-20b` |
| Analyst | `gemini-3.5-flash-lite` | `openai/gpt-oss-20b` |

Ngoài các model mặc định, giao diện cho chọn các Gemini Free Tier: `gemini-3.8-flash`, `gemini-3.6-flash`, `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`, `gemini-2.5-flash`, `gemini-2.5-flash-lite`. Groq Free Plan: `openai/gpt-oss-120b`, `openai/gpt-oss-20b`, `qwen/qwen3.8-27b`.

Đây là các model có Free Tier / Free Plan được tài liệu nhà cung cấp công bố; **không có nghĩa mọi tài khoản/mọi lượt gọi sẽ được miễn phí**.

Nguồn chính thức:

- Gemini Pricing: https://ai.google.dev/gemini-api/docs/pricing
- Gemini Models: https://ai.google.dev/gemini-api/docs/models
- Groq Free Rate Limits: https://console.groq.com/docs/rate-limits
- Groq Supported Models: https://console.groq.com/docs/models
- Groq Billing FAQs: https://console.groq.com/docs/billing-faqs

## Claude / OpenAI và Ollama

- **Claude API:** Không có gói API miễn phí thường trực bảo đảm. Có thể có tín dụng thử nghiệm có giới hạn, không tính là model free.
- **OpenAI API:** Không có mô hình API tổng quát miễn phí thường trực bảo đảm; nếu từng có tín dụng thử nghiệm thì cũng có thể hết hạn.
- **Ollama:** chạy local, không mất phí token API bên ngoài; vẫn tiêu tốn CPU/GPU/RAM và điện.

Khi **Chỉ sử dụng model có gói API miễn phí** được bật, phần mềm:
1. Cho chọn chế độ `Tự động`, `Gemini`, `Groq`, `Ollama`.
2. Tự động thử Gemini → Groq → Ollama. Chỉ chuyển khi lỗi tạm thời như 429/5xx/mất mạng; lỗi 401/403 sẽ hiện để người dùng sửa quyền truy cập.
3. Chặn lựa chọn trực tiếp Claude/OpenAI hoặc bật `Cho phép dự phòng trả phí` ngay từ lúc lưu.
4. Kiểm tra an toàn lần nữa ở bộ định tuyến Python trước khi gửi yêu cầu, kể cả khi cấu hình cũ vẫn chọn model trả phí.
5. Cho bật lại tính năng trả phí trong tương lai bằng cách chủ động bỏ chọn `Chỉ sử dụng model có gói API miễn phí`; khi đó người dùng chịu trách nhiệm bật tính phí và thiết lập giới hạn của API.

## Cách cập nhật và chọn gói miễn phí

Đóng phần mềm rồi mở PowerShell:

```powershell
cd D:\APhanMem\teabotAI
git pull origin main
cd studio
.\start_windows.bat
```

Mở http://127.0.0.1:8765 → `Ctrl+Shift+R` → **Cài đặt Gemini / Groq / AI**:

1. Giữ đánh dấu **Chỉ sử dụng model có gói API miễn phí**.
2. Bấm **Áp dụng Gemini → Groq cho tất cả agent** để chuyển những agent trước đây đã dùng Claude/OpenAI về chế độ tự động, không sửa khóa đã lưu.
3. Nhập Gemini API key thuộc dự án không bật tính phí và Groq API key thuộc Free Plan.
4. Bấm **Lưu cấu hình AI**, rồi **Kiểm tra Gemini** và **Kiểm tra Groq**.
5. Giao một nhiệm vụ mới cho AI CEO để thử. Toàn bộ agent được yêu cầu trả lời bằng tiếng Việt và ghi nhật ký trao đổi; CEO vẫn là người chốt phương án cuối.

**Lưu ý lỗi Groq 403:** HTTP 403 có thể do tổ chức/dự án chặn quyền, không phải vì model trả phí. Thay đổi model thường không khắc phục được khi lỗi xảy ra tại endpoint `/models`. Xem `studio/GROQ_CONNECTION_TROUBLESHOOTING.md`.

## Giới hạn bảo mật, dữ liệu

Dữ liệu nhiệm vụ gửi qua Gemini/Groq Free Tier đi tới máy chủ của Google/Groq để xử lý. Chính sách Gemini Free Tier cho phép dữ liệu được dùng để cải thiện sản phẩm. Không đưa cookie, mật khẩu, OTP hoặc hồ sơ khách hàng nhạy cảm vào prompt. Dữ liệu key vẫn được giữ trong Windows Credential Manager và không hiển thị lại qua giao diện.

Kiểm thử CI sử dụng API giả lập, chưa xác nhận Free Tier/billing hay mô hình được phép dùng của tài khoản thật của bạn.
