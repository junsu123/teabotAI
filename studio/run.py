"""TEA AI Mars Studio: local-first GUI over the existing tea_ai_local toolkit.

Uses only Python standard library for the dashboard HTTP server. Marketplace
publishing is intentionally not initiated by the dashboard. A profile can be
opened for manual login/use by the operator, subject to the platform rules.
"""
from __future__ import annotations
import json
import sqlite3
import os
import sys
import shutil
import tempfile
import subprocess
import threading
import webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, parse_qs

ROOT=Path(__file__).resolve().parent
STATIC=ROOT/'static'
LEGACY=ROOT.parent/'legacy'/'tea_ai_local'
sys.path.insert(0,str(LEGACY))
import shop_profiles
import browser_listing
import proxy_store
import uuid
import time
import re
import socket

DATA=ROOT/'data'
DB=DATA/'studio.sqlite3'
MAX_JSON=1024*1024
TRAIN_DIR=DATA/"training"
LEARN_PROCS={}
DATA.mkdir(exist_ok=True)
AGENTS=[
 {'id':'ceo','name':'AI CEO','role':'Điều phối & phê duyệt','emoji':'👑','room':'Phòng Founder','color':'#48c4ae'},
 {'id':'research','name':'AI Research','role':'Nghiên cứu thị trường','emoji':'🔭','room':'Đài nghiên cứu','color':'#9d84ff'},
 {'id':'strategy','name':'AI Strategy','role':'Chiến lược marketing','emoji':'🎯','room':'Tháp chiến lược','color':'#ffbf65'},
 {'id':'creative','name':'AI Creative','role':'Nội dung, poster, video','emoji':'🎨','room':'Xưởng sáng tạo','color':'#ff8e67'},
 {'id':'analyst','name':'AI Analyst','role':'Dữ liệu & bài học','emoji':'📊','room':'Trạm phân tích','color':'#6ab7ff'},
 {'id':'compliance','name':'AI Compliance','role':'Kiểm duyệt nội dung','emoji':'🛡️','room':'Trạm kiểm duyệt','color':'#e5a5e3'},
]

def conn():
 c=sqlite3.connect(DB,timeout=10)
 c.row_factory=sqlite3.Row
 return c

def init():
 shop_profiles.init(); browser_listing.initialize();proxy_store.init();TRAIN_DIR.mkdir(exist_ok=True)
 with conn() as c:
  c.executescript('''
   CREATE TABLE IF NOT EXISTS missions (
    id INTEGER PRIMARY KEY AUTOINCREMENT, agent_id TEXT NOT NULL,
    title TEXT NOT NULL, detail TEXT DEFAULT '', status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
   CREATE TABLE IF NOT EXISTS learnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT NOT NULL,
    title TEXT NOT NULL, description TEXT DEFAULT '', source TEXT DEFAULT '',
    validation TEXT NOT NULL DEFAULT 'chưa xác minh', created_at TEXT NOT NULL);
   CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, message TEXT NOT NULL);
  ''')

def utc():return datetime.now().astimezone().isoformat(timespec='seconds')

def sample_safe_records():
 # No fabricated shop accounts or live tasks. Fresh start = zero real shops and jobs.
 return None

def list_accounts():
 registry=shop_profiles.all_accounts()
 return [{ 'id':key, 'name': a['alias'], 'platform': a['platform'],
   'browser': a['browser'], 'proxy': ((a.get('proxy') or {}).get('server') or ''),
   'proxy_env_prefix': ((a.get('proxy') or {}).get('env_prefix') or ''), 'proxy_id':a.get('proxy_id',''),
   'profile_dir': str(shop_profiles.PROFILES/key), 'status':'chưa kiểm tra phiên'}
   for key,a in registry.items()]

def list_jobs():
 with browser_listing.connect() as c:
  out=[]
  for r in c.execute('SELECT id,sku,shop,mode,status,account_id,title,price,stock,created_at,updated_at FROM jobs ORDER BY id DESC LIMIT 200'):
   d=dict(r)
   d['images']=c.execute('SELECT COUNT(*) FROM images WHERE job_id=?',(d['id'],)).fetchone()[0]
   out.append(d)
 return out

def list_missions():
 with conn() as c:return [dict(r) for r in c.execute('SELECT * FROM missions ORDER BY id DESC LIMIT 200')]

def list_learnings():
 with conn() as c:return [dict(r) for r in c.execute('SELECT * FROM learnings ORDER BY id DESC LIMIT 150')]

def list_products():
 return json.loads(browser_listing.PRODUCTS.read_text(encoding='utf-8'))

def training_summary():
 result=[]
 for p in sorted(TRAIN_DIR.glob('*.json'),reverse=True)[:20]:
  if p.name.endswith('.status.json'):
   try:
    d=json.loads(p.read_text(encoding='utf-8'))
    events=TRAIN_DIR/(d['id']+'.events.jsonl')
    d['events_count']=sum(1 for _ in events.open(encoding='utf-8')) if events.exists() else 0
    d['has_result']=(TRAIN_DIR/(d['id']+'.result.json')).exists()
    result.append(d)
   except (KeyError,ValueError,OSError):continue
 return result

def training_detail(session_id):
 if not re.fullmatch(r'[a-f0-9]{16}',session_id):raise ValueError('Mã phiên học không hợp lệ')
 p=TRAIN_DIR/(session_id+'.result.json')
 if p.exists():return json.loads(p.read_text(encoding='utf-8'))
 ev=TRAIN_DIR/(session_id+'.events.jsonl')
 return {'steps':[json.loads(x) for x in ev.read_text(encoding='utf-8').splitlines() if x.strip()][:250] if ev.exists() else [], 'fields':[]}

def overview():
 shops=list_accounts(); jobs=list_jobs(); ms=list_missions()
 return {'agents':AGENTS,'accounts':shops,'jobs':jobs,'missions':ms,
    'learnings':list_learnings(), 'products':list_products(), 'proxies':proxy_store.all_proxies(), 'training':training_summary(),
    'stats':{'agents':len(AGENTS),'shops':len(shops),'jobs_open':sum(x['status'] not in ('posted','rejected','failed') for x in jobs),
             'missions_open':sum(x['status']!='done' for x in ms),'lessons':len(list_learnings())},
    'integration':{'ollama_url':'http://localhost:11434','telegram':'Cần cấu hình token ở máy',
            'browser':'Dùng Playwright ở bộ mã nguồn hiện có','publishing':'Chỉ hỗ trợ người điều hành hoàn tất đăng'}}

def json_reply(handler, obj, status=200):
 b=json.dumps(obj,ensure_ascii=False).encode('utf-8')
 handler.send_response(status);handler.send_header('Content-Type','application/json; charset=utf-8')
 handler.send_header('Cache-Control','no-store');handler.send_header('X-Content-Type-Options','nosniff')
 handler.send_header('Content-Length',str(len(b)));handler.end_headers();handler.wfile.write(b)

def error_reply(handler, code, msg):json_reply(handler,{'ok':False,'error':str(msg)},code)

def sanitize(text,limit=500):
 if not isinstance(text,str):raise ValueError('Giá trị phải là văn bản')
 return text.strip()[:limit]

class Handler(BaseHTTPRequestHandler):
 def log_message(self, fmt, *args):pass
 def is_local_host(self):
  # Reject DNS-rebinding attempts at accessing the machine-local control panel.
  host=self.headers.get('Host','').split(':',1)[0].lower()
  return host in ('127.0.0.1','localhost')
 def do_GET(self):
  if not self.is_local_host():return error_reply(self,403,'Chỉ cho phép truy cập cục bộ')
  path=urlparse(self.path).path
  if path=='/api/overview':return json_reply(self,overview())
  if path=='/api/health':return json_reply(self,{'ok':True,'date':utc(),'version':'0.2.0'})
  if path=='/api/training':return json_reply(self,{'sessions':training_summary()})
  if path=='/api/training/detail':
   sid=parse_qs(urlparse(self.path).query).get('id',[''])[0]
   try:return json_reply(self,training_detail(sid))
   except ValueError as e:return error_reply(self,400,str(e))
  rel='index.html' if path=='/' else path.lstrip('/')
  f=(STATIC/rel).resolve()
  if not f.is_relative_to(STATIC.resolve()) or not f.is_file():return error_reply(self,404,'Không tìm thấy trang')
  mime=('text/html; charset=utf-8' if f.suffix=='.html' else
        'text/javascript; charset=utf-8' if f.suffix=='.js' else
        'text/css; charset=utf-8' if f.suffix=='.css' else 'application/octet-stream')
  content=f.read_bytes();self.send_response(200);self.send_header('Content-Type',mime)
  self.send_header('Content-Length',str(len(content)))
  self.send_header('Cache-Control','no-store')
  self.send_header('X-Content-Type-Options','nosniff')
  self.send_header('Content-Security-Policy',"default-src 'self' 'unsafe-inline' data:; connect-src 'self'; img-src 'self' data:;")
  self.end_headers();self.wfile.write(content)
 def do_POST(self):
  if not self.is_local_host():return error_reply(self,403,'Chỉ cho phép truy cập cục bộ')
  origin=self.headers.get('Origin','')
  if origin and origin not in ('http://'+self.headers.get('Host',''),):
   return error_reply(self,403,'Nguồn yêu cầu không hợp lệ')
  path=urlparse(self.path).path
  try:
   n=int(self.headers.get('Content-Length','0'))
   if n<=0 or n>MAX_JSON:raise ValueError('Dữ liệu vượt quá giới hạn')
   body=json.loads(self.rfile.read(n))
   if not isinstance(body,dict):raise ValueError('Cần đối tượng JSON')
   if path=='/api/accounts':
    pid=sanitize(body.get('proxy_id',''),40)
    if pid:proxy_store.get_proxy(pid)
    account_id=sanitize(body.get('id',''),40)
    platform=body.get('platform','')
    alias=sanitize(body.get('name',''),100)
    proxy=sanitize(body.get('proxy',''),200)
    prefix=sanitize(body.get('proxy_env_prefix',''),60)
    a=shop_profiles.add_account(account_id,platform,alias=alias,proxy_server=None,proxy_env_prefix=None)
    if pid:proxy_store.assign_proxy(account_id,pid)
    return json_reply(self,{'ok':True,'account':{'id':account_id,**shop_profiles.get_account(account_id)}})
   if path=='/api/open-profile':
    aid=sanitize(body.get('account_id',''),40)
    shop_profiles.get_account(aid)
    command=[sys.executable,str(LEGACY/'shop_profiles.py'),'open',aid]
    flags=getattr(subprocess,'CREATE_NEW_CONSOLE',0) if os.name=='nt' else 0
    if os.name!='nt':
     # Console worker needs an actual terminal for the manual login workflow.
     # On Linux, prefer a terminal emulator or report actionable error.
     terminal=next((x for x in ('x-terminal-emulator','gnome-terminal','konsole','xterm') if shutil.which(x)),None)
     if not terminal:raise ValueError('Cần chạy `python shop_profiles.py open '+aid+'` từ Terminal để đăng nhập thủ công')
     if terminal=='gnome-terminal':command=[terminal,'--',*command]
     elif terminal=='konsole':command=[terminal,'-e',*command]
     else:command=[terminal,'-e',*command]
    subprocess.Popen(command,cwd=str(LEGACY),creationflags=flags,env={**os.environ,**proxy_store.account_env(aid)})
    return json_reply(self,{'ok':True,'message':'Đã yêu cầu mở profile; đăng nhập thủ công nếu cần'})
   if path=='/api/proxies':
    pid=sanitize(body.get('id',''),40)
    p=proxy_store.save_proxy(pid,sanitize(body.get('name',''),100),body.get('scheme','http'),
       sanitize(body.get('host',''),253),body.get('port',0),
       sanitize(body.get('username',''),120),body.get('password',''),edit=False)
    return json_reply(self,{'ok':True,'proxy':p})
   if path=='/api/proxies/update':
    pid=sanitize(body.get('id',''),40)
    p=proxy_store.save_proxy(pid,sanitize(body.get('name',''),100),body.get('scheme','http'),
       sanitize(body.get('host',''),253),body.get('port',0),
       sanitize(body.get('username',''),120),body.get('password',''),edit=True)
    return json_reply(self,{'ok':True,'proxy':p})
   if path=='/api/proxies/test':
    pid=sanitize(body.get('id',''),40)
    p=proxy_store.get_proxy(pid)
    try:
     with socket.create_connection((p['host'],p['port']),timeout=2.5):pass
     return json_reply(self,{'ok':True,'reachable':True,
       'message':'Có thể kết nối TCP tới máy chủ proxy; chưa kiểm tra xác thực hoặc IP thoát'})
    except OSError:
     return json_reply(self,{'ok':True,'reachable':False,
       'message':'Không kết nối TCP tới host:port này (hoặc bị firewall chặn)'})
   if path=='/api/proxies/delete':
    proxy_store.delete_proxy(sanitize(body.get('id',''),40))
    return json_reply(self,{'ok':True})
   if path=='/api/accounts/assign-proxy':
    return json_reply(self,{'ok':True,**proxy_store.assign_proxy(sanitize(body.get('account_id',''),40),
        sanitize(body.get('proxy_id',''),40))})
   if path=='/api/training/start':
    aid=sanitize(body.get('account_id',''),40)
    shop_profiles.get_account(aid)
    mode=body.get('mode','new')
    target=body.get('target','demo')
    if mode not in ('new','update'):raise ValueError('Chế độ học không hợp lệ')
    if target not in ('demo','seller'):raise ValueError('Nguồn học không hợp lệ')
    if target=='seller' and body.get('permission_confirmed') is not True:
     raise ValueError('Chỉ được ghi thao tác trên trang sàn khi bạn có quyền phù hợp')
    for sid,proc in list(LEARN_PROCS.items()):
     if proc.poll() is None:raise ValueError('Đang có một phiên học chạy, hãy dừng trước')
    sid=uuid.uuid4().hex[:16]
    status={'id':sid,'account_id':aid,'mode':mode,'target':target,'status':'starting',
            'created_at':utc(),'message':'Đang mở trình duyệt'}
    (TRAIN_DIR/(sid+'.status.json')).write_text(json.dumps(status,ensure_ascii=False),encoding='utf-8')
    args=[sys.executable,str(ROOT/'browser_trainer.py'),'--account',aid,'--mode',mode,
          '--target',target,'--session',sid]
    flags=getattr(subprocess,'CREATE_NEW_CONSOLE',0) if os.name=='nt' else 0
    proc=subprocess.Popen(args,cwd=str(ROOT),creationflags=flags,
          env={**os.environ,**proxy_store.account_env(aid)},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    LEARN_PROCS[sid]=proc
    return json_reply(self,{'ok':True,'session_id':sid})
   if path=='/api/training/stop':
    sid=sanitize(body.get('id',''),32)
    if not re.fullmatch(r'[a-f0-9]{16}',sid):raise ValueError('Mã phiên học không hợp lệ')
    if not (TRAIN_DIR/(sid+'.status.json')).exists():raise ValueError('Không tìm thấy phiên học')
    (TRAIN_DIR/(sid+'.stop')).touch()
    return json_reply(self,{'ok':True,'message':'Đã yêu cầu lưu và dừng phiên học'})
   if path=='/api/missions':
    agent=sanitize(body.get('agent_id',''),40)
    if agent not in {a['id'] for a in AGENTS}:raise ValueError('Nhân viên AI không hợp lệ')
    title=sanitize(body.get('title',''),150)
    detail=sanitize(body.get('detail',''),2000)
    if len(title)<3:raise ValueError('Cần tên nhiệm vụ dài ít nhất 3 ký tự')
    with conn() as c:
     cur=c.execute('INSERT INTO missions(agent_id,title,detail,status,created_at,updated_at) VALUES(?,?,?,?,?,?)',
                  (agent,title,detail,'pending',utc(),utc()))
    return json_reply(self,{'ok':True,'mission_id':cur.lastrowid})
   if path=='/api/missions/status':
    jid=int(body.get('id',0));status=body.get('status','')
    if status not in ('pending','in_progress','done','blocked'):raise ValueError('Trạng thái không hợp lệ')
    with conn() as c:
     cur=c.execute('UPDATE missions SET status=?,updated_at=? WHERE id=?',(status,utc(),jid))
     if not cur.rowcount:raise ValueError('Không tìm thấy nhiệm vụ')
    return json_reply(self,{'ok':True})
   if path=='/api/learnings':
    title=sanitize(body.get('title',''),140);description=sanitize(body.get('description',''),1500)
    if len(title)<3:raise ValueError('Cần tiêu đề bài học')
    cat=sanitize(body.get('category','bài học'),60)
    src=sanitize(body.get('source',''),350)
    with conn() as c:
     cur=c.execute('INSERT INTO learnings(category,title,description,source,validation,created_at) VALUES(?,?,?,?,?,?)',
                    (cat,title,description,src,'chưa xác minh',utc()))
    return json_reply(self,{'ok':True,'learning_id':cur.lastrowid})
   if path=='/api/products':
    sku=sanitize(body.get('sku',''),60)
    if not sku or not all(ch.isalnum() or ch in '-_' for ch in sku):raise ValueError('SKU chỉ chứa chữ, số, - và _')
    title=sanitize(body.get('title',''),200)
    desc=sanitize(body.get('description',''),3000)
    if not title or not desc:raise ValueError('Cần tên và mô tả sản phẩm')
    price=body.get('price');stock=body.get('stock')
    if type(price)!=int or price<0 or type(stock)!=int or stock<0:raise ValueError('Giá và tồn kho phải là số nguyên không âm')
    products=list_products();products[sku]={'title':title,'description':desc,'price':price,'stock':stock,
                                            'notes':'Dữ liệu do người dùng xác nhận trong Mars Studio'}
    browser_listing.PRODUCTS.write_text(json.dumps(products,ensure_ascii=False,indent=2),encoding='utf-8')
    return json_reply(self,{'ok':True,'sku':sku})
   if path=='/api/jobs':
    sku=sanitize(body.get('sku',''),60)
    aid=sanitize(body.get('account_id',''),40)
    mode=body.get('mode','new')
    a=shop_profiles.get_account(aid)
    jid=browser_listing.create_job(sku,a['platform'],mode,owner_id='',account_id=aid)
    return json_reply(self,{'ok':True,'job_id':jid})
   if path=='/api/jobs/reject':
    jid=int(body.get('id',0))
    browser_listing.update_state(jid,'rejected',by='gui_owner')
    return json_reply(self,{'ok':True})
   if path=='/api/jobs/approve':
    jid=int(body.get('id',0))
    browser_listing.update_state(jid,'approved',by='gui_owner')
    return json_reply(self,{'ok':True})
   return error_reply(self,404,'Không có chức năng này')
  except (ValueError,KeyError,sqlite3.Error,OSError,RuntimeError) as e:
   return error_reply(self,400,str(e))
  except Exception as e:
   return error_reply(self,500,f'Lỗi nội bộ: {type(e).__name__}')

def main():
 import argparse
 parser=argparse.ArgumentParser()
 parser.add_argument('--port',type=int,default=8765)
 parser.add_argument('--no-browser',action='store_true')
 args=parser.parse_args()
 if not (1024<=args.port<=65535):raise SystemExit('Port không hợp lệ')
 init()
 url=f'http://127.0.0.1:{args.port}'
 server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
 print(f'TEA AI MARS STUDIO: {url}\nDữ liệu nội bộ: {DB}\nNhấn Ctrl+C để dừng.')
 if not args.no_browser:threading.Timer(0.6,lambda:webbrowser.open(url)).start()
 try:server.serve_forever()
 except KeyboardInterrupt:pass
 finally:server.server_close()

if __name__=='__main__':main()
