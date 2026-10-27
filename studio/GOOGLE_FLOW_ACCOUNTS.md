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
