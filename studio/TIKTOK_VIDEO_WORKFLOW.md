# Quy trình nghiên cứu TikTok và sản xuất Video AI trong TEA AI Mars Studio

Bản cập nhật bổ sung một dây chuyền nội bộ do **AI CEO** điều hành.

## Quy trình

1. Chủ doanh nghiệp giao brief sản phẩm cho AI CEO.
2. Phòng Nghiên cứu TikTok (AI Research): tìm tiêu đề/tác giả công khai nếu TikTok cho phép qua oEmbed và kết hợp ghi chú/transcript thực tế do chủ cung cấp; đề xuất hook và góc triển khai nguyên bản. Không khẳng định đã xem hình/âm thanh video, lượt xem hoặc phản hồi khi chưa truy cập được.
3. Phòng Biên kịch (AI Creative): đề xuất hai kịch bản tiếng Việt, mỗi kịch bản 5 cảnh khoảng 8 giây.
4. Phòng Kiểm duyệt (AI Compliance): rà soát nội dung công dụng, giấy tờ, chứng nhận và yêu cầu chỉnh sửa nếu thiếu bằng chứng; chỉ đồng ý khi đạt yêu cầu.
5. Phòng Video AI: nhận kịch bản đã duyệt và tạo gói storyboard, prompt video, voiceover, phụ đề và chuyển cảnh; chưa render MP4.
6. AI CEO chốt phương án nội bộ, báo cáo lại cho chủ; chủ duyệt trước khi xuất bản.

Các phòng ban mới sử dụng các agent Research, Creative và Compliance đã có sẵn; bản này chưa cần tạo tài khoản AI mới.

## Cập nhật Windows

Đóng chương trình rồi mở PowerShell:

~~~powershell
cd D:\APhanMem\teabotAI
git pull origin main
cd studio
.\setup_windows.bat
.\start_windows.bat
~~~

Chạy setup một lần để cài pypdf; các lần sau chỉ cần start.

Mở http://127.0.0.1:8765 và nhấn Ctrl+Shift+R. Vào **Giao nhiệm vụ cho CEO** → **Giao nhiệm vụ CEO**; chọn loại nhiệm vụ **Nghiên cứu TikTok → kịch bản → Phòng Video AI**.

## Trường dữ liệu

- Tên sản phẩm (bắt buộc).
- Thành phần sản phẩm (bắt buộc, theo nhãn).
- Ảnh sản phẩm 3D dạng PNG/JPG/WebP tối đa 8MB.
- Giấy tờ công bố dạng PDF/PNG/JPG/WebP tối đa 12MB.
- Tối đa 8 URL video TikTok HTTPS, mỗi dòng một URL.
- Ghi chú hoặc transcript video từ người thực sự đã xem/nghe.
- Mô tả mục tiêu, giọng điệu, tỷ lệ video trong yêu cầu CEO.

Tệp được lưu trên ổ cứng máy chạy phần mềm dưới studio/data/product_missions; thông tin nhiệm vụ, trạng thái và file metadata trong studio/data/studio.sqlite3. Tài liệu PDF có chữ có thể được trích văn bản để AI tham khảo; ảnh/scan chưa được đọc bằng thị giác máy trong bản này. Tải giấy tờ không có nghĩa pháp lý đã xác thực giấy công bố. Mọi kết luận về giấy phép, công dụng và chứng nhận cần kiểm tra độc lập.

## Hạn chế và an toàn

Đối với link TikTok chủ cung cấp, phần mềm có thể thử dịch vụ oEmbed công khai của TikTok để lấy tiêu đề/tác giả (có thể bị từ chối hoặc ngừng hỗ trợ); đây chỉ là metadata, KHÔNG xem/đọc được khung hình, âm thanh, bình luận hoặc lượt view thực tế. Phần mềm không có quyền Research API hoặc module phân tích trực tiếp video. Nghiên cứu nội dung vẫn cần ghi chú/transcript do người thực sự xem cung cấp. Không bịa nội dung/doanh số hay sao chép video đối thủ.

Nếu sử dụng Gemini, Groq, Claude hoặc OpenAI, nội dung brief, ghi chú, URL, thành phần và văn bản trích từ PDF được gửi tới nhà cung cấp AI để xử lý. Tệp ảnh và PDF gốc giữ cục bộ, chưa trực tiếp gửi cho mô hình đa phương thức. Không đưa dữ liệu khách hàng nhạy cảm, OTP, cookies hoặc mật khẩu vào hồ sơ.

Bản này chỉ tạo bản thảo và storyboard cho Phòng Video AI, không trực tiếp sinh MP4 và không đăng lên TikTok. Phải kết nối riêng công cụ render video AI và cần phê duyệt của người điều hành trước khi phát hành.

Kết quả ở trang **Phòng nghiên cứu TikTok & Video AI**, đồng thời CEO và các agent để lại log trong **Phòng họp AI**. Nếu kiểm duyệt báo needs_review, kịch bản không được chuyển phòng sản xuất. Nếu lỗi blocked có thể Thử lại nhiệm vụ CEO.
