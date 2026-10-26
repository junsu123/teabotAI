# TEA AI Mars Studio v2 – Quản lý Proxy và Học thao tác bằng nút bấm

## Khởi chạy trên Windows

1. Cài Python 3.11 hoặc mới hơn từ python.org và cài Google Chrome.
2. Giải nén toàn bộ ZIP; không chạy trực tiếp tệp nằm trong ZIP.
3. Nhấp đúp **`studio/setup_windows.bat`** để cài Playwright và keyring (chỉ cần một lần).
4. Nhấp đúp **`studio/start_windows.bat`**. Nếu trình duyệt không tự mở, nhập `http://127.0.0.1:8765`.
5. Không cần gõ lệnh để **thêm/sửa/xóa proxy, gán proxy, mở profile hoặc ghi thao tác mẫu**.

## Thêm proxy hoàn toàn từ giao diện

1. Ở menu bên trái, chọn **Kho Proxy → + Thêm proxy**.
2. Điền mã proxy, tên, loại (HTTP/HTTPS/SOCKS5), IP/tên miền, port và, nếu có, username/password.
3. Bấm **Thêm proxy**. Mật khẩu (nếu nhập) được lưu qua kho mật khẩu hệ điều hành với thư viện `keyring`. SQLite chỉ lưu username và host/port. **Không lưu mật khẩu sàn và không lưu cookie trong kho Proxy.**
4. Có thể nhấp **Thử kết nối** để kiểm tra kết nối TCP đến host:port; đây **không phải** kiểm tra proxy dùng được để đăng nhập, không xác nhận xác thực hoặc địa chỉ IP thoát.
5. Chọn **Gian hàng & Profile → Thêm gian hàng** và chọn proxy trong danh sách. Với profile đã tạo, chọn **Gán proxy**.
6. Đóng profile Chrome trước khi thay proxy. Mỗi gian hàng dùng một thư mục profile riêng, lưu phiên đăng nhập trên máy; cookie có thể hết hạn.

## Học đăng bài bằng nút trong phần mềm

1. Vào **Học đăng bài (trình duyệt) → Bắt đầu học** hoặc nút **Học đăng bài** tại mỗi gian hàng.
2. Chọn profile, `Đăng mới`/`Cập nhật`, chọn **Form demo nội bộ** (mặc định) để thử.
3. Chỉ chọn **Seller Center** khi bạn được phép dùng trình ghi thao tác theo quy định nền tảng và tích vào ô xác nhận quyền.
4. Chrome mở; bạn bấm/điền form như bình thường. Công cụ chỉ lưu sự kiện click/change và **metadata DOM** như tag, id, label, placeholder, name, data-testid. **Không lưu nội dung form, cookie, password, OTP, số điện thoại hoặc email.**
5. Quay lại **Học đăng bài**, bấm **Dừng & lưu**. Bấm **Xem dữ liệu** để kiểm tra kết quả.
6. Bản học là dữ liệu tham chiếu, **chưa được biến thành tự động điền hoặc tự bấm nút đăng**. Cần người quản lý phê duyệt selector trước khi triển khai bước tiếp theo.

## Phần nào đã hoạt động, phần nào chưa

**Đã:** UI quản lý proxy, gán proxy theo account, kiểm tra kết nối TCP, lưu tài khoản/profile, mở profile bằng nút, bật/dừng phiên ghi DOM thao tác bằng nút, lưu JSON và xem bản ghi.

**Chưa:** học bằng AI để hiểu mọi giao diện sau một lần mẫu, điền form Shopee/TikTok Shop tự động, bấm đăng, vượt CAPTCHA, hỗ trợ đăng hàng khi bị nền tảng cấm, hay chạy nền khi máy tắt.

## Lưu trữ và bảo mật

- `studio/data/proxy_catalog.sqlite3`: địa chỉ proxy, username (không chứa mật khẩu).
- Kho mật khẩu hệ điều hành: mật khẩu proxy (Windows Credential Locker khi backend keyring khả dụng).
- `legacy/tea_ai_local/shop_accounts.json`: liên kết account → proxy ID, **không chứa mật khẩu**.
- `legacy/tea_ai_local/listing_data/account_profiles/`: Chrome profile chứa phiên đăng nhập, **cần bảo vệ và không chia sẻ**.
- `studio/data/training/`: các bản ghi DOM không chứa giá trị người dùng nhập.
- `studio/data/studio.sqlite3`: dữ liệu công ty AI.

Không đưa thư mục dữ liệu lên GitHub hoặc gửi qua Telegram. Chương trình chỉ lắng nghe cổng loopback 127.0.0.1.

## Lưu ý kỹ thuật

- Playwright có thể dùng phiên Chrome persistent qua `launch_persistent_context`; một profile chỉ mở ở một tiến trình tại một thời điểm.
- Trình ghi dựa vào API `browser_context.add_init_script()` và `expose_binding()` của Playwright, có thể bỏ sót thao tác trong iframe bị hạn chế hoặc widget canvas đặc biệt.
- Tài khoản đăng nhập có thể yêu cầu OTP/captcha; phần mềm không tự vượt hoặc giải các thử thách này.
- Tùy chính sách của sàn, chế độ ghi thao tác thật có thể không được phép; khi chưa rõ, chỉ dùng form demo và thao tác Seller Center bằng tay.
