# Ưu tiên Claude API trong TEA AI Mars Studio (không cần sửa file .env)

## 1. Cập nhật và mở phần mềm

Đóng ứng dụng cũ. Trong Windows PowerShell:

```powershell
cd D:\APhanMem\teabotAI
git pull origin main
cd studio
.\start_windows.bat
```

Nếu bạn chưa chạy `setup_windows.bat` ở phiên bản cài đặt gần đây, mở nó **một lần** để cài gói keyring; sau đó bạn chỉ cần mở `start_windows.bat`.

Mở http://127.0.0.1:8765 → `Ctrl+Shift+R` → menu **Cài đặt Claude / ChatGPT & Telegram**.

## 2. Kết nối Claude API trên giao diện

1. Truy cập **Claude Console**: https://platform.claude.com/settings/keys, tạo một API key riêng cho Mars Studio. **Tài khoản Claude trên website và tiền sử dụng Claude API được quản lý riêng.**
2. Dán vào **Claude API Key (Anthropic)** ngay trong giao diện phần mềm. Không gửi key qua Telegram hoặc đưa key vào GitHub.
3. Bấm **Ưu tiên Claude cho tất cả agent**, hoặc **Claude CEO & chiến lược, Ollama việc nhẹ**.
4. Chọn model cho từng agent: mặc định gợi ý Sonnet 4.6 cho CEO/Strategy/Compliance/Research, Haiku 4.5 cho Creative/Analyst. Opus 4.6 dành cho việc rất khó.
5. Chỉnh ngưỡng chi phí Claude ước tính (USD/tháng), bấm **Lưu cấu hình AI**.
6. Nhấn **Kiểm tra Claude API**. Nút này gọi API đọc danh sách model, không tạo văn bản tính phí. Model có thể cần được cấp quyền hoặc bật thanh toán.
7. Giao một nhiệm vụ mới cho **AI CEO**. Trong màn hình nhiệm vụ, cấu hình từng agent hiển thị tuyến model đã lựa chọn.

Không cần đổi `ANTHROPIC_API_KEY` trong PowerShell hoặc đặt file `.env`. Nếu đã lưu key, có thể để trống ô khi chỉnh sửa model khác.

Nút **Xóa Claude key** xóa key khỏi kho khóa Windows và chuyển các agent đang dùng Claude về Ollama.

## 3. Phân bổ mô hình tham khảo

| Vị trí | Gợi ý tiết kiệm nhưng chất lượng |
| --- | --- |
| AI CEO | Claude Sonnet 4.6 – lập kế hoạch, tổng hợp, kết luận |
| Strategy | Claude Sonnet 4.6 – chiến lược và phản biện |
| Compliance | Claude Sonnet 4.6 – rà soát tuyên bố quảng cáo |
| Research | Claude Sonnet 4.6 nếu dùng Claude; cần dữ liệu nguồn đáng tin cậy |
| Creative | Claude Haiku 4.5 hoặc Ollama |
| Analyst | Python tính số liệu thật + Claude Haiku 4.5 hoặc Ollama |

`claude-opus-4-6` có thể chọn riêng với chi phí cao hơn. Các tùy chọn GPT/OpenAI và Ollama vẫn được giữ để chuyển đổi bằng một menu.

## 4. Chi phí và an toàn

Giá tiêu chuẩn của Anthropic Claude API (USD / triệu token, không gồm caching và các dịch vụ đặc thù), tham khảo vào thời điểm tích hợp:

- Opus 4.6: 5 USD token vào / 25 USD token ra.
- Sonnet 4.6: 3 USD token vào / 15 USD token ra.
- Haiku 4.5: 1 USD token vào / 5 USD token ra.

Kiểm tra bảng giá hiện hành: https://platform.claude.com/docs/en/about-claude/pricing .

Ngưỡng chi phí trong Mars Studio chỉ là **ước tính cục bộ**. Chương trình tính giá từ lượng token API trả về và chặn gọi mới nếu dự toán vượt ngưỡng. Đây **không phải** giới hạn thanh toán cứng trên Anthropic Console; các lời gọi lỗi, sự cố trước khi ghi token, nhiều phiên chạy đồng thời hoặc thay đổi giá vẫn có thể khiến số tiền thực khác ước tính. Hãy dùng thêm cảnh báo và giới hạn trong Anthropic Console.

Nội dung nhiệm vụ, hồ sơ sản phẩm liên quan và prompt của agent chọn Claude sẽ được gửi đến Anthropic. Không cung cấp mật khẩu, OTP, cookie hay dữ liệu khách hàng nhạy cảm trong yêu cầu cho AI. Key lưu bằng `keyring` trong kho khóa của hệ điều hành, không ghi lại ở `integrations.local.json`, log cuộc họp AI, Telegram hoặc GitHub.

## 5. Luồng điều hành

**Chủ doanh nghiệp → AI CEO → Agent nội bộ → Trao đổi/Phản biện → CEO chốt → Báo cáo lại chủ doanh nghiệp.**

Thay đổi model không thay đổi quyền hạn: nhân viên AI không được tự quyết định cuối, tự đăng bài, đổi giá hoặc chi tiền. Không có fallback tự động sang nhà cung cấp khác khi Claude gặp lỗi; nhiệm vụ báo `blocked` để bạn chủ động chọn lại.

Ngôn ngữ nội bộ và báo cáo yêu cầu tiếng Việt chuẩn có dấu. Mô hình có thể không tuân thủ 100% yêu cầu trong mọi trường hợp; cần kiểm tra kết quả thực tế.

## 6. Kiểm thử

```powershell
cd D:\APhanMem\teabotAI
py -3 -m unittest discover -s studio/tests -v
```

Các bài test dùng Anthropic API giả lập; **chưa kiểm thử được Claude API thật trên Windows hay API key của bạn**. Hãy bấm Kiểm tra Claude API sau khi lưu.
