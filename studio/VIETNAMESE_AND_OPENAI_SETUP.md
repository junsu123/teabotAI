# Cấu hình ngôn ngữ tiếng Việt & lựa chọn OpenAI cho AI CEO

## Nguyên tắc bất biến

- **Toàn bộ nội dung trao đổi, tranh luận, đề xuất, báo cáo và quyết định của agent đều phải bằng tiếng Việt**, có dấu. Tên model, mã SKU, URL và khóa JSON được giữ nguyên.
- **Chủ doanh nghiệp chỉ làm việc với AI CEO**. Agent khác chỉ trao đổi nội bộ và không có quyền chốt phương án.
- Phần mềm **chạy Ollama cục bộ theo mặc định**, không tự động bật API OpenAI hay phát sinh phí.
- Tất cả gọi OpenAI qua **Responses API**, model được chọn theo từng vai trò, không chuyển cookie/proxy credential/tokens/mật khẩu của sàn.
- Tuyệt đối không đưa API key vào repo GitHub, `config.json`, `studio/data` hay nội dung nhiệm vụ.

## Mô hình khuyến nghị

| Agent | Mặc định | Khi bật OpenAI |
|---|---|---|
| CEO | Ollama | `gpt-6.1-sol`, ưu tiên số 1 |
| Strategy | Ollama | `gpt-6.1-sol` với nhiệm vụ quan trọng |
| Compliance | Ollama | `gpt-6.1-sol` để đối chiếu rủi ro |
| Research | Ollama | `gpt-6-luna` để xử lý tài liệu có nguồn |
| Creative | Ollama | `gpt-6-luna` để viết số lượng lớn |
| Analyst | Python tính KPI + Ollama diễn giải | `gpt-6-luna` diễn giải |

Không phụ thuộc model: Research phải có **nguồn dữ liệu công khai hợp lệ**, Analyst phải được cấp báo cáo số liệu thật, Compliance phải tham chiếu hồ sơ sản phẩm và pháp luật. Mô hình không thể tự biết dữ liệu Shopee/TikTok Shop nếu không được kết nối/cấp quyền.

**Quan trọng:** ChatGPT Plus/Pro không mặc nhiên bao gồm OpenAI API. API có cơ chế thanh toán độc lập. Người dùng phải tạo API key và tự kích hoạt.

## Bắt đầu: chỉ dùng OpenAI cho AI CEO

1. Tạo API key trong tài khoản API tại https://platform.openai.com/api-keys, cài đặt thanh toán và hạn mức ở trang API.
2. Đóng cửa sổ TEA AI đang chạy.
3. Mở PowerShell mới tại `D:\APhanMem\teabotAI\studio`.
4. Dùng cách nhập key **ẩn ký tự**, chỉ lưu trong biến môi trường của cửa sổ PowerShell đó:

```powershell
$env:TEA_OPENAI_AGENTS="ceo"
$env:TEA_OPENAI_MONTHLY_LIMIT_USD="12"
$secure=Read-Host "Nhap OpenAI API key" -AsSecureString
$env:OPENAI_API_KEY=[System.Net.NetworkCredential]::new("",$secure).Password
.\start_windows.bat
```

5. Truy cập `http://127.0.0.1:8765` → **Giao nhiệm vụ cho CEO**. Phần mềm hiển thị tuyến model CEO = OpenAI `gpt-6.1-sol`; các agent khác = Ollama.

Bật thêm Strategy và Compliance khi đã thử nghiệm thực tế:

```powershell
$env:TEA_OPENAI_AGENTS="ceo,strategy,compliance"
```

Khi thay đổi biến môi trường, **khởi động lại phần mềm** trong đúng cửa sổ PowerShell đó.

Tắt toàn bộ OpenAI, trở về Ollama:

```powershell
$env:TEA_OPENAI_AGENTS="none"
.\start_windows.bat
```

Nếu OpenAI bị lỗi, chương trình **không tự âm thầm chuyển sang Ollama**; nhiệm vụ chuyển `blocked` để bạn kiểm tra, tránh báo cáo kết quả dưới sai nhà cung cấp.

## Chi phí

Giá API chuẩn tại thời điểm cập nhật (USD / 1 triệu token):

- `gpt-6.1-sol`: $2 đầu vào; $10 đầu ra.
- `gpt-6-luna`: $0,10 đầu vào; $0,50 đầu ra.

Phí có thể thay đổi; xác minh lại tại https://developers.openai.com/api/docs/pricing trước khi bật.

`TEA_OPENAI_MONTHLY_LIMIT_USD=12` là **chốt chặn ước tính tại phần mềm**, theo số token API báo về mỗi lời gọi và dự trù trước lời gọi kế tiếp. Đây KHÔNG phải hạn mức cứng do OpenAI quản lý; phí tìm kiếm/tool/các ứng dụng khác hoặc lời gọi bị gián đoạn có thể không nằm trong tổng ước tính cục bộ. Cần cài thêm giới hạn/ngưỡng cảnh báo tại tài khoản API chính thức.

Dữ liệu sử dụng OpenAI cục bộ (chỉ số token và chi phí ước tính, không có key/prompt/cookie): `studio/data/openai_usage.sqlite3`.

## Bảo mật dữ liệu

Khi bật OpenAI cho một agent, **nội dung prompt và hồ sơ sản phẩm xuất hiện trong nhiệm vụ của agent đó sẽ được gửi đến OpenAI để xử lý**. Không điền thông tin xác thực sàn, dữ liệu cá nhân khách hàng hoặc nội dung bí mật không muốn gửi đi.

Tất cả gọi API hiện dùng `store:false`, không bật công cụ web search mặc định, không phát sinh hành động đăng sản phẩm. Dữ liệu vẫn được lưu cục bộ vào log nội bộ do bạn quản lý.

## Kiểm thử

```powershell
cd D:\APhanMem\teabotAI
py -3 -m unittest discover -s studio/tests -v
```

Kiểm thử tự động dùng HTTP giả lập để chắc chắn rằng không tự gọi API khi chưa bật, kiểm tra tiếng Việt và kiểm soát ngân sách cục bộ. **Chưa kiểm thử OpenAI API thật bằng key của bạn**.

Không có phương pháp prompt nào bảo đảm hoàn toàn không xuất hiện tiếng Anh hoặc không có lỗi thực tế. Để đánh giá chính xác, hãy kiểm tra vài nhiệm vụ thật trong giao diện Phòng họp AI, đối chiếu bằng chứng và dữ liệu.
