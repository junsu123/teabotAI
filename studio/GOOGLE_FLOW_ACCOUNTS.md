# Quản lý nhiều Google Flow Gmail và tín dụng tạo video

TEA AI Mars Studio có trang **Google Flow · Tài khoản & tín dụng** (trong menu bên trái).

## Tình trạng tích hợp thực tế

Google Flow là một dịch vụ giao diện web. Tài liệu công khai tại https://support.google.com/flow/answer/16526234?hl=vi hướng dẫn xem tín dụng bằng cách mở Flow và nhấn ảnh đại diện góc trên phải. Chưa có API Flow công khai được xác nhận là hỗ trợ chính thức việc kiểm tra số dư nhiều Gmail và tự tạo video qua các phiên đăng nhập trong phần mềm này.

**Tính năng đã hoạt động:** nhập Gmail, lưu tín dụng do chủ xác nhận, lưu thời gian kiểm tra, phân 5 prompt đã kiểm duyệt vào từng Gmail đủ điểm, dành chỗ tín dụng để không đặt quá số dư, tự phân lại các prompt CHƯA tạo sang Gmail khác khi chủ cập nhật một tài khoản hết điểm, lưu hoàn thành do chủ xác nhận và điểm ước tính đã dùng.

**Chưa tự động:** đăng nhập Google, đọc điểm từ giao diện Flow, gửi prompt/nạp ảnh 3D vào Flow, chờ kết quả render, tải file MP4, vượt CAPTCHA/kiểm tra đăng nhập hoặc chuyển phiên đăng nhập để tự động chạy nhiều Gmail. Bấm “Mở Google Flow” mở trang chính thức, bạn chọn đúng tài khoản, dán prompt và tạo video trong Google Flow. Việc tự động chuyển tài khoản trong phần mềm là **phân bổ công việc theo số dư**, không phải tự chuyển tài khoản Google trong trình duyệt. Không hỗ trợ vượt hạn mức tài khoản hoặc điều khoản Google.

## Cách sử dụng

1. Đóng phần mềm và mở PowerShell:
   ~~~powershell
   cd D:\APhanMem\teabotAI
   git pull origin main
   cd studio
   .\start_windows.bat
   ~~~
   Mở http://127.0.0.1:8765 rồi Ctrl+Shift+R.
2. Mở **Google Flow · Tài khoản & tín dụng**, dán mỗi Gmail một dòng và bấm **Thêm Gmail vào database**. Không nhập mật khẩu, OTP, cookie hay mã khôi phục Google vào phần mềm.
3. Mở https://labs.google/fx/tools/flow ở từng tài khoản được phép sử dụng. Nhấn ảnh đại diện bên phải để xem số điểm còn. Trở lại phần mềm, nhập số tín dụng chính xác và bấm **Lưu điểm**. Có thể nhập nhãn Chrome profile để tự nhận biết, nhưng nhãn này chưa tự mở Chrome profile.
4. Tại **Xưởng SEO · Giá · Google Veo 3**, giao việc cho CEO, chờ hoàn tất kiểm duyệt để có **5 prompt 8 giây**. Tại mục Google Flow, chọn nhiệm vụ và chế độ model, nhấn **Tạo hàng đợi 5 cảnh**.
5. Bộ phân bổ sẽ chọn tài khoản có số dư vừa được xác nhận trong 12 giờ và đủ điểm. Số tín dụng dự kiến của những prompt đã phân được **dành chỗ** chứ chưa bị trừ. Để thực hiện, sao chép prompt → mở Flow → đăng nhập bằng Gmail được gán → chọn đúng model, 8 giây và số video tạo → tạo thật.
6. **Chỉ sau khi video đã được tạo thành công**, nhấn **Xác nhận video đã tạo** trên đúng cảnh. Phần mềm ghi hoàn thành và trừ số điểm dự kiến. Hãy cập nhật lại số điểm thật đọc từ Flow để đối chiếu nếu phát sinh thêm thế hệ video hoặc chi phí khác.
7. Nếu một tài khoản hết điểm, nhập **0** cho Gmail đó. Hàng đợi của các prompt chưa xác nhận sẽ được phân lại cho tài khoản khác có đủ số điểm đã xác minh, nếu có. Nếu không tài khoản nào đủ, nhiệm vụ ở trạng thái chờ.

## Điểm tín dụng

Theo tài liệu Google Flow hiện hành (đã tra ngày 27/10/2026):
- Tài khoản chưa có gói Google AI: 50 tín dụng/ngày; không tự cộng 50 vào database theo đồng hồ. Bạn cần đọc lại số dư thực trên Flow sau khi làm mới.
- Veo 3.1 Lite: 10 điểm/video 8s cho người dùng không thuộc gói Ultra; Ultra có cách tính khác.
- Veo 3.1 Fast: 20 điểm/video cho người dùng không thuộc Ultra.
- Veo 3.1 Quality: 100 điểm/video.
- Giá được tính **mỗi lượt tạo video**, không nhất thiết mỗi lần bấm gửi prompt; Flow có thể tạo hơn 1 video/1 lần yêu cầu và Google có thể đổi chi phí bất cứ lúc nào. Xem mức điểm tại Settings ở vùng prompt của Flow trước khi chạy.

Hàng đợi lưu giá dự kiến theo bảng trên; không tự đọc giá hiện tại từ Flow. Nếu tài khoản đang dùng gói Ultra hoặc video tạo nhiều phiên bản, số dư thực có thể khác ước tính. Đừng xem số dư do phần mềm tính là số dư chính thức của Google. Khi phát hiện khác biệt, ghi lại số dư vừa đọc ở Flow.

## Bảo mật & chính sách

- Chỉ lưu địa chỉ email, nhãn profile, số điểm người dùng nhập và prompt video; **không lưu mật khẩu Google, cookies hoặc token đăng nhập Flow**.
- Tài khoản phải do người dùng sở hữu/quản lý hợp lệ; tất cả lượt tạo phải tuân thủ điều khoản và hạn mức của Google Flow. Không tự chuyển để né các biện pháp ngăn chặn, giới hạn hoặc điều kiện đăng ký gói của Google.
- Mỗi cảnh cần có prompt đã được phòng kiểm duyệt thông qua và người chủ vẫn phải duyệt trước khi phát hành.
- Không hứa tự tạo/tải video MP4 khi chưa có tích hợp tạo video chính thức.

Nếu tương lai Google cung cấp API Flow được hỗ trợ hoặc bạn chọn API tạo video riêng có giấy phép (ví dụ Gemini API/Google enterprise), có thể nối backend vào hàng đợi. **Tín dụng của API đó không mặc nhiên dùng chung với tín dụng Flow giao diện web.**


## Chrome profile riêng theo từng Gmail (cập nhật 27/10/2026)

1. Tại màn Google Flow · Tài khoản & tín dụng, chọn **+ Thêm tài khoản**.
2. Nhập một Gmail rồi nhấn **Tạo profile & mở Flow**.
3. Phần mềm tạo thư mục profile riêng trong `studio/data/flow_chrome_profiles/<profile_id>/` và mở Google Chrome với `--user-data-dir` trỏ vào thư mục đó.
4. Tự đăng nhập Google trong cửa sổ mới. Chrome lưu phiên trên máy; không cần nhập mật khẩu, cookie hoặc OTP trong Mars Studio.
5. Lần sau bấm nút **◎** ở đúng dòng tài khoản để mở lại profile, không sử dụng Chrome mặc định.
6. Thêm theo danh sách: mỗi Gmail có thư mục profile riêng, nhưng không tự mở hàng loạt cửa sổ.
7. Các Gmail đã lưu trước đây được cấp profile khi cập nhật, giữ nguyên số dư và hàng đợi.
8. Trong hàng đợi 5 prompt, nút **Mở Flow đúng profile** dùng Gmail đã phân công cho cảnh; cảnh chưa phân Gmail không thể mở profile.

Liên kết lưu lâu dài: `flow_jobs.email` → `flow_browser_profiles.email` → `profile_id` → thư mục Chrome riêng. Hàm `flow_profiles.profile_for_job()` kiểm tra phân công trước khi trả về profile tương ứng. Tích hợp dữ liệu/video được cấp phép trong tương lai phải sử dụng chính liên kết này.

### Bảo mật và giới hạn

- **Đã làm:** tạo thư mục Chrome profile riêng, gắn với Gmail, mở đúng profile, giữ phiên cục bộ, chặn mở trùng profile trong ứng dụng.
- **Chưa làm:** tự động đọc số dư tín dụng, xác minh đăng nhập Google, gửi prompt, render và tải MP4 bằng Google Flow. Các chức năng này cần tích hợp riêng được phép; hiện vẫn thao tác thủ công.
- Chrome được mở trực tiếp trên máy bằng trình duyệt cài sẵn. Google có thể yêu cầu xác minh hoặc đăng nhập lại.
- Mọi cookie/phiên đăng nhập của Chrome được bảo vệ như dữ liệu nhạy cảm. Dữ liệu nằm trong `studio/data/`, bị `.gitignore` loại trừ; không đưa profile lên GitHub/Telegram.
- Nếu ứng dụng hoặc Chrome tắt đột ngột, file khóa `.flow_browser_in_use` có thể tồn tại. Chỉ xử lý file khóa khi đã đóng mọi cửa sổ Chrome tương ứng.
- Chỉ dùng tài khoản bạn được phép sử dụng; profile riêng không đồng nghĩa có quyền vượt hạn mức hoặc dùng API không công khai.

## Đọc tín dụng Flow từ chính Chrome profile (bổ sung 27/10/2026)

- Sau khi đăng nhập trong Chrome profile riêng, hãy **đóng cửa sổ Chrome của tài khoản đó**. Mars Studio sẽ tự thử mở lại cùng profile ở chế độ đọc thông tin để kiểm tra phần tử chữ `span.credits-count` trên Google Flow (ví dụ `1.016 tín dụng Google Flow` được hiểu là 1016 điểm).
- Có thể chủ động kiểm tra bằng nút **↻** tại dòng Gmail. **Phải đóng Chrome profile đó trước khi bấm ↻** để tránh hai tiến trình cùng sử dụng thư mục profile.
- Nút **✎** dùng để nhập tín dụng thủ công và chỉnh nhãn Chrome. Nút làm mới tổng thể chỉ tải lại kết quả hiện có ở database.
- Khi đọc được điểm, hệ thống lưu số nguyên, nguồn `browser_dom` và thời gian cập nhật trong SQLite `flow_accounts`. Phần mềm phân bổ video theo số dư này giống như số nhập thủ công.
- Nếu Google chuyển đến trang đăng nhập, đổi bố cục, hoặc cần xác minh tài khoản, tính năng báo **Đọc điểm chưa thành công** và **không ghi đè số dư cũ**. Chủ tài khoản vẫn có thể nhập điểm thủ công.
- Đọc thông tin giao diện là phương thức best-effort, không phải API kiểm tra điểm được Google chứng nhận. Giao diện hoặc chính sách Google thay đổi có thể làm mất khả năng kiểm tra.
- **Cookie:** Chrome đã lưu cookie đăng nhập cục bộ trong thư mục profile. Phần mềm **không xuất, sao chép, in, gửi hay lưu thêm cookie** vào SQLite, JSON hoặc GitHub. Không cung cấp cookie hay OTP cho bất kỳ tiện ích/dịch vụ lạ nào.
- Đảm bảo đăng nhập đúng Gmail ở từng profile; công cụ đọc chữ hiện chưa xác minh độc lập chủ sở hữu Gmail đang đăng nhập.

## Xóa Chrome profile và Reload tín dụng toàn bộ (27/10/2026)

- Nút **▤ Xóa** trên mỗi dòng Flow yêu cầu xác nhận, sau đó xóa Gmail khỏi danh sách cùng toàn bộ thư mục Chrome riêng và cookie/phiên lưu trong thư mục đó. **Đóng cửa sổ Chrome của profile trước khi xóa**. Không thể hoàn tác.
- Nếu có cảnh video chưa thực hiện đang gán Gmail này, cảnh đó được trả về hàng chờ và phân bổ lại cho Gmail đủ tín dụng. Video **đã hoàn thành** vẫn giữ email lịch sử để truy vết.
- Hệ thống di chuyển thư mục Chrome sang vị trí xóa tạm trước khi cập nhật SQLite; nếu cập nhật database lỗi, thư mục được đưa về vị trí cũ. Nếu không thể xóa hết file trên Windows, phần mềm cảnh báo tên thư mục tạm còn lại.
- Các nút **Nạp lại** và **Làm mới tất cả** giờ khởi động một lượt đọc số dư cho **tất cả Gmail đang bật**. Mỗi profile được mở bằng Chrome ở chế độ đọc (headless) **lần lượt**, dùng đúng dữ liệu đăng nhập cục bộ.
- Profile nào hiện còn một cửa sổ Chrome đang mở sẽ được **bỏ qua**, tránh hỏng profile hoặc xung đột khóa. Đóng Chrome rồi bấm Reload lại nếu muốn kiểm tra profile đó.
- Bảng hiển thị tiến độ Reload và thông báo kết quả cập nhật/lỗi/bỏ qua. Nếu đọc được chữ tín dụng, lưu điểm, nguồn `browser_dom` và thời gian kiểm tra; nếu không đọc được thì **không ghi đè số dư cũ**.
- Đây là cách đọc chữ đang hiển thị, không phải API chính thức của Google Flow. Google có thể thay đổi giao diện hoặc yêu cầu xác minh đăng nhập. Chỉ sử dụng với các tài khoản bạn sở hữu và trong giới hạn quyền được phép.
