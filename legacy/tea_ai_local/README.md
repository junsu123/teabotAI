# TEA AI LOCAL – Công ty marketing AI chạy trên máy cá nhân

Một **bản khung Python chạy được (MVP)** gồm 6 vai trò: CEO, Research, Analyst, Strategy, Creative, Compliance. Mô hình AI hoạt động **trên máy** bằng Ollama; dữ liệu lưu SQLite; không cần VPS hay API trả phí để bắt đầu.

> Đây là phiên bản dòng lệnh, **chưa có giao diện đồ họa**. AI không tự đăng bài, đặt quảng cáo, mua hàng, truy cập Shopee/TikTok Shop hay chỉnh sửa sản phẩm. Các chức năng đó cần tích hợp API chính thức và bước duyệt riêng. Chưa được chạy thử với Ollama thật trong môi trường tạo tệp; các thành phần không cần AI đã có bài kiểm thử tự động.

## Yêu cầu

- **Python 3.11+**: <https://www.python.org/downloads/>
- **Ollama**: <https://ollama.com/download>. Trên Windows, Ollama thường tự phục vụ API tại `127.0.0.1:11434` khi ứng dụng đang chạy.
- RAM **16 GB trở lên khuyến nghị** cho `qwen3:4b` và tác vụ khác. Máy RAM 8 GB có thể cân nhắc `qwen3:1.7b`, chấp nhận chất lượng thấp hơn và chạy chậm. GPU là tùy chọn; CPU vẫn chạy nhưng có thể chậm. Dung lượng model `qwen3:4b` khoảng 2,5 GB và còn cần chỗ chứa Ollama/hệ thống.
- Máy cần có Internet **chỉ khi** lấy nguồn web hoặc dùng API tìm kiếm. AI và cơ sở dữ liệu có thể chạy cục bộ sau khi tải model.

## Cài trên Windows (PowerShell)

1. Giải nén thư mục `tea_ai_local`, mở Terminal/PowerShell tại thư mục.
2. Cài Python, Ollama như trên. Mở Ollama.
3. Tải model bằng lệnh:

```powershell
ollama pull qwen3:4b
```

4. Khởi tạo dữ liệu và kiểm tra:

```powershell
py -3 main.py init
py -3 main.py doctor
```

5. Mở file `config.json` vừa tạo và thay `product`, `product_facts` thành thông tin **đã xác minh** về sản phẩm trà của bạn. Không ghi mật khẩu hoặc API key vào file này.
6. Giao việc:

```powershell
py -3 main.py run "Viết 3 kịch bản video 5 cảnh cho combo trà túi lọc, tránh quảng cáo công dụng điều trị"
```

7. Xem bản nháp Markdown trong `outputs/`.

Trên Linux/macOS: đổi `py -3` thành `python3`.

**Nếu không chạy được Ollama**: mở ứng dụng Ollama, kiểm tra `ollama list`, `ollama serve` nếu chưa có tiến trình lắng nghe; tiếp đó chạy `py -3 main.py doctor`.

## Tạo bộ nhớ nghiên cứu từ các nguồn web

Tự thêm các nguồn HTTPS công khai mà bạn có quyền truy cập và xử lý. Hỗ trợ HTML thông thường hoặc RSS/Atom:

```powershell
py -3 main.py add-source "https://ten-website-hop-le.example/duong-dan-bai-viet"
py -3 main.py learn
py -3 main.py review
py -3 main.py approve 1
```

- `learn`: lấy nội dung, yêu cầu agent Research rút ý, ghi URL và thời điểm, lưu thành **chưa kiểm chứng**.
- `review`: liệt kê những ghi chú cần bạn kiểm tra.
- `approve <id>`: đánh dấu đã được con người xem xét; không đảm bảo nguồn chính xác tuyệt đối.
- `learn` chỉ học nguồn có sẵn. Trang dùng JavaScript mạnh, trang yêu cầu đăng nhập, trang có chống bot, file PDF, video TikTok/Shopee **chưa được hỗ trợ**.
- Hãy kiểm tra điều khoản, robots.txt, bản quyền, giới hạn truy cập của nguồn trước khi thêm. Không thêm nguồn riêng tư hoặc thu thập dữ liệu cá nhân. Chương trình hiện không tự diễn giải toàn bộ chính sách truy cập của từng website.

### Tự chạy nhiều lần mỗi ngày

```powershell
py -3 main.py daemon --minutes 240
```

Chu kỳ trên chạy 4 giờ/lần **khi cửa sổ lệnh còn mở và máy chưa ngủ**. Muốn chạy khi khởi động Windows, tạo tác vụ bằng **Task Scheduler** (trỏ tới `learn_windows.bat`) và chọn cài đặt nguồn điện, quyền phù hợp. Tắt nguồn/ngủ thì agent không chạy. Chu kỳ tối thiểu là 30 phút; không nên dùng tần suất cao để spam nguồn.

### Tìm ý tưởng khắp web (tùy chọn, có thể phát sinh phí)

Nếu bạn có Brave Search API Key (không bắt buộc), nhập trong PowerShell **chỉ cho phiên hiện tại**:

```powershell
$env:BRAVE_API_KEY="API_KEY_CUA_BAN"
py -3 main.py discover "trà túi lọc cách bán hàng thương mại điện tử" 
```

Thêm `--add` nếu muốn đưa kết quả vào danh sách nguồn học định kỳ (hãy rà soát quyền truy cập của các nguồn đó). Với Brave key và `"auto_discover": true` trong config, chế độ daemon có thể chủ động tìm nguồn từ `research_queries` 1 lần/ngày, tối đa 2 truy vấn/ngày ở phiên bản này.

**Quan trọng:** Không bật `auto_discover` trước khi hiểu chi phí API, quyền truy cập và cách kiểm tra nguồn. Brave là dịch vụ ngoài, nên từ khóa tìm kiếm được gửi tới họ. Không bật `--add` vô điều kiện đối với website chưa có quyền thu thập.

## Học từ dữ liệu bán hàng thực tế

Có tệp mẫu `examples/sales_example.csv`. Định dạng cột cố định:

`campaign,variant,impressions,clicks,orders,revenue,ad_spend,cogs,fees,refunds`

Các giá trị tiền tệ cùng đơn vị VNĐ; `cogs` là **tổng giá vốn của các đơn** trong dòng dữ liệu, không phải giá vốn mỗi hộp. `refunds` là khoản hoàn/điều chỉnh chi phí cần trừ. Chuẩn hóa và không nhập giá trị chồng lặp.

```powershell
py -3 main.py import-sales examples/sales_example.csv
py -3 main.py status
py -3 main.py evaluate
py -3 main.py run "Phân tích hai kịch bản video và đề xuất thử nghiệm tiếp theo"
```

Phần mềm tính CTR, CVR và lợi nhuận đóng góp bằng công thức xác định, sau đó Analyst sử dụng làm đầu vào. Lệnh `evaluate` gọi Analyst rút bài học **chưa kiểm chứng** mỗi khi có dữ liệu nhập mới; `daemon` cũng gọi lệnh này tự động. Ngăn nhập trùng tệp y hệt bằng SHA256. **Cảnh báo:** dữ liệu chưa phải thí nghiệm phân nhóm ngẫu nhiên, không chứng minh nhân quả; số nhỏ cần kiểm chứng lại.

## Học từ góp ý trực tiếp của chủ doanh nghiệp

Sau khi `run`, hệ thống lưu báo cáo kèm mã `run_id` (xem bằng `status`). Đánh giá chất lượng và ghi lại chỉnh sửa cần thiết:

```powershell
py -3 main.py status
py -3 main.py feedback 1 4 "Slogan phải ngắn hơn; luôn chừa khoảng trống trên cùng cho ảnh sản phẩm"
```

Góp ý do chính bạn đưa ra được lưu thành bộ nhớ nội bộ `approved` để các agent sử dụng trong nhiệm vụ tiếp theo. Việc lưu góp ý giúp agent điều chỉnh đầu ra, **không** làm mô hình nền thay đổi trọng số.

## Vai trò agent và mức độ tự động

| Agent | Hoạt động |
|---|---|
| Research | Đọc bộ nhớ và nguồn công khai; trích dẫn nguồn; nêu giả thuyết |
| Analyst | Đọc KPI thực, đưa ra hạn chế và đề xuất đo tiếp |
| Strategy | Tạo kế hoạch marketing và thiết kế thử nghiệm |
| Creative | Sinh nội dung marketing nháp, chưa render ảnh/video |
| Compliance | Rà soát tuyên bố nhạy cảm; không thay thế pháp lý |
| CEO | Hợp nhất kết quả thành báo cáo để người dùng duyệt |

Cả 6 agent dùng **chung mô hình Ollama**, chỉ khác vai trò hệ thống và dữ liệu được đưa vào. Các tác vụ chạy tuần tự để tiết kiệm RAM. **Không tự cập nhật trọng số model**; chỉ phát triển năng lực qua bộ nhớ, nghiên cứu, dữ liệu và con người xác nhận.

## Cấu trúc dự án

```
tea_ai_local/
  main.py                 # CLI, SQLite, Ollama, web research, 6 agent
  config.json             # tạo khi chạy init; điền hồ sơ sản phẩm
  data/                   # bộ nhớ SQLite; nên sao lưu thường xuyên
  outputs/                # báo cáo nội dung CHỜ DUYỆT
  examples/sales_example.csv
  tests/test_main.py
  start_windows.bat
  learn_windows.bat
  requirements.txt        # không cần thư viện Python ngoài
```

## Kiểm thử, bảo mật và giới hạn

Chạy kiểm thử offline:

```powershell
py -3 -m unittest discover -s tests -v
```

Các biện pháp sẵn có: chỉ chấp nhận HTTPS công khai cho nguồn website, không follow HTTP redirect, giới hạn kích thước tài liệu, log công việc, không có công cụ chạy lệnh tùy ý cho AI, không có quyền đăng bài/chi tiền, không lưu API key trên SQLite, có trạng thái dữ liệu chờ duyệt.

Cần bổ sung ở giai đoạn production: kiểm tra robots.txt tự động, chống DNS rebind ở lớp mạng, mã hóa ổ đĩa và sao lưu, monitoring, chống prompt injection nâng cao, phân quyền đa người dùng, xử lý retry/backoff theo mã lỗi, import xuất báo cáo API chính thức, bài đánh giá chất lượng LLM, giao diện người dùng, hàng đợi công việc và cơ chế khôi phục sau mất điện. Không đặt dịch vụ Ollama hoặc SQLite lên Internet công cộng.

### Nguồn tài liệu kỹ thuật

- Ollama API: <https://docs.ollama.com/api>
- Qwen3 4B trên Ollama: <https://ollama.com/library/qwen3:4b>
- SQLite FTS5: <https://www.sqlite.org/fts5.html>
- Brave Web Search API: <https://api-dashboard.search.brave.com/app/documentation/web-search>

### Lộ trình phát triển tiếp

1. Giao diện Streamlit hoặc FastAPI localhost, xem báo cáo và duyệt bằng nút.
2. Bổ sung web search được cấp phép, ghi chú nguồn đáng tin và lịch trình có checkpoint.
3. Chuyển từ SQLite FTS5 sang tìm kiếm lai embeddings + FTS; bổ sung phân phiên bản kiến thức.
4. Tích hợp nguồn bán hàng chính thức, đối chiếu số liệu, tránh trùng nhập.
5. Thiết kế thước đo thử nghiệm định lượng và học từ phản hồi duyệt của con người.
6. Chỉ sau khi thử nghiệm đầy đủ mới trao quyền có giới hạn để xuất bản nội dung thông qua API được cấp phép.

---

# Phần mở rộng: AI hỗ trợ đăng hàng bằng TRÌNH DUYỆT (không API sàn)

Đã bổ sung `browser_listing.py` và `telegram_listing_bot.py`. Chúng chạy độc lập với các lệnh `main.py` cũ và dùng chung thư mục dự án.

**Cách hoạt động hiện tại:** nhận ảnh từ Telegram → xác định SKU trong `products.json` → tạo phiếu HTML → bạn duyệt → Python mở Seller Center bằng Playwright trong cửa sổ trình duyệt **hiển thị** → bạn thực hiện thao tác cuối và xác nhận trạng thái. Mẫu bước thao tác Playwright có thể ghi và chuyển thành cấu hình để tự điền trong trường hợp bạn được phép tự động hóa giao diện. **Chưa có selector thật của Shopee/TikTok vì chưa được ghi thao tác từ tài khoản của bạn. Không tự đăng sản phẩm lên sàn ngay sau khi giải nén.**

## 1. Cài đặt trên Windows

Mở PowerShell trong thư mục `tea_ai_local`, chạy:

```powershell
py -3 -m pip install -r browser_requirements.txt
py -3 -m playwright install chromium
py -3 browser_listing.py init
```

Chạy `py -3 browser_listing.py init` để tạo:

- `products.json`: danh sách SKU chính xác, tên, mô tả, giá, tồn kho. **Thay sản phẩm DEMO bằng dữ liệu thật**; không điền thông tin sức khỏe chưa kiểm chứng.
- `browser_steps.json`: URL Seller Center, các bước thao tác. Mặc định `permission_to_automate = false`, `steps = []`.
- `listing_data/listings.sqlite3`: nhiệm vụ, ảnh, trạng thái, nhật ký.

## 2. Tạo Telegram Bot

1. Mở Telegram và tìm **@BotFather** (tài khoản chính thức), dùng `/newbot` tạo bot, giữ **TOKEN** bí mật.
2. Lấy **Telegram numeric user ID** của chính bạn bằng một công cụ bạn tin tưởng hoặc đọc thuộc tính `update.effective_user.id` trong bot do bạn quản lý. Không cấp quyền bằng username; username có thể đổi.
3. Trong PowerShell **chỉ phiên làm việc hiện tại**, đặt biến môi trường:

```powershell
$env:TEA_TELEGRAM_TOKEN="TOKEN_CUA_BAN"
$env:TEA_TELEGRAM_ALLOWED_IDS="123456789"
py -3 telegram_listing_bot.py
```

Đổi `123456789` thành user ID thực tế. Không lưu token trong file `.py`, không chia sẻ token. Bot chỉ chấp nhận ID nằm trong whitelist.

Trong Telegram gửi một ảnh và chú thích:

```text
SKU=TRA-001 SHOP=shopee MODE=new
```

Hoặc:

```text
SKU=TRA-001 SHOP=tiktok MODE=update
```

Ảnh thêm vào một nhiệm vụ:

```text
ADD=1
```

Gửi `/status 1` để xem trạng thái; `/approve 1` để duyệt; `/reject 1` để từ chối. Một nhiệm vụ chỉ cho một SKU, một shop, một kiểu tạo mới hoặc cập nhật. Muốn đăng hai sàn hãy tạo hai nhiệm vụ riêng.

## 3. Duyệt rồi mở trình duyệt bằng Python

Trong PowerShell thứ hai, chạy:

```powershell
py -3 browser_listing.py watch --seconds 15
```

Worker đọc SQLite, tự mở cửa sổ Chromium **khi nhiệm vụ được duyệt**. Hỗ trợ mặc định không tự gõ thông tin lên trang sàn để tránh vi phạm điều khoản; phiếu HTML xuất ở `listing_data/previews/job_1.html` có nút sao chép từng trường, ảnh lưu tại `listing_data/images/1`.

Hoặc thực hiện từng bước:

```powershell
py -3 browser_listing.py create TRA-001 shopee new
py -3 browser_listing.py add 1 "C:\duong-dan\anh-san-pham.png"
py -3 browser_listing.py preview 1
py -3 browser_listing.py approve 1
py -3 browser_listing.py work 1
```

Khi đăng xong trên Seller Center, tại terminal ghi:

```powershell
py -3 browser_listing.py posted 1 --url "https://duong-dan-san-pham-thuc-te"
```

**Quan trọng:** Chỉ `posted` khi bạn đã kiểm tra đã đăng hoặc đã có sản phẩm theo trạng thái thực trên sàn. Lệnh không tự chứng minh đăng thành công; cũng không tự lấy URL sản phẩm từ sàn.

## 4. Chế độ học thao tác với Playwright Codegen

Chỉ chạy trên nền tảng/trường hợp mà bạn đã xác minh mình có quyền tự động hóa. Lệnh:

```powershell
py -3 browser_listing.py record shopee new
py -3 browser_listing.py record tiktok update
```

Playwright ghi thao tác mẫu ra `listing_data/recordings/<shop>_<mode>.py`, dùng **hồ sơ trình duyệt riêng**. Mã ghi chỉ để tham khảo; **không chạy trực tiếp file được ghi** (thường chứa dữ liệu và selector gắn với mẫu cụ thể). Hãy chuyển những bước hợp lệ thành `browser_steps.json` ở dạng JSON, ví dụ:

```json
{
  "action": "fill",
  "locator": {"by": "label", "value": "Tên sản phẩm"},
  "field": "title"
}
```

Các thao tác hỗ trợ `fill`, `upload`, `select`, `click` và `pause`; các trường dữ liệu hợp lệ là `title`, `description`, `price`, `stock`, `sku`, `images`. **Đây chỉ là ví dụ locator**, không bảo đảm nhãn này đang hiện trên một sàn cụ thể. `click` không được sử dụng để thực hiện hành động đăng cuối cùng. Nếu đã được phép và đã cấu hình bước hợp lệ, có thể thử:

```powershell
py -3 browser_listing.py work 1 --auto
```

`--auto` CHỈ hoạt động khi `permission_to_automate` trong JSON được bật **vì bạn đã nhận được sự cho phép phù hợp**. Chế độ này tự điền theo bước đã duyệt nhưng **không tự bấm Đăng**; chủ cửa hàng phải tự thao tác bước đăng cuối. Phải có nhiệm vụ mới đã duyệt để chạy; ví dụ job 1 đã đóng sẽ không chạy lại.

Playwright không thể học để xử lý mọi thay đổi chỉ từ 1 lần làm mẫu. Các trường như danh mục, giấy tờ, thương hiệu, kích cỡ, cân nặng, mã kho, thuế, nhãn hàng… có thể cần thêm thông tin và phải kiểm tra theo từng sản phẩm. **Không tự vượt CAPTCHA, OTP, 2FA hoặc xác thực bảo mật**.

## 5. Điều khoản sử dụng cần lưu ý

- **TikTok Shop Việt Nam:** Điều khoản Seller cập nhật 09/02/2026 hạn chế bot hay phương tiện truy cập tự động khi chưa có sự cho phép rõ ràng bằng văn bản: https://seller-vn.tiktok.com/university/essay?knowledge_id=2581017870255874&lang=en
- **Shopee:** Tài liệu hỗ trợ cảnh báo việc dùng phần mềm giả lập/bot không được cấp phép truy cập ứng dụng Shopee, có nguy cơ hạn chế tài khoản: https://help.shopee.vn/portal/4/article/79263
- **Tránh làm việc tự động trên tài khoản thật khi chưa xác minh điều khoản**, không thực hiện truy cập ẩn hay né hệ thống chống bot.

## 6. Giới hạn bản phát hành

- Đã có mã nguồn xử lý Telegram, ảnh, SQLite, duyệt và chạy trình duyệt. **Chưa kiểm thử end-to-end với Telegram Bot token thật hoặc Seller Center thật** vì không có thông tin tài khoản của bạn.
- Chưa tự sinh tiêu đề/miêu tả từ ảnh. Bản này lấy dữ liệu chuẩn trong `products.json`; AI soạn nội dung bằng `main.py` là bước riêng và cần con người kiểm duyệt trước khi cập nhật dữ liệu SKU.
- Chưa hỗ trợ nhiều shop cùng lúc, nhiều session browser của cùng một hồ sơ, tạo biến thể phức tạp, hoặc tự xử lý thay đổi giao diện.
- Chỉ chạy khi máy bật, có kết nối Internet, Python còn chạy; nếu ngủ/tắt máy sẽ ngừng nhận và xử lý. Telegram có thể giữ update pending nhưng không bảo đảm không thất lạc nếu lưu hàng đợi quá lâu.
- Thư mục `listing_data/browser_profiles` lưu session/cookie nhạy cảm. Không tải lên GitHub hay chia sẻ.

---

## Bản mở rộng nhiều gian hàng (Multi-Shop)

Tệp này được đóng gói cùng **`SHOP_PROFILES_GUIDE.md`**. Bản mở rộng hỗ trợ một Chrome/Chromium profile riêng và proxy cố định cho mỗi `account_id`, gán nhiều tài khoản vào công việc Telegram, quét DOM thử nghiệm trên file HTML nội bộ và kiểm thử tách job cho từng shop. Bản mở rộng không sử dụng API của sàn và chưa có chức năng tự bấm Đăng. Vui lòng đọc `SHOP_PROFILES_GUIDE.md` trước khi sử dụng.
