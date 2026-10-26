# CEO-only Operating Policy / Quy tắc CEO là đầu mối duy nhất

## Quy tắc bất biến do chủ doanh nghiệp yêu cầu

1. Chủ doanh nghiệp **chỉ giao nhiệm vụ và nhận báo cáo qua AI CEO**.
2. AI Research, Strategy, Creative, Analyst và Compliance là **nhân viên nội bộ**. Không có nút, biểu mẫu hay API dành cho chủ doanh nghiệp để giao trực tiếp cho các agent này.
3. AI CEO tiếp nhận yêu cầu, phân tích mục tiêu, chia nhỏ nhiệm vụ, chọn agent phù hợp, theo dõi tiến độ, tổng hợp kết quả và trình báo cáo về chủ doanh nghiệp.
4. Những hành động có tác động bên ngoài (đăng bài, thay đổi giá, chi tiền quảng cáo, cập nhật dữ liệu gian hàng) cần cơ chế phê duyệt đúng quyền hạn, đặc biệt trong giai đoạn thử nghiệm.
5. Các thao tác **cấu hình hệ thống** (thêm proxy, tạo Chrome profile, đăng nhập thủ công, dạy thao tác DOM) không phải là giao nhiệm vụ cho nhân viên. Chủ doanh nghiệp vẫn được chỉnh cấu hình qua giao diện.

## Luồng dự kiến

```text
Owner / Telegram / Mars Studio
          |
          v
    CEO INBOX (missions.agent_id = "ceo")
          |
          v
 AI CEO: lập kế hoạch + duyệt phân công
          |
          +--> Research
          +--> Strategy
          +--> Creative
          +--> Analyst
          +--> Compliance
          |
          v
  AI CEO tổng hợp, yêu cầu duyệt và báo cáo
          |
          v
         Owner
```

## Trạng thái hiện tại

- Giao diện Mars Studio chỉ cho gửi nhiệm vụ tới AI CEO.
- Backend `POST /api/missions` từ chối `agent_id` khác `ceo`.
- `POST /api/jobs` chuyển yêu cầu đăng sản phẩm thành nhiệm vụ trong CEO inbox; **chưa tạo job đăng hàng thực thi**.
- Chưa có AI CEO tự động gọi mô hình và điều phối agent. Các nhiệm vụ đang được **lưu vào hàng đợi** chờ phiên bản điều phối thực sự.
- Các nhiệm vụ cũ đã từng ghi trực tiếp tới một phòng ban (nếu có) được giữ nguyên lịch sử; quy tắc mới áp dụng cho tất cả nhiệm vụ tạo mới.

## Kế hoạch phát triển AI CEO

1. `CEOPlanner` đọc mission, sản phẩm, trạng thái gian hàng và bộ nhớ.
2. Tạo `delegated_tasks` có liên kết `parent_mission_id`, `assigned_by="ceo"` và `agent_id` của nhân viên.
3. Thực thi các công việc an toàn và tạo bản nháp; chờ phê duyệt cho các thao tác quan trọng.
4. Gửi tình trạng và báo cáo **chỉ qua AI CEO**, mọi agent con không nhắn trực tiếp cho chủ doanh nghiệp.
5. Kiểm tra không có API hay UI khác bypass CEO inbox.

**Không được mô tả hệ thống là đã tự điều phối khi các bước trên chưa được hiện thực.**
