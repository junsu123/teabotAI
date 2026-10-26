# TEA AI MARS STUDIO — bản GUI Python trên máy cá nhân

Đây là **bản thử nghiệm có giao diện tương tác**, lấy cảm hứng từ phong cách trụ sở ảo trên Sao Hỏa trong video người dùng cung cấp. Bản đồ là đồ họa **2.5D SVG**, không phải game 3D hoặc mô phỏng 19 agent thật.

## Khởi chạy

1. Cài **Python 3.11+** trên Windows (đánh dấu **Add Python to PATH**).
2. Giải nén đủ toàn bộ thư mục ZIP.
3. Nhấp đúp `studio/start_windows.bat` hoặc dùng PowerShell:
   ```powershell
   cd studio
   py -3 run.py
   ```
4. Trình duyệt sẽ mở `http://127.0.0.1:8765`. Nếu không mở tự động, nhập địa chỉ trên thủ công.
5. Muốn đóng chương trình, quay lại cửa sổ PowerShell rồi nhấn `Ctrl+C`.

**Giao diện GUI chỉ cần Python chuẩn, không bắt buộc cài Flask/PySide6.**

## Màn hình và trạng thái

| Màn hình | Đã làm được trong bản này | Chưa làm tự động |
|---|---|---|
| Trụ sở Sao Hỏa | Bản đồ 2.5D, chọn các tòa nhà, mở thông tin AI, sơ đồ tổ chức, phóng to/nhỏ | Nhân vật 3D di chuyển, mô phỏng độc lập |
| Nhân viên AI | 6 vai trò, giao nhiệm vụ | Chạy 6 mô hình AI tự lập kế hoạch |
| Nhiệm vụ | Tạo, đổi trạng thái, lưu qua khởi động lại | Tự xử lý khi không có AI worker |
| Gian hàng | Tạo nhiều account_id, thư mục profile riêng, proxy riêng, mở Chrome để đăng nhập thủ công | Tự đăng thật trên Shopee/TikTok Shop |
| Kho sản phẩm | Quản lý SKU, tên, mô tả, giá, tồn | Tự viết/duyệt mô tả |
| Đăng sản phẩm | Tạo nhiệm vụ, duyệt/từ chối với các kiểm tra dữ liệu | Tự đăng và bấm nút cuối |
| Bộ nhớ | Lưu bài học, nguồn, trạng thái chưa xác minh | Học web định kỳ hoàn toàn tự động |
| Telegram | Hướng dẫn khởi chạy bot Python cũ; giao diện đọc cùng hàng đợi | Bật/tắt bot trực tiếp trong GUI |
| DOM | Hướng dẫn quét `input`, `label`, `placeholder` từ form HTML cục bộ với bộ công cụ cũ | Quét tùy ý trang sàn không được cho phép |

## Mở Chrome Profile và Telegram Bot

Bản GUI tận dụng mã Python từ **TEA AI Multi-Shop Python v2** bên trong `legacy/tea_ai_local`.

Cài thư viện cho phần profile/browser, **chỉ nếu muốn dùng các tính năng đó**:

```powershell
cd legacy\tea_ai_local
py -3 -m pip install -r browser_requirements.txt
py -3 -m playwright install chromium
```

Khi nhấn **Mở Chrome**, Playwright tạo `launch_persistent_context()` và mở Chrome profile phù hợp. Bạn tự đăng nhập, tự xử lý OTP và tự đóng phiên. Chức năng này có thể cần cài Google Chrome nếu profile chọn `chrome`.

Muốn chạy bot Telegram, đặt `TEA_TELEGRAM_TOKEN` và `TEA_TELEGRAM_ALLOWED_IDS` bằng biến môi trường, rồi từ `legacy/tea_ai_local` chạy:

```powershell
py -3 telegram_listing_bot.py
```

Ví dụ chú thích đính kèm ảnh:

```text
SKU=TRA-001
MODE=new
ACCOUNTS=shopee_01,tiktok_01
```

Muốn gắn thêm ảnh vào nhiệm vụ đã tạo từ GUI, dùng `ADD=ID` trong chú thích Telegram. Cần tạo sản phẩm và profile trước.

## Các thư mục dữ liệu

- `studio/data/studio.sqlite3`: lưu nhiệm vụ AI và bài học.
- `legacy/tea_ai_local/shop_accounts.json`: danh sách tài khoản.
- `legacy/tea_ai_local/listing_data/account_profiles/*`: Chrome profile, cookie và phiên đăng nhập **cần bảo mật**.
- `legacy/tea_ai_local/listing_data/listings.sqlite3`: hàng đợi đăng sản phẩm/ảnh.
- `legacy/tea_ai_local/products.json`: hồ sơ SKU.

**Không gửi nguyên thư mục chứa profile/cookies cho người khác.** Đừng sao lưu public lên GitHub. Token Telegram, mật khẩu proxy cần đặt trong biến môi trường, không lưu trong văn bản thường hoặc hộp chat.

## Hạn chế quan trọng

- Mọi thao tác đăng/cập nhật thực tế cần tuân thủ điều khoản của Shopee và TikTok Shop; bộ GUI **không tự động truy cập hoặc bấm đăng hàng**.
- Một profile Chrome không dùng song song ở hai tiến trình.
- Cookie có thể hết hạn, không được bảo đảm đăng nhập mãi mãi.
- API server chỉ lắng nghe `127.0.0.1`. Không mở cổng này ra Internet hoặc ngrok nếu chưa bổ sung hệ thống xác thực và phân quyền.
- Giao diện hiển thị "sẵn sàng" nghĩa là **vai trò đã cấu hình**, không phải AI agent đang xử lý nền.
- Đây là MVP cho Windows, chưa phải file EXE cài đặt có chữ ký số.
- Hãy đọc và kiểm tra mã nguồn trước khi dùng với thông tin cửa hàng thật.
