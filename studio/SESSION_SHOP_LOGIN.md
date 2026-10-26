# Xác minh trạng thái đăng nhập Shopee / TikTok Shop bằng trình duyệt

**Không dùng API sàn. Không dùng số cookie để kết luận đã đăng nhập.**

## Vì sao cookie không đáng tin?

Cookie có thể tồn tại dù phiên đã hết hạn, bị thu hồi hoặc đang cần OTP/CAPTCHA.
Tương tự, chỉ thấy URL `/portal/` không chứng minh có quyền sử dụng Seller Center.
Phần mềm phải xác minh bằng **trang quản trị vừa được tải lại** và các nhóm menu nội bộ đang hiển thị.

## Cách sử dụng

1. Vào **Gian hàng & Profile → Mở Chrome** trên đúng tài khoản.
2. Đăng nhập thủ công trên Shopee Seller Center hoặc TikTok Shop Seller Center.
3. Sau khi vào trang quản trị thật, phần mềm nhận diện các mục như **Sản phẩm** và **Đơn hàng** trên thanh menu; lúc này nó chỉ biết một trang riêng tư tiềm năng, **chưa vội xác nhận đăng nhập**.
4. Trình theo dõi mở một tab Chrome riêng trong cùng profile và tải lại trang quản trị để xác minh. Tab bạn đang làm việc không bị điều hướng.
5. Nút **Kiểm tra đăng nhập** yêu cầu xác minh lại ngay. Nếu Chrome Profile đóng, phần mềm mở lại cùng profile, tải trang quản trị bảo vệ, kiểm tra rồi đóng.
6. Khi Chrome do phần mềm quản lý đang mở, hệ thống định kỳ kiểm tra lại khoảng **60 giây/lần**; kết quả `Đã xác minh đăng nhập` chỉ có hiệu lực **5 phút** và kèm thời điểm kiểm tra.

## Các trạng thái

| Trạng thái | Điều kiện |
|---|---|
| Đã xác minh đăng nhập | Sau lần tải trang mới, ở đúng tên miền Seller Center, có ít nhất 2 nhóm menu quản trị riêng tư |
| Đã đăng xuất | Chuyển đến trang đăng nhập hoặc hiển thị form mật khẩu |
| Cần xác minh | Trình duyệt hiển thị OTP, CAPTCHA hay trang challenge |
| Chưa xác định | Không đọc được đủ tín hiệu, chỉ có URL/cookie hoặc kết quả cũ quá 5 phút |
| Lỗi kiểm tra | Mạng, proxy hoặc trang không tải được |
| Đang kiểm tra | Chưa có kết quả xác minh mới |

### Giới hạn độ chính xác

Không có cách nào bảo đảm phiên vẫn hợp lệ **mãi về sau**. Mỗi lần xác minh chỉ chứng minh rằng trình duyệt **vừa tải được** giao diện quản trị tại thời điểm đó.
Ứng dụng có thể dùng SPA/SSR và thay đổi DOM; nếu menu không có trong các phần tử `nav`, `aside` hoặc `role=navigation/menuitem`, kết quả sẽ là **Chưa xác định** thay vì báo Online sai.

Nếu Shopee/TikTok Shop đổi cách hiển thị thanh menu, phải điều chỉnh quy tắc DOM từ ảnh chụp giao diện thực tế hoặc tiếp tục yêu cầu bạn xác nhận thủ công.

Không tự cố vượt CAPTCHA, OTP, khóa tài khoản hoặc điều kiện sử dụng của sàn.

## Bảo mật

- Cookie tiếp tục lưu trong **Chrome Profile riêng**, không xuất ra JSON hoặc Telegram.
- Phần xác minh **không đọc cookie nữa**. Chỉ trả về tín hiệu logic từ DOM, trạng thái và thời điểm kiểm tra.
- Tệp `login_probe.json` chỉ chứa URL HTTPS của trang quản trị đã nhận diện **không có query/fragment**. Nếu URL chứa token hoặc query thì không được ghi nhận.
- `login_status.json` chỉ lưu kết quả và thời gian. Cả hai đều thuộc profile local, không đẩy lên GitHub.
- Nếu profile đang mở, không khởi chạy tiến trình thứ hai dùng cùng thư mục cookie; gửi lệnh kiểm tra cho cửa sổ hiện có.

## Cập nhật

```powershell
cd D:\APhanMem\teabotAI
git pull origin main
cd studio
.\start_windows.bat
```

Nếu đang dùng trình duyệt cũ, đóng ứng dụng và mở lại rồi nhấn `Ctrl + Shift + R`.

**Chưa được kiểm thử trực tiếp với tài khoản Shopee/TikTok Shop của bạn.**
