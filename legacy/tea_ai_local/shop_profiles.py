"""Per-account persistent Chrome/Chromium profiles and read-only DOM form mapping.

Uses browser UI only; no Shopee/TikTok Shop APIs. All live automation/inspection
requires the operator to confirm they have platform permission. No password,
OTP, cookie export, anti-bot evasion, or automatic final publishing.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'listing_data'
PROFILES = DATA / 'account_profiles'
SCHEMAS = DATA / 'form_schemas'
REGISTRY = ROOT / 'shop_accounts.json'
PLATFORMS = {
    'shopee': 'https://banhang.shopee.vn/',
    'tiktok': 'https://seller-vn.tiktok.com/',
}
ACCOUNT_RE = re.compile(r'^[a-z0-9][a-z0-9_-]{1,39}$')
PREFIX_RE = re.compile(r'^[A-Z][A-Z0-9_]{2,60}$')


def _private_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if os.name != 'nt':
        path.chmod(0o700)


def _private_write(path: Path, data: dict) -> None:
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    if os.name != 'nt':
        temp.chmod(0o600)
    temp.replace(path)


def init() -> None:
    for p in (DATA, PROFILES, SCHEMAS):
        _private_dir(p)
    if not REGISTRY.exists():
        _private_write(REGISTRY, {'accounts': {}})


def all_accounts() -> dict:
    init()
    result = json.loads(REGISTRY.read_text(encoding='utf-8'))
    if not isinstance(result.get('accounts'), dict):
        raise ValueError('shop_accounts.json không hợp lệ')
    return result['accounts']


def validate_id(account_id: str) -> str:
    if not ACCOUNT_RE.fullmatch(account_id):
        raise ValueError('account_id phải dùng chữ thường, số, gạch nối/gạch dưới; dài 2–40 ký tự')
    return account_id


def allowed_url(platform: str, url: str) -> str:
    expected = urlparse(PLATFORMS[platform]).hostname
    parsed = urlparse(url)
    if (parsed.scheme != 'https' or parsed.hostname != expected
            or parsed.username or parsed.password or parsed.fragment):
        raise ValueError('Chỉ được mở trang HTTPS trên đúng tên miền Seller Center đã khai báo')
    return url


def validate_proxy(proxy_server: str | None, env_prefix: str | None) -> dict | None:
    if not proxy_server:
        if env_prefix:
            raise ValueError('proxy_env_prefix cần proxy_server')
        return None
    p = urlparse(proxy_server)
    if p.scheme not in {'http', 'https', 'socks5'} or not p.hostname or not p.port:
        raise ValueError('Proxy cần có dạng http://host:port hoặc socks5://host:port')
    if p.username or p.password or p.path or p.query or p.fragment:
        raise ValueError('Không đưa mật khẩu/proxy credentials vào URL')
    if env_prefix and not PREFIX_RE.fullmatch(env_prefix):
        raise ValueError('proxy_env_prefix chỉ chứa chữ hoa, số và _')
    return {'server': proxy_server, 'env_prefix': env_prefix or ''}


def add_account(account_id: str, platform: str, *, alias: str = '', proxy_server: str | None = None,
                proxy_env_prefix: str | None = None, browser: str = 'chrome') -> dict:
    validate_id(account_id)
    if platform not in PLATFORMS:
        raise ValueError('Nền tảng phải là shopee hoặc tiktok')
    if browser not in {'chrome', 'chromium'}:
        raise ValueError('Browser phải là chrome hoặc chromium')
    accounts = all_accounts()
    if account_id in accounts:
        raise ValueError(f'Account {account_id} đã tồn tại; không được ghi đè profile')
    entry = {
        'platform': platform,
        'alias': alias.strip()[:100] or account_id,
        'browser': browser,
        'start_url': PLATFORMS[platform],
        'proxy': validate_proxy(proxy_server, proxy_env_prefix),
    }
    accounts[account_id] = entry
    _private_dir(PROFILES / account_id)
    _private_write(REGISTRY, {'accounts': accounts})
    return entry


def get_account(account_id: str) -> dict:
    validate_id(account_id)
    accounts = all_accounts()
    if account_id not in accounts:
        raise ValueError(f'Không có account_id={account_id}')
    record = dict(accounts[account_id])
    if record.get('platform') not in PLATFORMS:
        raise ValueError('Cấu hình platform không hợp lệ')
    allowed_url(record['platform'], record['start_url'])
    validate_proxy((record.get('proxy') or {}).get('server'),
                   (record.get('proxy') or {}).get('env_prefix'))
    return record


def resolve_proxy(record: dict, env_overrides: dict | None = None) -> dict | None:
    cfg = record.get('proxy')
    if not cfg:
        return None
    proxy = {'server': cfg['server']}
    prefix = cfg.get('env_prefix')
    if prefix:
        env = os.environ if env_overrides is None else {**os.environ, **env_overrides}
        user = env.get(f'{prefix}_USERNAME')
        password = env.get(f'{prefix}_PASSWORD')
        if bool(user) != bool(password):
            raise ValueError(f'Cần cả {prefix}_USERNAME và {prefix}_PASSWORD trong biến môi trường')
        if user:
            proxy.update(username=user, password=password)
    return proxy


@contextmanager
def account_context(playwright, account_id: str, proxy_env: dict | None = None):
    """One profile = one browser process. Profile contents never copied/exported."""
    account = get_account(account_id)
    folder = PROFILES / account_id
    _private_dir(folder)
    lock = folder / '.tea_ai_in_use'
    # Exclusive lock for independent Python workers (profile also locked by Chrome).
    try:
        fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as e:
        raise RuntimeError(f'{account_id} đã có phiên trình duyệt hoặc còn file khóa sau sự cố; đóng Chrome trước khi xử lý') from e
    os.close(fd)
    context = None
    try:
        kwargs = {
            'user_data_dir': str(folder),
            'headless': False,
            'accept_downloads': False,
            'viewport': {'width': 1400, 'height': 900},
        }
        if account['browser'] == 'chrome':
            kwargs['channel'] = 'chrome'
        proxy = resolve_proxy(account, proxy_env)
        if proxy:
            kwargs['proxy'] = proxy
        context = playwright.chromium.launch_persistent_context(**kwargs)
        yield context
    finally:
        try:
            if context is not None:
                context.close()
        finally:
            lock.unlink(missing_ok=True)


# Read-only DOM inventory: never access input.value, password/OTP, browser cookies,
# session storage, local storage, full HTML, hidden fields, or auth tokens.
DOM_INVENTORY_JS = r'''() => {
 const privateRe = /(password|passcode|otp|secret|auth|token|cookie|2fa|mật khẩu|xác minh|số điện thoại|phone|e-?mail)/i;
 const items = Array.from(document.querySelectorAll('input,textarea,select,[contenteditable="true"]')).slice(0,250);
 return items.flatMap((e) => {
   const tag = e.tagName.toLowerCase();
   const type = (e.getAttribute('type') || '').toLowerCase();
   if (['password','hidden','email','tel'].includes(type)) return [];
   const info = {
     tag,
     type,
     id: e.getAttribute('id') || '',
     name: e.getAttribute('name') || '',
     placeholder: e.getAttribute('placeholder') || '',
     aria_label: e.getAttribute('aria-label') || '',
     test_id: e.getAttribute('data-testid') || '',
     label: Array.from(e.labels || []).map(x=>x.innerText.trim()).filter(Boolean).join(' | '),
   };
   if (privateRe.test(Object.values(info).join(' '))) return [];
   return [Object.fromEntries(Object.entries(info).map(([k,v]) => [k, String(v).slice(0,120)]))];
 });
}'''


def suggest_field(info: dict) -> tuple[str, str]:
    value = ' '.join(str(info.get(k,'')) for k in ('label','aria_label','placeholder','name','id')).lower()
    matches = [
        ('title', ('tên sản phẩm', 'product name', 'product title', 'product_name')),
        ('description', ('mô tả', 'description', 'chi tiết sản phẩm')),
        ('price', ('giá bán', 'giá sản phẩm', 'price')),
        ('stock', ('tồn kho', 'kho hàng', 'inventory', 'stock', 'quantity')),
        ('images', ('tải ảnh', 'hình ảnh', 'upload image', 'product image')),
    ]
    for field, keywords in matches:
        if any(term in value for term in keywords):
            return field, 'needs_review'
    if info.get('type') == 'file':
        return 'images', 'needs_review'
    return '', 'unknown'


def scan_page(page) -> list[dict]:
    """Run only on local demo or pages the operator has permission to inspect."""
    output = []
    for frame in page.frames:
        try:
            for info in frame.evaluate(DOM_INVENTORY_JS):
                field, confidence = suggest_field(info)
                info['suggested_field'] = field
                info['confidence'] = confidence
                info['frame_url_host'] = urlparse(frame.url).hostname or 'local'
                output.append(info)
        except Exception:
            # Cross-origin, removed or inaccessible frames are ignored.
            continue
    return output[:250]


def scan_local_html(html_path: str | Path, account_id: str, mode: str) -> Path:
    from playwright.sync_api import sync_playwright
    if mode not in {'new','update'}:
        raise ValueError('Mode phải là new hoặc update')
    get_account(account_id)
    p = Path(html_path).resolve()
    if not p.is_file() or p.suffix.lower() not in {'.html','.htm'}:
        raise ValueError('Chỉ quét file HTML mẫu cục bộ')
    with sync_playwright() as playwright:
        with account_context(playwright, account_id) as context:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(p.as_uri(), wait_until='domcontentloaded')
            inventory = scan_page(page)
    dest = SCHEMAS / f'{account_id}_{mode}.json'
    _private_write(dest, {'account_id': account_id, 'mode': mode, 'source': 'local_demo',
                          'fields': inventory, 'reviewed': False})
    return dest


def check_account_once(account_id: str, proxy_env: dict | None = None) -> dict:
    """User-requested, visible browser read-only session check for a closed profile."""
    from playwright.sync_api import sync_playwright
    from session_monitor import write_status, read_status, verify_in_separate_tab
    account = get_account(account_id)
    folder = PROFILES / account_id
    lock = folder / '.tea_ai_in_use'
    if lock.exists():
        # The original browser process owns the profile. Never open it twice.
        (folder / 'check_login.request').touch()
        return {**read_status(folder), 'message': 'Đã yêu cầu Chrome đang mở kiểm tra bằng trang quản trị.'}
    write_status(folder, 'checking', message='Đang mở trang quản trị đã xác minh...')
    try:
        with sync_playwright() as playwright:
            with account_context(playwright, account_id, proxy_env=proxy_env) as context:
                return verify_in_separate_tab(context, account, folder)
    except Exception as exc:
        msg = f'Không thể kiểm tra trạng thái: {type(exc).__name__}. Đóng profile, kiểm tra mạng/proxy rồi thử lại.'
        write_status(folder, 'error', message=msg)
        return read_status(folder)


def interactive_open(account_id: str) -> None:
    """Manual login; automatically inspect status, without exporting cookies."""
    from playwright.sync_api import sync_playwright
    from session_monitor import inspect_and_save, write_status, verify_in_separate_tab, PROBE_REQUEST
    account = get_account(account_id)
    folder = PROFILES / account_id
    with sync_playwright() as playwright:
        with account_context(playwright, account_id) as context:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(account['start_url'], wait_until='domcontentloaded', timeout=60000)
            print(f'Đã mở Chrome Profile {account_id}. Đăng nhập thủ công trong cửa sổ Chrome.')
            print('Phần mềm kiểm tra trạng thái mỗi 5 giây. Đóng cửa sổ Chrome để kết thúc.')
            while True:
                try:
                    alive = [p for p in context.pages if not p.is_closed()]
                except Exception:
                    # Browser was closed by the operator.
                    break
                if not alive:
                    break
                try:
                    requested = folder / PROBE_REQUEST
                    if requested.exists():
                        requested.unlink(missing_ok=True)
                        verify_in_separate_tab(context, account, folder)
                    else:
                        inspect_and_save(context, account, folder)
                except Exception as exc:
                    write_status(folder, 'error',
                                 message=f'Không thể đọc trạng thái: {type(exc).__name__}; đang thử lại.')
                try:
                    alive[0].wait_for_timeout(5000)
                except Exception:
                    import time
                    time.sleep(1)

def main(argv=None):
    parser = argparse.ArgumentParser(description='TEA AI | quản lý profile nhiều gian hàng và đọc DOM trên HTML mẫu')
    commands = parser.add_subparsers(dest='cmd', required=True)
    commands.add_parser('init')
    add = commands.add_parser('add')
    add.add_argument('account_id'); add.add_argument('platform', choices=PLATFORMS)
    add.add_argument('--alias', default=''); add.add_argument('--proxy', default=None)
    add.add_argument('--proxy-env-prefix', default=None)
    add.add_argument('--browser', choices=('chrome','chromium'), default='chrome')
    commands.add_parser('list')
    op = commands.add_parser('open'); op.add_argument('account_id')
    ck = commands.add_parser('check'); ck.add_argument('account_id')
    scan = commands.add_parser('scan-demo'); scan.add_argument('account_id')
    scan.add_argument('html_path'); scan.add_argument('--mode', choices=('new','update'), default='new')
    args = parser.parse_args(argv)
    try:
        if args.cmd == 'init':
            init(); print('Đã khởi tạo shop_accounts.json')
        elif args.cmd == 'add':
            a = add_account(args.account_id, args.platform, alias=args.alias,
                            proxy_server=args.proxy, proxy_env_prefix=args.proxy_env_prefix,
                            browser=args.browser)
            print(f'Đã tạo {args.account_id} ({a["platform"]}, {a["browser"]})')
        elif args.cmd == 'list':
            print(json.dumps(all_accounts(), ensure_ascii=False, indent=2))
        elif args.cmd == 'open':
            interactive_open(args.account_id)
        elif args.cmd == 'check':
            print(json.dumps(check_account_once(args.account_id), ensure_ascii=False))
        elif args.cmd == 'scan-demo':
            print(scan_local_html(args.html_path, args.account_id, args.mode))
    except (ValueError, RuntimeError, OSError) as exc:
        parser.exit(2, f'Lỗi: {exc}\n')


if __name__ == '__main__':
    main()
