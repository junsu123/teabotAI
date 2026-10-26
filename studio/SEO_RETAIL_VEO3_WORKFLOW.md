# TEA AI Mars Studio: bộ nội dung SEO, giá bán lẻ và Google Veo 3

Đây là quy trình mặc định cho từng sản phẩm mới do AI CEO tiếp nhận và điều phối.

## Năm đầu ra chính

1. Tiêu đề SEO: 3–5 phương án dành cho Shopee và TikTok Shop, dựa trên tên sản phẩm và thành phần thực sự được cung cấp, không bịa công dụng hoặc chứng nhận.
2. Mô tả SEO: trình bày dễ đọc, từ khóa liên quan, thành phần và hướng dẫn sử dụng chỉ khi có bằng chứng; cần chủ kiểm duyệt trước khi đăng.
3. Nghiên cứu giá bán lẻ: dựa trên link, mức giá và ngày kiểm tra do chủ nhập. Hiện tại **chưa có API nghiên cứu giá Shopee/TikTok trực tiếp**, nên khi thiếu nguồn phải ghi CHƯA XÁC MINH GIÁ BÁN LẺ và đưa phương pháp khảo sát, không tự bịa số.
4. Kịch bản video bán hàng dài 40 giây: 5 cảnh x 8 giây, có mở đầu thu hút, lời thoại tiếng Việt, hình ảnh và CTA. Hai hướng triển khai sáng tạo.
5. Prompt Google Veo 3: 5 prompt độc lập, mỗi prompt 8 giây để tạo 5 clip và ghép thành video 40 giây. Prompt nêu cảnh quay, camera, ánh sáng, thoại, âm thanh, 9:16 và nhân vật/bối cảnh nhất quán.

## Lưu mẫu gốc Veo 3

Vào Phòng TikTok & Video AI, tìm mục Prompt gốc Google Veo 3, dán mẫu do chủ cung cấp, nhấn Lưu prompt mẫu.

Mẫu nằm trong SQLite cục bộ, bảng content_templates. Khi giao nhiệm vụ mới, hệ thống giữ một bản sao mẫu trong hồ sơ của sản phẩm. Việc sửa mẫu sau này chỉ áp dụng với nhiệm vụ mới, không sửa nhiệm vụ cũ. Hỗ trợ hai chỗ giữ chỗ văn bản: {product_name} và {ingredients}.

Agent biên kịch tham khảo cấu trúc/phong cách của prompt mẫu để tạo kịch bản mới; Phòng Video AI tạo 5 prompt đã biến tấu, không sao chép nguyên văn mẫu hoặc video người khác. Nếu chủ chưa đưa mẫu, hệ thống dùng phong cách trung tính và không tự nhận đã dùng mẫu riêng.

## Quy trình AI CEO

Nghiên cứu TikTok (metadata công khai và ghi chú được cung cấp) → Phòng phân tích giá → Phòng SEO → Phòng biên kịch video 40 giây → Phòng kiểm duyệt → Phòng video AI tạo 5 prompt x 8 giây → CEO báo cáo.

Compliance chưa duyệt thì SEO và kịch bản chỉ là bản nháp, không bàn giao prompt tạo video. Nếu không tạo được đủ 5 prompt JSON hợp lệ x 8 giây, tác vụ sẽ báo lỗi để thử lại, không bịa ra các cảnh còn thiếu.

## Dữ liệu giao việc

Giao nhiệm vụ cho CEO, chọn Bộ nội dung sản phẩm: SEO + Giá bán lẻ + Video 40s + 5 prompt Veo 3. Điền tên và thành phần; tùy chọn tải ảnh 3D sản phẩm và giấy công bố, link TikTok và ghi chú, dữ liệu giá đối thủ có nguồn/ngày kiểm tra. Mọi công dụng phải có hồ sơ căn cứ; chỉ thêm chữ hỗ trợ không khiến tuyên bố tự động hợp lệ.

Kết quả nằm tại Phòng TikTok & Video AI, có nút sao chép từng mục và từng prompt cảnh 1–5.

## Giới hạn

Ứng dụng chưa tự đọc đầy đủ âm thanh/hình ảnh/bình luận TikTok; chỉ có thể thử lấy metadata oEmbed, còn nội dung video cần transcript/ghi chú thật. Ứng dụng chưa có công cụ khảo sát giá online được cấp phép và chưa render MP4 bằng Veo 3. Các giá thị trường cần xác minh bên ngoài. Ảnh bao bì gốc phải giữ nguyên nhãn, chữ, màu và tên. AI Compliance chỉ hỗ trợ sơ bộ, cần chủ duyệt trước khi đăng. Nội dung văn bản và PDF trích được có thể được gửi đến Gemini/Groq theo cấu hình API.

## Cập nhật trên Windows

~~~powershell
cd D:\APhanMem\teabotAI
git pull origin main
cd studio
.\start_windows.bat
~~~

Mở http://127.0.0.1:8765, nhấn Ctrl + Shift + R. Nếu cần cài thư viện còn thiếu thì chạy setup_windows.bat trước khi khởi động. CI thử mã và mock AI; chưa thể đảm bảo đã chạy trên máy Windows của chủ.
