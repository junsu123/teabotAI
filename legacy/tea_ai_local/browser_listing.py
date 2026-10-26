"""TEA AI Local - browser-assisted product listing (no marketplace APIs).

Default mode is human-assisted. UI automation is available only for sites/flows
whose operator has explicitly confirmed permission in browser_steps.json.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import html
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import time
from urllib.parse import urlparse
from contextlib import contextmanager
from shop_profiles import get_account, all_accounts, account_context

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'listing_data'
DB = DATA / 'listings.sqlite3'
FILES = DATA / 'images'
PREVIEWS = DATA / 'previews'
PROFILES = DATA / 'browser_profiles'
RECORDINGS = DATA / 'recordings'
PRODUCTS = ROOT / 'products.json'
STEPS = ROOT / 'browser_steps.json'
SHOP_URLS = {
    'shopee': 'https://banhang.shopee.vn/',
    'tiktok': 'https://seller-vn.tiktok.com/',
}
MODES = {'new', 'update'}
MAX_IMAGE_BYTES = 15 * 1024 * 1024


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def initialize() -> None:
    for path in (DATA, FILES, PREVIEWS, PROFILES, RECORDINGS):
        path.mkdir(parents=True, exist_ok=True)
    with connect() as db:
        db.executescript('''
          CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT NOT NULL, shop TEXT NOT NULL, mode TEXT NOT NULL,
            status TEXT NOT NULL, owner_id TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL DEFAULT '', description TEXT NOT NULL DEFAULT '',
            price INTEGER, stock INTEGER, approved_by TEXT DEFAULT '',
            product_url TEXT DEFAULT '', error TEXT DEFAULT '',
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            account_id TEXT NOT NULL DEFAULT ''
          );
          CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL, file_path TEXT NOT NULL, sha256 TEXT NOT NULL,
            UNIQUE(job_id,sha256), FOREIGN KEY(job_id) REFERENCES jobs(id)
          );
          CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL, at TEXT NOT NULL,
            event TEXT NOT NULL, details TEXT NOT NULL DEFAULT ''
          );
        ''')
        cols={row['name'] for row in db.execute('PRAGMA table_info(jobs)')}
        if 'account_id' not in cols:
            db.execute("ALTER TABLE jobs ADD COLUMN account_id TEXT NOT NULL DEFAULT ''")
    if not PRODUCTS.exists():
        PRODUCTS.write_text(json.dumps({
          'TRA-DEMO-01': {
             'title': 'THAY BẰNG TÊN SẢN PHẨM TRÊN NHÃN',
             'description': 'THAY BẰNG MÔ TẢ ĐÃ KIỂM TRA',
             'price': None, 'stock': None,
             'notes': 'Điền thông tin thật trước khi duyệt đăng.'
          }
        }, ensure_ascii=False, indent=2), encoding='utf-8')
    if not STEPS.exists():
        STEPS.write_text(json.dumps({
          '_note': 'Mặc định chỉ hỗ trợ thủ công. Không bật tự động hóa trên sàn khi chưa được phép.',
          'shopee': {'start_url': SHOP_URLS['shopee'], 'permission_to_automate': False, 'steps': []},
          'tiktok': {'start_url': SHOP_URLS['tiktok'], 'permission_to_automate': False, 'steps': []}
        }, ensure_ascii=False, indent=2), encoding='utf-8')


def connect():
    db = sqlite3.connect(DB, timeout=20)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys = ON')
    return db


def product(sku: str) -> dict:
    products = json.loads(PRODUCTS.read_text(encoding='utf-8'))
    if sku not in products:
        raise ValueError(f'Chưa có SKU {sku!r} trong products.json')
    record = products[sku]
    for key in ('title','description','price','stock'):
        if key not in record:
            raise ValueError(f'SKU {sku} thiếu trường {key}')
    if record['price'] is not None and (type(record['price']) is not int or record['price'] < 0):
        raise ValueError('Giá phải là số nguyên >= 0 hoặc null')
    if record['stock'] is not None and (type(record['stock']) is not int or record['stock'] < 0):
        raise ValueError('Tồn kho phải là số nguyên >= 0 hoặc null')
    return record


def log(db, job_id: int, event: str, details: str = '') -> None:
    db.execute('INSERT INTO events(job_id,at,event,details) VALUES(?,?,?,?)',
               (job_id,now(),event,details[:1000]))


def create_job(sku: str, shop: str, mode: str, owner_id: str = '', account_id: str = '') -> int:
    initialize()
    if shop not in SHOP_URLS or mode not in MODES:
        raise ValueError('SHOP phải là shopee hoặc tiktok; MODE phải là new hoặc update')
    if account_id:
        account=get_account(account_id)
        if account['platform'] != shop:
            raise ValueError('account_id thuộc sàn khác với shop được chỉ định')
    elif any(a['platform']==shop for a in all_accounts().values()):
        raise ValueError('Đã có danh sách gian hàng; phải chọn ACCOUNT cụ thể để tránh đăng nhầm shop')
    info = product(sku)
    with connect() as db:
        dup = db.execute('''SELECT id FROM jobs WHERE sku=? AND shop=? AND mode=?
            AND account_id=? AND status IN ('received','approved','editing','needs_confirmation') ORDER BY id DESC LIMIT 1''',
            (sku,shop,mode,account_id)).fetchone()
        if dup:
            raise ValueError(f'Đang có nhiệm vụ chưa xong #{dup["id"]}; dùng ADD={dup["id"]} để thêm ảnh')
        cur = db.execute('''INSERT INTO jobs
            (sku,shop,mode,status,owner_id,title,description,price,stock,created_at,updated_at,account_id)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',
            (sku,shop,mode,'received',str(owner_id),info['title'],info['description'],
             info['price'],info['stock'],now(),now(),account_id))
        jid = cur.lastrowid
        log(db,jid,'created', f'{shop}/{mode}')
    return int(jid)


def get_job(job_id: int) -> dict:
    initialize()
    with connect() as db:
        record = db.execute('SELECT * FROM jobs WHERE id=?',(job_id,)).fetchone()
        if record is None:
            raise ValueError(f'Không thấy nhiệm vụ #{job_id}')
        result = dict(record)
        result['images'] = [r['file_path'] for r in
                            db.execute('SELECT file_path FROM images WHERE job_id=? ORDER BY id',(job_id,))]
    return result


def add_image(job_id: int, original: str | Path) -> str:
    job = get_job(job_id)
    if job['status'] not in ('received','approved'):
        raise ValueError('Không thể thêm ảnh sau khi đã bắt đầu mở phiên đăng')
    source = Path(original)
    if source.suffix.lower() not in {'.png','.jpg','.jpeg','.webp'}:
        raise ValueError('Chỉ nhận PNG/JPG/WEBP')
    size = source.stat().st_size
    if size == 0 or size > MAX_IMAGE_BYTES:
        raise ValueError('Ảnh rỗng hoặc vượt quá 15 MB')
    # Check actual image signature; never trust Telegram filenames alone.
    from PIL import Image, UnidentifiedImageError
    try:
        with Image.open(source) as img:
            img.verify()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValueError('File không phải ảnh hợp lệ') from exc
    binary = source.read_bytes()
    digest = hashlib.sha256(binary).hexdigest()
    output_folder = FILES / str(job_id)
    output_folder.mkdir(parents=True,exist_ok=True)
    dst = output_folder / (digest[:20] + source.suffix.lower())
    if not dst.exists():
        dst.write_bytes(binary)
    with connect() as db:
        db.execute('INSERT OR IGNORE INTO images(job_id,file_path,sha256) VALUES(?,?,?)',
                   (job_id,str(dst),digest))
        log(db,job_id,'image_added',digest[:12])
    return str(dst)


def update_state(job_id: int, status: str, *, by: str = '', details: str = '', product_url: str = '') -> None:
    job = get_job(job_id)
    rules = {
      'received': {'approved','rejected'},
      'approved': {'editing','rejected'},
      'editing': {'needs_confirmation','failed'},
      'needs_confirmation': {'posted','failed'},
      'failed': {'approved','rejected'},
      'rejected': set(), 'posted': set(),
    }
    if status not in rules.get(job['status'],set()):
        raise ValueError(f'Chuyển trạng thái không hợp lệ: {job["status"]} -> {status}')
    if status == 'approved':
        if not job['images']:
            raise ValueError('Chưa có ảnh')
        if job['price'] is None or job['stock'] is None:
            raise ValueError('Thiếu giá hoặc tồn kho thật trong products.json. Tạo nhiệm vụ mới sau khi cập nhật SKU.')
        if 'THAY BẰNG' in job['title'] or 'THAY BẰNG' in job['description']:
            raise ValueError('Còn nội dung mẫu, cần cập nhật products.json và tạo nhiệm vụ mới')
    if status == 'posted' and not by:
        raise ValueError('Phải có người xác nhận đã đăng')
    with connect() as db:
        db.execute('''UPDATE jobs SET status=?, approved_by=CASE WHEN ?='approved' THEN ? ELSE approved_by END,
             product_url=CASE WHEN ?='posted' THEN ? ELSE product_url END,
             error=CASE WHEN ?='failed' THEN ? ELSE error END,
             updated_at=? WHERE id=?''',
             (status,status,by,status,product_url,status,details,now(),job_id))
        log(db,job_id,status, f'{by}: {details}')


def preview(job_id: int) -> Path:
    job = get_job(job_id)
    img = '\n'.join(f'<img alt="Ảnh sản phẩm" src="{Path(p).as_uri()}" />' for p in job['images'])
    fields = {'SKU':job['sku'],'Sàn':job['shop'],'Tài khoản':job.get('account_id') or '(legacy)', 'Chế độ':job['mode'],
              'Tên':job['title'],'Mô tả':job['description'],
              'Giá':job['price'] if job['price'] is not None else 'CHƯA CÓ',
              'Tồn kho':job['stock'] if job['stock'] is not None else 'CHƯA CÓ'}
    rows = '\n'.join('<div class="field"><b>'+html.escape(k)+'</b><p>'+html.escape(str(v))+'</p>'+
                     '<button data-copy="'+html.escape(str(v),quote=True)+'" onclick="navigator.clipboard.writeText(this.dataset.copy).catch(()=>prompt(\'Sao chép nội dung:\',this.dataset.copy))">Sao chép</button></div>'
                     for k,v in fields.items())
    doc = f'''<!doctype html><html lang="vi"><meta charset="UTF-8" />
      <title>TEA AI | Job #{job_id}</title><style>
      body{{font:16px system-ui,sans-serif;margin:2rem auto;max-width:950px;color:#23313d}}
      .field{{border:1px solid #d6dfe5;padding:12px;margin:10px 0;border-radius:8px}}
      p{{white-space:pre-wrap}}button{{padding:7px 14px;cursor:pointer}}
      img{{max-width:190px;max-height:190px;object-fit:contain;margin:8px}}
      .alert{{background:#fff2d5;padding:10px;border-radius:8px}}</style>
      <h1>Phiếu hỗ trợ đăng sản phẩm #{job_id}</h1>
      <p class="alert">Đây là bản nháp để kiểm tra. Không xác nhận đã đăng nếu chưa kiểm tra trên Seller Center.</p>
      {rows}<h2>Ảnh</h2>{img}</html>'''
    path = PREVIEWS / f'job_{job_id}.html'
    path.write_text(doc,encoding='utf-8')
    return path


def validate_shop_url(shop: str, url: str) -> str:
    domain = urlparse(url)
    approved_host = urlparse(SHOP_URLS[shop]).hostname
    if domain.scheme != 'https' or not domain.hostname or domain.hostname.lower() != approved_host:
        raise ValueError('URL phải là HTTPS trên đúng tên miền Seller Center chính thức đã cấu hình')
    if domain.username or domain.password:
        raise ValueError('Không đặt mật khẩu vào URL')
    return url


def field_locator(page, data: dict):
    k = data.get('by')
    value = data.get('value')
    if not isinstance(value,str) or not value:
        raise ValueError('Locator thiếu value')
    if k == 'label': return page.get_by_label(value)
    if k == 'placeholder': return page.get_by_placeholder(value)
    if k == 'role':
        role = data.get('role')
        if not role: raise ValueError('Cần role')
        return page.get_by_role(role,name=value)
    if k == 'css': return page.locator(value)
    if k == 'test_id': return page.get_by_test_id(value)
    if k == 'name': return page.locator('[name=' + json.dumps(value) + ']')
    if k == 'id': return page.locator('[id=' + json.dumps(value) + ']')
    raise ValueError('Locator chỉ hỗ trợ label/placeholder/role/css/test_id/name/id')


def run_steps(page, shop: str, job: dict, *, allowed: bool) -> None:
    # A per-account reviewed configuration can supersede platform defaults.
    profile_config = RECORDINGS / f"{job.get('account_id','')}_{job['mode']}_steps.json"
    config = (json.loads(profile_config.read_text(encoding='utf-8'))
              if job.get('account_id') and profile_config.exists()
              else json.loads(STEPS.read_text(encoding='utf-8'))[shop])
    steps = config.get('steps',[])
    if not allowed or not bool(config.get('permission_to_automate')):
        raise PermissionError('Chưa khai báo được phép tự động hóa giao diện cho sàn này')
    if not steps:
        raise ValueError('Chưa cấu hình steps cho sàn này. Hãy ghi thao tác mẫu và chuyển thành JSON.')
    vars = {k:str(job[k]) for k in ['sku','title','description','price','stock']}
    vars['images'] = job['images']
    for index,step in enumerate(steps,1):
        action = step.get('action')
        if action == 'pause':
            input(f'[Bước {index}] Vui lòng thao tác thủ công rồi nhấn Enter để tiếp tục... ')
            continue
        if action not in {'fill','upload','click','select'}:
            raise ValueError(f'Hành động không hỗ trợ: {action}')
        locator = field_locator(page,step.get('locator',{}))
        count = locator.count()
        if count != 1:
            raise ValueError(f'Bước {index}: tìm thấy {count} trường, yêu cầu đúng 1; dừng để tránh điền nhầm')
        if action == 'fill':
            key = step.get('field')
            if key not in vars or key == 'images': raise ValueError('Trường fill không hợp lệ')
            locator.fill(vars[key], timeout=15000)
        elif action == 'upload':
            locator.set_input_files(vars['images'], timeout=20000)
        elif action == 'select':
            key = step.get('field')
            if key not in vars or key == 'images': raise ValueError('Trường select không hợp lệ')
            locator.select_option(label=vars[key],timeout=15000)
        else:
            # Safety by design: a generic click could trigger an irreversible
            # publish action even when JSON fails to label it as publishing.
            # Use a manual pause instead; all publishing stays human-controlled.
            raise ValueError('Tự click bị tắt để tránh bấm nhầm Đăng; hãy dùng action=pause để người dùng thao tác')


@contextmanager
def legacy_context(playwright, shop: str):
    context = playwright.chromium.launch_persistent_context(
        user_data_dir=str(PROFILES / shop), headless=False,
        accept_downloads=False, viewport={'width':1360,'height':900})
    try:
        yield context
    finally:
        context.close()


def browser_work(job_id: int, automation: bool = False) -> None:
    initialize()
    job = get_job(job_id)
    if job['status'] != 'approved':
        raise ValueError('Nhiệm vụ phải được duyệt trước khi mở trình duyệt')
    config = json.loads(STEPS.read_text(encoding='utf-8'))[job['shop']]
    account_id = job.get('account_id') or ''
    url = (get_account(account_id)['start_url'] if account_id else config['start_url'])
    url = validate_shop_url(job['shop'], url)
    print('Phiếu nội dung:', preview(job_id))
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        context_manager = account_context(p, account_id) if account_id else legacy_context(p, job['shop'])
        with context_manager as context:
            try:
                page = context.pages[0] if context.pages else context.new_page()
                page.goto(url,wait_until='domcontentloaded',timeout=60000)
                update_state(job_id,'editing',details=f'Opened {account_id or job["shop"]} browser')
                print('Mở Seller Center trong profile:', account_id or job['shop'])
                print('Đăng nhập/OTP thủ công nếu được yêu cầu. Không gửi thông tin đăng nhập lên Telegram.')
                if automation:
                    run_steps(page,job['shop'],job,allowed=True)
                else:
                    print('Chế độ hỗ trợ thủ công (không tự thao tác trên sàn).')
                print('Xem phiếu HTML; kiểm tra và đăng trên trang chính thức khi được phép.')
                input('Khi đóng phiên, nhấn Enter... ')
                update_state(job_id,'needs_confirmation',details='Awaiting owner verification')
                print('Nếu đã đăng thật: python browser_listing.py posted',job_id,'--url URL_SAN_PHAM')
            except Exception as exc:
                if get_job(job_id)['status']=='editing':
                    update_state(job_id,'failed',details=str(exc)[:250])
                raise


def record_browser(shop: str, mode: str) -> None:
    if shop not in SHOP_URLS or mode not in MODES:
        raise ValueError('shop hoặc mode không hợp lệ')
    initialize()
    print('CHỈ DÙNG ghi thao tác trên gian hàng khi được nền tảng cho phép.')
    print('Không ghi mật khẩu, OTP, dữ liệu khách hàng, thông tin nhạy cảm.')
    print('Playwright sẽ tạo file mã nguồn tham khảo; không tự chạy file đó.')
    path = RECORDINGS / f'{shop}_{mode}.py'
    command = [sys.executable,'-m','playwright','codegen','--target','python',
               '--output',str(path),'--user-data-dir',str(PROFILES / ('codegen_'+shop)),
               SHOP_URLS[shop]]
    subprocess.run(command,check=True)
    print('Đã ghi mã mẫu tại:',path)


def print_status(job_id: int):
    job = get_job(job_id)
    print(json.dumps(job,ensure_ascii=False,indent=2))


def main(argv=None):
    parser = argparse.ArgumentParser(description='TEA AI – hỗ trợ đăng sản phẩm bằng trình duyệt, không dùng API sàn')
    sub = parser.add_subparsers(dest='command',required=True)
    sub.add_parser('init')
    c=sub.add_parser('create');c.add_argument('sku');c.add_argument('shop',choices=SHOP_URLS);c.add_argument('mode',choices=MODES);c.add_argument('--account',default='')
    assign=sub.add_parser('assign');assign.add_argument('sku');assign.add_argument('mode',choices=MODES);assign.add_argument('--accounts',required=True,help='Danh sách account_id cách nhau dấu phẩy')
    a=sub.add_parser('add');a.add_argument('id',type=int);a.add_argument('image')
    for name in ('status','preview','approve','reject','work'):
        p=sub.add_parser(name);p.add_argument('id',type=int)
        if name=='work':p.add_argument('--auto',action='store_true')
    post=sub.add_parser('posted');post.add_argument('id',type=int);post.add_argument('--url',default='')
    l=sub.add_parser('record');l.add_argument('shop',choices=SHOP_URLS);l.add_argument('mode',choices=MODES)
    watch=sub.add_parser('watch'); watch.add_argument('--seconds',type=int,default=20)
    args=parser.parse_args(argv)
    try:
        if args.command=='init':initialize();print('Đã khởi tạo',ROOT)
        elif args.command=='create':print('Job #',create_job(args.sku,args.shop,args.mode,account_id=args.account),sep='')
        elif args.command=='assign':
            ids=[a.strip() for a in args.accounts.split(',') if a.strip()]
            if not ids or len(ids)!=len(set(ids)):raise ValueError('Danh sách account_id rỗng hoặc trùng')
            for account_id in ids:
                shop=get_account(account_id)['platform']
                print(f'{account_id}: Job #{create_job(args.sku,shop,args.mode,account_id=account_id)}')
        elif args.command=='add':print(add_image(args.id,args.image))
        elif args.command=='status':print_status(args.id)
        elif args.command=='preview':print(preview(args.id))
        elif args.command=='approve':update_state(args.id,'approved',by='local_owner');print('Đã duyệt job',args.id)
        elif args.command=='reject':update_state(args.id,'rejected',by='local_owner');print('Đã từ chối job',args.id)
        elif args.command=='work':browser_work(args.id,automation=args.auto)
        elif args.command=='posted':update_state(args.id,'posted',by='local_owner',product_url=args.url);print('Đã ghi nhận do người dùng xác nhận')
        elif args.command=='record':record_browser(args.shop,args.mode)
        elif args.command=='watch':
            initialize();print('Đang chờ việc đã được duyệt. Ctrl+C để dừng.')
            while True:
                with connect() as db:
                    ids=[row['id'] for row in db.execute("SELECT id FROM jobs WHERE status='approved' ORDER BY id")]
                for jid in ids:
                    try: browser_work(jid,automation=False)
                    except Exception as e: print(f'Job {jid}: {e}',file=sys.stderr)
                time.sleep(max(5,args.seconds))
    except (ValueError,PermissionError,FileNotFoundError) as exc:
        parser.exit(2,f'Lỗi: {exc}\n')


if __name__=='__main__':
    main()
