# Phòng họp AI – Log trao đổi & phản biện, CEO chốt quyết định

## Quy tắc điều hành

**Bạn chỉ giao việc và nhận báo cáo qua AI CEO.** Mọi phòng ban là agent nội bộ. Giao diện Phòng họp AI là **chế độ xem read-only** để kiểm tra tiến trình, không có chức năng gửi lệnh trực tiếp cho nhân viên.

## Luồng xử lý

1. CEO nhận nhiệm vụ, lập kế hoạch và lựa chọn tối đa **2 agent** trong Research / Strategy / Creative / Analyst / Compliance.
2. Mỗi agent cung cấp ý kiến ban đầu; log có người gửi, người nhận, loại thông điệp và thời gian.
3. Agent A đặt câu hỏi về một vấn đề hoặc điểm chưa thống nhất cho agent B.
4. Agent B trả lời và đưa phản biện / câu hỏi ngược lại.
5. Agent A điều chỉnh hoặc bảo vệ quan điểm, ghi rõ điều đã thống nhất/chưa thống nhất.
6. CEO đọc bản nháp và log tranh luận, cân nhắc rủi ro rồi **quyết định phương án cuối**.
7. CEO gửi báo cáo cho chủ doanh nghiệp. Các quyết định có tác động bên ngoài (đăng hàng, chỉnh giá, chạy quảng cáo) vẫn cần người có thẩm quyền phê duyệt.

Để giới hạn tài nguyên máy chạy mô hình cục bộ, mặc định chỉ **1 vòng tranh luận**, tối đa 2 vòng. Không chạy thảo luận vô hạn hoặc tự tạo nhiều agent mới.

## Cách theo dõi trên giao diện

Mở Mars Studio → **Phòng họp AI – Log thảo luận** → chọn nhiệm vụ CEO.
Log được tự cập nhật khoảng 6,5 giây khi bạn mở trang đó. Từ màn hình **Giao nhiệm vụ cho CEO**, bấm **Xem log tranh luận** ở nhiệm vụ muốn xem.

Các loại log:
- `assignment`: CEO phân công, gửi yêu cầu.
- `proposal`: nhân viên đề xuất ban đầu.
- `question`: câu hỏi giữa nhân viên.
- `objection`: trả lời/phản biện.
- `revision`: điều chỉnh phương án.
- `decision`: chỉ CEO có quyền ghi nhận quyết định cuối.
- `error`: báo lỗi xử lý.
- `retry`: đánh dấu nhiệm vụ chạy lại, giữ lịch sử cũ.

Nhật ký lưu trong bảng `agent_messages` của cơ sở dữ liệu `studio/data/studio.sqlite3`. Không xóa bảng dữ liệu hoặc profile khi cập nhật code.
Giao diện đọc từ `GET /api/agent-forum?mission_id=123` trên `127.0.0.1:8765`, giới hạn nội dung và chỉ truy cập cục bộ.

## Chọn mức tranh luận phù hợp cấu hình máy

Mặc định: 1 vòng; cần tổng cộng tối đa 7 lần gọi mô hình cho tác vụ 2 agent (lập kế hoạch CEO, hai đề xuất, ba lượt phản biện, một quyết định CEO). Trên máy yếu hoặc chạy CPU, công việc có thể hoàn tất chậm hơn chế độ cũ. Để tạm tắt tranh luận:

```powershell
$env:TEA_DEBATE_ROUNDS="0"
cd D:\APhanMem\teabotAI\studio
.\start_windows.bat
```

Chọn 1 vòng (mặc định):

```powershell
$env:TEA_DEBATE_ROUNDS="1"
.\start_windows.bat
```

Tối đa 2 vòng: `$env:TEA_DEBATE_ROUNDS="2"`. Không khuyến nghị trên PC yếu.

**Lưu ý:** Đây là các thông điệp giải quyết công việc do agent sinh ra, không phải quá trình suy luận nội tâm hoặc bằng chứng rằng các agent đã truy cập mạng, đăng bài hoặc hoàn thành tác vụ ngoài trình duyệt. Các phát biểu chưa kiểm chứng phải được đánh dấu. Không ghi cookie, mật khẩu hoặc token vào lời giao việc.

## Kiểm thử

```powershell
cd D:\APhanMem\teabotAI
py -3 -m unittest discover -s studio/tests -v
```

Nếu Ollama chưa cài/chưa chạy, nhiệm vụ sẽ vào trạng thái lỗi hoặc chờ; bạn vẫn xem được log trước khi lỗi và nút thử lại. Các bài kiểm thử GitHub Actions mô phỏng lời thoại, chưa xác minh thực tế chất lượng tranh luận từ model trên máy bạn.
