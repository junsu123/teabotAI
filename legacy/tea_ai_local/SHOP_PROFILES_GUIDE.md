# TEA AI – Quản lý nhiều shop với Chrome Profile riêng

**Phạm vi:** Chạy tại PC; mỗi tài khoản sở hữu một profile riêng; giữ đăng nhập bằng dữ liệu Chromium/Chrome; hỗ trợ proxy cố định; kiểm thử nhận diện trường form qua DOM trên tệp HTML nội bộ. Không dùng API Shopee/TikTok Shop. **Không có chức năng vượt CAPTCHA/2FA, giấu dấu vết bot, xoay proxy để tránh hệ thống kiểm tra hoặc tự bấm Đăng.**

## 1. Cài đặt (Windows PowerShell)

```powershell
py -3 -m pip install -r browser_requirements.txt
py -3 -m playwright install chromium
py -3 shop_profiles.py init
```

Để dùng Chrome thật, cài Google Chrome vào máy. Nếu chỉ muốn trình duyệt Chromium do Playwright quản lý, dùng `--browser chromium`.

## 2. Giao AI CEO danh sách tài khoản

```powershell
py -3 shop_profiles.py add shopee_01 shopee --alias "Shopee - Kho A" --browser chrome
py -3 shop_profiles.py add shopee_02 shopee --alias "Shopee - Kho B" --browser chrome
py -3 shop_profiles.py add tiktok_01 tiktok --alias "TikTok - Kho A" --browser chromium
py -3 shop_profiles.py list
```

Tên `account_id` dùng chữ thường, số, `_`, `-` (2–40 ký tự). Tên hiển thị không chứa mật khẩu, số điện thoại, email, OTP hay dữ liệu bí mật.

Cấu hình proxy **cố định** cho một shop khi tạo mới:

```powershell
py -3 shop_profiles.py add shopee_03 shopee --proxy http://proxy.example:8080 --proxy-env-prefix TEA_PROXY_SHOPEE03
$env:TEA_PROXY_SHOPEE03_USERNAME='proxy_user'
$env:TEA_PROXY_SHOPEE03_PASSWORD='proxy_password'
py -3 shop_profiles.py open shopee_03
```

`proxy.example` chỉ là ví dụ. Khi proxy không yêu cầu mật khẩu, bỏ `--proxy-env-prefix`. Biến môi trường tồn tại trong phiên PowerShell; nên dùng hệ thống quản lý bí mật của hệ điều hành thay vì chèn giá trị vào file cấu hình. **Không được dùng proxy để né lệnh cấm, xác thực hay hạn chế tài khoản.** Chỉ sử dụng khi nhà cung cấp dịch vụ và nền tảng cho phép.

## 3. Đăng nhập một lần trên mỗi profile

```powershell
py -3 shop_profiles.py open shopee_01
py -3 shop_profiles.py open tiktok_01
```

Bạn đăng nhập trực tiếp ở Chrome/Chromium, tự hoàn thành OTP/2FA. Khi quay về terminal và nhấn Enter, trình duyệt được đóng đúng quy trình, cookies/local storage tự lưu. Lần sau lặp lại `open` sẽ dùng profile đã lưu; phiên đăng nhập vẫn có thể hết hạn.

**Bảo mật:**

- Không gửi cookies, ảnh chụp vùng chứa mã xác thực, tệp profile hoặc mật khẩu qua Telegram.
- Sao lưu có mã hóa nếu cần; không đồng bộ profile chưa mã hóa lên Drive/Git.
- Không mở song song 2 cửa sổ tự động hóa cùng thư mục profile. Nếu file `.tea_ai_in_use` còn lại sau máy bị tắt đột ngột, hãy chắc chắn đã đóng mọi cửa sổ Chrome sử dụng profile đó trước khi xóa file khóa thủ công.
- Luôn tách profile AI khỏi profile Chrome dùng để truy cập email/ngân hàng cá nhân.
- Nếu thay đổi proxy hoặc vị trí địa lý thường xuyên, nền tảng có thể yêu cầu xác minh lại.

## 4. AI nhận biết form bằng DOM (chạy demo an toàn)

```powershell
py -3 shop_profiles.py scan-demo shopee_01 demo_product_form.html --mode new
```

Tệp được tạo: `listing_data/form_schemas/shopee_01_new.json`. Bộ quét **chỉ đọc** tag `input`, `textarea`, `select`, `[contenteditable=true]` và thuộc tính an toàn `id`, `name`, `placeholder`, `aria-label`, `data-testid`, nhãn liên kết. Không đọc giá trị ô, cookie, localStorage, password, OTP hay mã token. `suggested_field` chỉ là **gợi ý**, cần người duyệt vì tên trường có thể mơ hồ.

**Live Seller Center:** Các trang của Shopee/TikTok Shop có điều khoản hạn chế tự động hóa; phần quét/điền trực tiếp trên website chỉ nên triển khai khi có quyền phù hợp. Bản bàn giao không tự chạy quét DOM trên Seller Center và không gửi biểu mẫu lên sàn.

## 5. Ghép với AI CEO / Telegram Bot

Nhiệm vụ cần thêm `account_id` để xác định shop nhận ảnh. Hệ thống hiện có `browser_listing.py` và `telegram_listing_bot.py` được nâng cấp chấp nhận `ACCOUNT=shopee_01` hoặc `ACCOUNTS=shopee_01,tiktok_01` trong chú thích của ảnh. Một ảnh có thể sinh ra nhiều job có cùng SKU nhưng khác account. Bot chỉ nhận Telegram user ID nằm trong allowlist.

Ví dụ chú thích ảnh:

```
SKU=TRA-001 MODE=new ACCOUNTS=shopee_01,tiktok_01
```

Bot tạo các job rồi yêu cầu duyệt từng job. Mỗi job sử dụng profile đúng `account_id`, không dùng chung session. Điều kiện `SHOP` không cần khi có `ACCOUNT` hoặc `ACCOUNTS`; hệ thống lấy nền tảng theo profile.

AI CEO có thể phân phối lượt xử lý tuần tự theo tài khoản nhằm tránh xung đột profile. **Mặc định job chỉ mở trình duyệt hỗ trợ nhập tay**, không tự bấm Đăng. Chế độ tự điền hiện hữu chỉ có thể bật khi quyền tự động hóa của nền tảng được xác nhận và đã định nghĩa trường DOM chính xác. Trang web thay đổi sẽ cần quét/điều chỉnh lại.

## 6. Kiểm thử

```powershell
py -3 -m unittest discover -s tests -v
```

Không cần nhập mật khẩu/cookie hay liên hệ sàn để chạy unit tests. Cần có Playwright và Chrome/Chromium thật để chạy demo quét HTML.

## 7. Quy tắc kiểm duyệt thao tác

- Công cụ phát hiện trường form chỉ sinh bản nháp gợi ý `suggested_field`, **chưa tự xác nhận selector đúng**.
- Nếu bất kỳ locator nào chọn 0 hoặc nhiều hơn 1 phần tử, thao tác tự điền được dừng để tránh sửa sai trường.
- Nút hành động `click` trong chế độ tự điền bị khóa; sử dụng `pause` cho những chỗ cần người thao tác, nhất là bước đăng sản phẩm.
- Không dùng trình quét để lấy token, cookies, thông tin xác thực, dữ liệu khách hàng; không có cơ chế né CAPTCHA hoặc chống phát hiện tự động hóa.
- Để triển khai quét DOM/thao tác tự động vào Seller Center thật, hãy kiểm tra giấy phép của sàn. Ví dụ các quy định hạn chế bot có thể khiến shop bị giới hạn hoặc khóa; mặc định chỉ sử dụng trên form HTML mẫu nội bộ.
