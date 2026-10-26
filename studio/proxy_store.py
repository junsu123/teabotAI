"""Local proxy catalog. Credentials are stored via OS keyring, never JSON/SQLite."""
from __future__ import annotations
import sqlite3
from contextlib import closing
import re
from pathlib import Path
from datetime import datetime
import sys
ROOT=Path(__file__).resolve().parent
LEGACY=ROOT.parent/'legacy'/'tea_ai_local'
sys.path.insert(0,str(LEGACY))
import shop_profiles
DB=ROOT/'data'/'proxy_catalog.sqlite3'
RE=re.compile(r'^[a-z][a-z0-9_-]{1,39}$')
SERVICE='tea-ai-mars-proxy-v2'

def now(): return datetime.now().astimezone().isoformat(timespec='seconds')

def connection():
 DB.parent.mkdir(parents=True,exist_ok=True)
 c=sqlite3.connect(DB,timeout=10)
 c.row_factory=sqlite3.Row
 return c

def init():
 with closing(connection()) as c, c:
  c.execute('''CREATE TABLE IF NOT EXISTS proxies (
   id TEXT PRIMARY KEY, name TEXT NOT NULL, scheme TEXT NOT NULL,
   host TEXT NOT NULL, port INTEGER NOT NULL, username TEXT NOT NULL DEFAULT '',
   created_at TEXT NOT NULL, updated_at TEXT NOT NULL)''')

def all_proxies():
 init()
 with closing(connection()) as c, c:
  return [dict(x) for x in c.execute('SELECT * FROM proxies ORDER BY name,id')]

def get_proxy(pid):
 with closing(connection()) as c, c:
  row=c.execute('SELECT * FROM proxies WHERE id=?',(pid,)).fetchone()
 if not row:raise ValueError('Không tìm thấy proxy')
 return dict(row)

def _keyring():
 try:
  import keyring
  from keyring.backends.fail import Keyring as FailKeyring
  kr=keyring.get_keyring()
  if isinstance(kr,FailKeyring):raise RuntimeError('Hệ điều hành chưa có kho mật khẩu khả dụng')
  return keyring
 except ImportError as e:
  raise RuntimeError('Để lưu user/password proxy, hãy cài: py -3 -m pip install keyring') from e

def proxy_prefix(pid):return 'TEA_GUI_'+pid.upper().replace('-','_')

def proxy_url(p):return f"{p['scheme']}://{p['host']}:{p['port']}"

def save_proxy(pid,name,scheme,host,port,username='',password='',edit=False):
 if not RE.fullmatch(pid or ''):raise ValueError('Mã proxy: chữ thường, số, - hoặc _, từ 2–40 ký tự')
 name=(name or '').strip()[:100] or pid
 host=(host or '').strip().lower()
 if not host or any(x in host for x in ' /\\@?#:') or len(host)>253:raise ValueError('Host proxy không hợp lệ (IP hoặc tên miền; không chứa giao thức)')
 if scheme not in ('http','https','socks5'):raise ValueError('Loại proxy không hỗ trợ')
 port=int(port)
 if not 1<=port<=65535:raise ValueError('Cổng phải từ 1 đến 65535')
 username=(username or '').strip()[:120]
 if password and not username:raise ValueError('Nhập tên đăng nhập proxy trước khi nhập mật khẩu')
 shop_profiles.validate_proxy(f'{scheme}://{host}:{port}',proxy_prefix(pid))
 old=None
 try:old=get_proxy(pid)
 except ValueError:pass
 if bool(old)!=bool(edit):raise ValueError('Proxy đã tồn tại hoặc chưa được tạo, vui lòng tải lại giao diện')
 if password:
  kr=_keyring()
  kr.set_password(SERVICE,pid,password)
 elif username and (not old or username!=old['username']):
  raise ValueError('Proxy có username mới phải nhập mật khẩu để lưu an toàn')
 if old and any(a.get('proxy_id')==pid for a in shop_profiles.all_accounts().values()):
  for aid,a in shop_profiles.all_accounts().items():
   if a.get('proxy_id')==pid and (shop_profiles.PROFILES/aid/'.tea_ai_in_use').exists():
    raise ValueError('Đóng Chrome profile đang sử dụng proxy trước khi sửa')
 with closing(connection()) as c, c:
  if edit:
   c.execute('UPDATE proxies SET name=?,scheme=?,host=?,port=?,username=?,updated_at=? WHERE id=?',
     (name,scheme,host,port,username,now(),pid))
  else:
   c.execute('INSERT INTO proxies VALUES(?,?,?,?,?,?,?,?)',
     (pid,name,scheme,host,port,username,now(),now()))
 # Keep per-account launch settings synced; no credentials in registry.
 for aid,a in shop_profiles.all_accounts().items():
  if a.get('proxy_id')==pid: assign_proxy(aid,pid)
 return get_proxy(pid)

def delete_proxy(pid):
 p=get_proxy(pid)
 if any(a.get('proxy_id')==pid for a in shop_profiles.all_accounts().values()):
  raise ValueError('Hãy gỡ proxy khỏi các gian hàng trước khi xóa')
 with closing(connection()) as c, c:c.execute('DELETE FROM proxies WHERE id=?',(pid,))
 if p['username']:
  try:_keyring().delete_password(SERVICE,pid)
  except Exception:pass

def assign_proxy(aid,pid=''):
 account=shop_profiles.get_account(aid)
 if (shop_profiles.PROFILES/aid/'.tea_ai_in_use').exists():raise ValueError('Đóng Chrome profile trước khi đổi proxy')
 allacc=shop_profiles.all_accounts()
 account=allacc[aid]
 if pid:
  p=get_proxy(pid)
  account['proxy']=shop_profiles.validate_proxy(proxy_url(p),proxy_prefix(pid))
  account['proxy_id']=pid
 else:
  account['proxy']=None
  account['proxy_id']=''
 allacc[aid]=account
 shop_profiles._private_write(shop_profiles.REGISTRY,{'accounts':allacc})
 return {'account_id':aid,'proxy_id':pid}

def account_env(aid):
 account=shop_profiles.get_account(aid)
 pid=account.get('proxy_id')
 if not pid:return {}
 p=get_proxy(pid)
 if not p['username']:return {}
 pwd=_keyring().get_password(SERVICE,pid)
 if not pwd:raise ValueError('Không tìm thấy mật khẩu proxy trong kho mật khẩu hệ điều hành')
 prefix=proxy_prefix(pid)
 return {f'{prefix}_USERNAME':p['username'],f'{prefix}_PASSWORD':pwd}
