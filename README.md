# TEA AI Mars Studio v2

Phần mềm GUI Python quản lý công ty marketing AI: trụ sở Sao Hỏa 2.5D, gian hàng Shopee/TikTok Shop, Chrome profiles, proxy và ghi học thao tác DOM.

> Đây là bản thử nghiệm. Các thao tác đăng sản phẩm thực tế cần quyền sử dụng phù hợp và kiểm tra riêng trên các sàn. Không lưu hoặc commit cookie, OTP, mật khẩu, token Telegram lên repository.

## Tải dự án về máy Windows

```powershell
git clone https://github.com/junsu123/teabotAI.git
cd teabotAI\studio
.\setup_windows.bat
.\start_windows.bat
```

**Yêu cầu:** Python 3.11+ và Git. Truy cập giao diện theo thông báo trong cửa sổ lệnh (mặc định `http://127.0.0.1:8765`).

## Cấu trúc

- `studio/` – giao diện và server cục bộ, quản lý proxy, ghi thao tác DOM trong môi trường được phép.
- `legacy/tea_ai_local/` – mã nguồn agent, Telegram và profile từ bản thử nghiệm trước.
- `studio/README_V2_VI.md` – hướng dẫn v2 chi tiết.
- `.gitignore` – chặn dữ liệu phiên làm việc và các file chứa bí mật khỏi lần commit sau.

## Lệnh cập nhật

```powershell
cd teabotAI
git pull
```

## Bảo mật

Repository được phát hành để chia sẻ **mã nguồn**. Tài khoản shop, proxy, cookies, key và dữ liệu kinh doanh phải cấu hình trên máy. Tránh vô hiệu hóa xác thực bảo mật của sàn.
