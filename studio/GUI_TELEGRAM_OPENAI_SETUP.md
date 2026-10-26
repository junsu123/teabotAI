# Cài đặt ChatGPT/OpenAI và Telegram trực tiếp trên TEA AI Mars Studio

Từ bản nâng cấp này, **không cần tạo/sửa .env hoặc gõ lệnh đặt token/key**.
Các khóa bí mật lưu trong **Windows Credential Manager** thông qua `keyring`. Phần cài đặt thông thường và vận hành bot đều thực hiện trong trình duyệt của Mars Studio trên localhost.

## Cập nhật một lần trên Windows

Đóng cửa sổ phần mềm cũ rồi mở PowerShell:

```powershell
cd D:\APhanMem\teabotAI
git pull origin main
cd studio
.\setup_windows.bat
.\start_windows.bat
```

`setup_windows.bat` chỉ cần chạy **một lần sau nâng cấp** để cài gói `keyring` và `python-telegram-bot`. Các lần sau chỉ cần bấm đúp `start_windows.bat`.

Trong trình duyệt mở `http://127.0.0.1:8765`, nhấn Ctrl + Shift + R để làm mới JavaScript. Chọn **⚙ Cài đặt ChatGPT & Telegram** ở thanh menu.

## 1. ChatGPT / OpenAI API

1. Tạo key tại https://platform.openai.com/api-keys (API có chi phí riêng với gói ChatGPT).
2. Dán key vào ô **OpenAI API Key** của phần mềm.
3. Chọn nhà cung cấp **OpenAI API** hoặc **Ollama** cho từng agent.
4. Chọn model **gpt-6.1-sol** hoặc **gpt-6-luna**. Khuyên dùng OpenAI cho CEO trước, các phòng ban khác chạy Ollama tiết kiệm chi phí.
5. Điền ngân sách USD/tháng rồi bấm **Lưu cấu hình ChatGPT**.
6. Bấm **Kiểm tra API key**. Đây là lệnh đọc danh sách model, *không tạo câu trả lời có tính phí*. Nếu model đã chọn không xuất hiện trong danh sách được phép dùng, phần mềm cảnh báo.
7. Giao nhiệm vụ mới cho AI CEO. Những lượt gọi mô hình tiếp theo sẽ sử dụng tuyến model đã lưu.

Thay đổi lựa chọn sẽ áp dụng từ lần gọi mô hình tiếp theo; **không đổi model giữa một lượt API đang xử lý**.

**Xóa API key**: nút *Xóa API key đã lưu*. Tất cả agent tự chuyển lại Ollama. Key không bao giờ hiện lại trong ô sau khi lưu.

**Dữ liệu gửi đi**: nếu agent dùng OpenAI, nội dung nhiệm vụ cùng hồ sơ sản phẩm cần thiết được truyền đến OpenAI; không đưa dữ liệu đăng nhập sàn, cookie hay khách hàng vào lời giao việc. Phần mềm đặt `store:false` với OpenAI Responses API. Ngưỡng ngân sách nội bộ chỉ là ước tính; hãy cấu hình thêm cảnh báo trên tài khoản API của bạn.

## 2. Telegram Bot

1. Mở Telegram, tìm **@BotFather** chính thức.
2. Nhắn `/newbot`, đặt tên và username cho bot, sao chép Bot Token.
3. Trong phần mềm → **Cài đặt ChatGPT & Telegram** hoặc **Telegram Bot**, dán Bot Token.
4. **Chưa biết Telegram User ID?** Để trống danh sách User ID, bấm **Lưu Telegram**, sau đó bấm **Bật Bot**. Tìm bot vừa tạo trong Telegram và nhắn `/myid`. Bot chỉ trả về **User ID của chính người hỏi**, các chức năng khác vẫn bị khóa.
5. Trở lại phần mềm, bấm **Tắt Bot**, nhập User ID dạng số vào ô *Telegram User ID được phép* (nhiều ID phân cách dấu phẩy), bấm **Lưu Telegram**, rồi **Bật Bot** lại.
6. Bấm **Kiểm tra token** để xác thực token bằng Telegram Bot API `getMe`.
7. Nếu muốn bot tự chạy khi phần mềm mở, tích **Tự chạy Telegram Bot khi khởi động** rồi lưu.

Các thao tác **Bật Bot / Tắt Bot** trên giao diện điều khiển một tiến trình Python cục bộ. Bot phải chạy trên máy tính của bạn để nhận tin nhắn, và chỉ nhận ảnh/chú thích theo chức năng của phiên bản này; **không tự đăng hàng lên Shopee/TikTok Shop**.

Các lệnh hiện có: `/start`, `/myid`, `/status ID`, `/approve ID`, `/reject ID`. Những lệnh khác ngoài `/myid` chỉ cho phép User ID có trong danh sách cấp quyền.

**Xóa Bot Token:** Tắt Bot, sau đó nhấn *Xóa token đã lưu*. Token được xóa khỏi kho mật khẩu Windows.

## 3. Bảo mật & dữ liệu

- `OPENAI_API_KEY` và `TEA_TELEGRAM_TOKEN` không được ghi vào file .env/JSON, cơ sở dữ liệu hay GitHub.
- Thông tin khóa chỉ giữ trong Credential Manager của Windows; giao diện chỉ hiển thị **đã lưu / chưa lưu**.
- Các tùy chọn không nhạy cảm (mô hình, agent, chi phí, Telegram ID được phép) lưu trong `studio/data/integrations.local.json` — ngoài GitHub.
- Khi khởi động bot, phần mềm truyền token vào **biến môi trường tạm của tiến trình Python con**, không ghi xuống file và không hiển thị trên dòng lệnh. Đây là chi tiết triển khai nội bộ; bạn không cần cấu hình biến môi trường.
- Bộ điều hành vẫn **chỉ nhận lệnh từ chủ qua AI CEO**. Các tính năng kỹ thuật kết nối không thay đổi nguyên tắc.
- Bảo vệ máy tính Windows và không chia sẻ thư mục profile hay kho khóa hệ điều hành.
- Bộ lọc/ngôn ngữ hướng dẫn agent bắt buộc **tiếng Việt**, ngoại trừ tên model, mã sản phẩm và tên thuộc tính JSON.
- Khóa OpenAI không được tích hợp trực tiếp với tài khoản ChatGPT trên website. ChatGPT Plus/Pro và API là hai dịch vụ thanh toán độc lập.

## Khắc phục lỗi

- **Lưu token thất bại:** chạy lại `setup_windows.bat`, kiểm tra Windows Credential Manager hoạt động và tài khoản Windows có quyền sử dụng.
- **Không bật được Bot:** kiểm tra token, kết nối mạng; nếu chưa cài `python-telegram-bot` hãy chạy `setup_windows.bat`.
- **Bot vừa bật rồi dừng:** có thể token sai, mạng không thông hoặc token đang được dùng bởi tiến trình polling khác. Dừng chương trình Bot cũ rồi bấm Kiểm tra token.
- **OpenAI trả HTTP 401/403:** key hoặc quyền truy cập model chưa hợp lệ. Có thể trả HTTP 429 khi hết hạn mức/quá giới hạn.
- **Ollama bị thiếu:** khi đã chọn OpenAI cho CEO, CEO vẫn có thể chạy không cần Ollama; agent khác vẫn dùng Ollama theo cấu hình.
- **Log không hoạt động:** kiểm tra Ollama/OpenAI API key và trạng thái `blocked`, rồi thử lại nhiệm vụ.

## Kiểm thử

```powershell
cd D:\APhanMem\teabotAI
py -3 -m unittest discover -s studio/tests -v
```

CI kiểm thử luồng cấu hình bằng kho keyring và phản hồi API giả lập. **Chưa thử trên tài khoản Bot, API key hoặc Windows của bạn**, nên bấm *Kiểm tra* sau khi lưu để xác nhận kết nối thực.
