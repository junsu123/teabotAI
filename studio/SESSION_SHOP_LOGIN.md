# Kiểm tra phiên đăng nhập Shopee/TikTok Shop (không dùng API)

## Cách dùng

1. Trong **Gian hàng & Chrome Profile**, bấm **Mở Chrome** ở tài khoản muốn sử dụng.
2. Đăng nhập thủ công, nhập OTP/xác minh trên trang chính thức (không nhập vào TEA AI).
3. Giữ cửa sổ Chrome được phần mềm mở. Công cụ đọc trạng thái trang Seller Center và đếm các cookie áp dụng cho tên miền đó mỗi khoảng 5 giây.
4. Quay lại Mars Studio → **Gian hàng & Profile**: xem cột **Đăng nhập**, gồm trạng thái và thời điểm kiểm tra.
5. Bấm **Kiểm tra đăng nhập** nếu cần làm mới. Nếu profile đang mở, trình theo dõi hiện tại sẽ cập nhật. Nếu profile đã đóng, hệ thống sẽ mở Chrome một lần để đọc trạng thái rồi đóng.

## Trạng thái

- **Đang đăng nhập:** tìm thấy cookie *và* dấu hiệu giao diện Seller Center đã đăng nhập (ví dụ đường dẫn `/portal/` của Shopee). Đây là kết quả tại **thời điểm kiểm tra**, không bảo đảm phiên sẽ luôn còn hiệu lực.
- **Đã đăng xuất:** đang thấy giao diện nhập mật khẩu/trang đăng nhập.
- **Chưa xác định:** có cookie nhưng trang chưa cung cấp bằng chứng đăng nhập, không có cookie, hoặc không ở trang Seller Center.
- **Đang kiểm tra:** đã yêu cầu kiểm tra nhưng chưa có kết quả.
- **Lỗi kiểm tra:** lỗi browser, mạng hoặc proxy, không đồng nghĩa đã logout.

> **Cookie còn tồn tại không đồng nghĩa vẫn đăng nhập.** Cookie có thể hết hạn, bị sàn thu hồi hoặc cần OTP lại. Quy tắc nhận biết DOM có thể cần điều chỉnh theo giao diện Seller Center thực tế.

## Bảo mật

- Chrome Profile riêng của mỗi tài khoản đã tự quản lý và giữ cookie giữa các lần mở. Không cần và **không nên** xuất cookie đăng nhập sang JSON.
- Chương trình chỉ đọc cookie trong bộ nhớ Playwright, **không lưu tên/giá trị cookie**, không gửi đến ChatGPT, Telegram, GitHub hoặc server từ xa.
- Tệp `login_status.json` nằm *trong thư mục profile cục bộ* và chỉ có `status`, `cookie_count`, `checked_at`, `message`. File và toàn bộ profile không được commit lên GitHub.
- Mỗi profile được khóa để không chạy hai cửa sổ Playwright cùng lúc. Nếu xuất hiện lỗi bị khóa, đóng các trình duyệt thuộc profile trước khi kiểm tra.
- Nếu tài khoản yêu cầu đăng nhập lại, hãy đăng nhập thủ công. Không vượt OTP/CAPTCHA hoặc cơ chế bảo vệ.

## Nếu trạng thái Chưa xác định

Kiểm tra trực tiếp trong Chrome profile rằng bạn đang ở bảng điều khiển dành cho người bán, không phải trang đăng nhập hoặc trang công khai. Nếu sàn cập nhật đường dẫn hoặc layout, logic nhận diện phải được kiểm thử và điều chỉnh. **Không tự coi như đã đăng nhập chỉ vì cookie_count > 0.**

## Kiểm thử

```powershell
cd D:\APhanMem\teabotAI
py -3 -m unittest discover -s studio/tests -v
```

Bản này chưa được kiểm thử trên phiên đăng nhập Shopee/TikTok Shop thật của bạn.
