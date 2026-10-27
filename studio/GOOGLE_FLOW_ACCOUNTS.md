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

## Thêm một Gmail → đăng nhập → xác minh điểm → tự đóng Chrome

- Bấm **+ Thêm tài khoản**, nhập một Gmail rồi **Tạo profile & mở Flow**. Phần mềm tạo (hoặc dùng lại) thư mục Chrome profile riêng và mở cửa sổ Chrome có thể thao tác đăng nhập bằng tay.
- Trình theo dõi chỉ đọc thông tin đang hiển thị trên trang Flow: liên kết AccountChooser cung cấp **địa chỉ Gmail đầy đủ**, phần tử `credits-count` hiển thị **tín dụng**. Chỉ khi Gmail đúng với tài khoản đã đăng ký và giá trị số hợp lệ, phần mềm mới lưu điểm vào SQLite và **đóng cửa sổ Chrome được quản lý**.
- Browser tự lưu và tái sử dụng cookie/phiên đăng nhập trong thư mục profile. Phần mềm **không xuất hoặc nhân bản cookie đăng nhập**, không gửi chúng đến API hoặc tệp văn bản.
- Trạng thái ở bảng Flow: chờ đăng nhập, đang xác minh, nhầm Gmail, đã cập nhật tín dụng, hoặc không thể theo dõi.
- **Giới hạn:** Một số quy trình đăng nhập Google có thể từ chối Chrome được điều khiển bằng Playwright. Nếu gặp tình huống này, dùng nút **◎** để mở Chrome thường, đăng nhập thủ công và đóng lại, sau đó dùng **↻** để kiểm tra tín dụng. Chế độ dự phòng này không tự đóng cửa sổ.
- Nếu không xác minh được Gmail hoặc không thấy tín dụng, phần mềm **không đóng tự động với lý do thành công** và không ghi dữ liệu không xác minh. Bạn có thể tiếp tục thao tác hoặc đóng cửa sổ thủ công.
- Việc xác minh dựa trên bố cục hiện tại của Google Flow, **không phải API Google hỗ trợ chính thức**. Cần kiểm tra thực tế trên Windows sau khi cập nhật phần mềm.

## Tạo profile mới mà không nhập Gmail trước (27/10/2026)

- Nút **+ Thêm tài khoản** lập tức tạo một thư mục Chrome profile độc lập có ID ngẫu nhiên và mở trang Google Flow. Bạn **không cần nhập Gmail** vào phần mềm.
- Bạn đăng nhập Google như bình thường. Sau khi Flow hiển thị trang tài khoản, ứng dụng đọc **chỉ văn bản đang hiển thị** trong `.user-email` và `.credits-count`, theo ảnh DevTools bạn cung cấp. Có thể cần mở menu ảnh đại diện để số điểm và địa chỉ email hiển thị.
- Khi nhận được **email hợp lệ và số tín dụng**, phần mềm đóng cửa sổ Chrome, lưu phiên của Chrome vào profile đó rồi tạo Gmail mới trong SQLite, liên kết với chính ID profile và số dư đã đọc. Số tín dụng được đánh dấu nguồn `browser_dom`.
- Nếu Gmail đã tồn tại, phần mềm thông báo trùng tài khoản, **không ghi đè profile hoặc số dư cũ** và xóa profile tạm sau khi Chrome đóng.
- Nếu bạn đóng cửa sổ trước khi xác minh, phần mềm không tạo tài khoản không rõ Gmail và dọn profile tạm.
- Cookie, mật khẩu, mã OTP và token đăng nhập **không được xuất, đọc, gửi về API hoặc lưu vào SQLite**. Chrome tự quản lý cookie trong thư mục profile riêng (đã được `.gitignore` loại trừ).
- Chỉ **Thêm theo danh sách** mới tiếp tục có ô nhập nhiều địa chỉ Gmail. Đây là chế độ khác với nút + Thêm tài khoản.
- Chức năng đọc nội dung trang không phải API Google chính thức. Nếu Google thay đổi bố cục hoặc từ chối trình duyệt tự động hóa, bảng sẽ hiển thị trạng thái lỗi và không lưu một Gmail chưa xác minh; cần kiểm tra thực tế trên Windows.

## Khắc phục Google chặn đăng nhập bằng trình duyệt tự động (27/10/2026)

Google có thể trả về `Couldn't sign you in` khi Playwright trực tiếp khởi chạy Chrome (và Chrome hiển thị cảnh báo `--no-sandbox`). Vì vậy **nút + Thêm tài khoản không dùng Playwright lúc đăng nhập nữa**.

- **Bấm + Thêm tài khoản:** ứng dụng tạo thư mục Chrome riêng và dùng Google Chrome cài trên máy với `--user-data-dir`, `--new-window`. Không thêm `--no-sandbox`, `--remote-debugging-port`, cờ bỏ qua xác minh hay sửa user-agent.
- **Bạn đăng nhập trong cửa sổ Google Chrome thật**, tự vượt qua các bước xác minh hợp lệ nếu Google yêu cầu. **Sau khi đăng nhập thành công, đóng cửa sổ Chrome**. Chương trình mới thử đọc trang Flow ở chế độ chỉ đọc, trên chính profile vừa đăng nhập.
- Nếu đọc được `.user-email` và `.credits-count` trên `labs.google` hoặc `flow.google.com`, Gmail và số dư được gắn vào profile; không cần nhập Gmail trước.
- **Nếu không đọc được:** profile chưa bị xóa. Chương trình cho phép xác nhận Gmail và số dư mà bạn đã nhìn thấy trên trang để sử dụng lại phiên Chrome đang lưu (chỉ xảy ra như phương án dự phòng). Không tuyên bố tự động thành công khi chưa xác minh.
- Nếu nhập Gmail đã được lưu trước đây, chương trình không ghi đè Chrome profile hay tín dụng cũ.
- **Không thể bảo đảm tự đóng cửa sổ ngay khi đăng nhập** nếu không điều khiển Chrome trong bước đăng nhập; phiên bản an toàn này yêu cầu bạn tự đóng Chrome rồi mới đọc dữ liệu.
- Chrome tiếp tục tự quản lý cookie trong thư mục riêng, không xuất cookie thô ra phần mềm, GitHub hoặc file JSON.
- Tài khoản đăng nhập với Chrome đã qua kiểm tra thủ công vẫn có thể bị Google yêu cầu đăng nhập lại; không có cơ chế vượt qua chính sách bảo mật Google.


## Luồng hiện hành: Windows UI Automation, KHÔNG cần cài Extension (28/10/2026)

**Phần này thay thế các mô tả về Extension và Playwright đăng nhập ở các mục lịch sử phía trên.**

1. Trên Windows, cập nhật code và chạy `studio/setup_windows.bat` **một lần** để cài `pywinauto`, là thư viện Windows UI Automation. Đây là thư viện Python cho Mars Studio, **không phải tiện ích trình duyệt**.
2. Nhấn **+ Thêm tài khoản**. Mars Studio tạo Chrome profile trống độc lập, mở đúng Chrome đã cài với `--user-data-dir` riêng và trang Google Flow; không yêu cầu nhập Gmail trước.
3. Đăng nhập tài khoản Google bằng chính cửa sổ Chrome đó. **Mở menu ảnh đại diện** để các thông tin email và tín dụng hiển thị trên màn hình (ví dụ `owner@gmail.com`, `996 tín dụng Google Flow`). Bạn không cần F5 hay cài `Load unpacked`.
4. Windows UI Automation chỉ đọc các tên Text/Hyperlink trợ năng của **cửa sổ Chrome thuộc đúng tiến trình/profile vừa mở**, bỏ qua các trường Edit/Password. Phần mềm yêu cầu **hai lần đọc liên tiếp giống nhau**, đúng một email hợp lệ và một giá trị tín dụng có nhãn Google Flow.
5. Sau khi xác minh, lưu Gmail, số điểm, thời gian và ID profile bằng một giao dịch SQLite, sau đó **yêu cầu đóng nhẹ nhàng đúng cửa sổ Chrome đó**. Chrome tự lưu cookie/session vào profile như bình thường; phần mềm không đọc cookie, token, mật khẩu hoặc OTP.
6. Nếu Gmail đã nằm trong danh sách, không ghi đè Gmail/điểm/profile cũ. Profile tạm mới bị dọn sau khi cửa sổ Chrome đóng.
7. Nếu thiếu quyền trợ năng, phiên Chrome không hiển thị email/điểm, hoặc Google đổi cấu trúc trợ năng: phần mềm **giữ nguyên phiên đăng nhập** và thông báo bạn đóng Chrome, sau đó có thể tự xác nhận Gmail/điểm để gắn đúng profile. Số do bạn xác nhận có nguồn `manual`, còn số UIA đọc được có nguồn `browser_uia`.

**Lưu ý về độ tin cậy:** Windows UI Automation của Chrome có từ Chrome 138, nhưng **không bảo đảm mọi thành phần Google Flow đều được đưa vào cây trợ năng**. Chức năng này là best-effort, **không phải API chính thức của Google**. Chưa có kiểm thử đăng nhập trực tiếp trên máy Windows của bạn. Nếu phần mềm không đọc được số, hãy nhấn vào menu tài khoản để hiện thông tin và kiểm tra thư viện pywinauto đã được cài.

**Các thao tác khác:** Nút Reload tín dụng của tài khoản có sẵn vẫn sử dụng luồng kiểm tra riêng và cần kiểm chứng thực tế; thay đổi này áp dụng cho **bước + Thêm tài khoản mới**. Toàn bộ dữ liệu Chrome vẫn lưu dưới `studio/data/flow_chrome_profiles/` và không tải lên GitHub.
