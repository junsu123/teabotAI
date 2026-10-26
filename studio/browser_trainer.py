"""Operator-controlled click/field metadata recorder (no form values or secrets).

Only started through the local GUI after the operator chooses a profile.
Does not publish, replay interactions, bypass login challenges or extract cookies.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import time
from datetime import datetime
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'legacy'/'tea_ai_local'))
from shop_profiles import account_context, get_account, scan_page
TRAIN=ROOT/'data'/'training'
RECORDER=r'''(() => {
 if (window.__teaRecorderInstalled) return;
 window.__teaRecorderInstalled=true;
 const privateRe=/(password|passcode|otp|secret|auth|token|cookie|2fa|mật khẩu|xác minh|số điện thoại|phone|e-?mail|đăng nhập|log ?in|sign ?in)/i;
 function send(ev){
  if (!window.teaRecordEvent || !ev.isTrusted) return;
  let element=ev.target;
  if (!element || !element.closest) return;
  element=element.closest('input,textarea,select,button,[role="button"],[role="textbox"],[contenteditable="true"],label');
  if (!element) return;
  const type=(element.getAttribute('type')||'').toLowerCase();
  if (['password','hidden','email','tel'].includes(type)) return;
  const o={action:ev.type,tag:element.tagName.toLowerCase(),type,
    id:(element.id||'').slice(0,120), name:(element.getAttribute('name')||'').slice(0,120),
    placeholder:(element.getAttribute('placeholder')||'').slice(0,120),
    aria_label:(element.getAttribute('aria-label')||'').slice(0,120),
    test_id:(element.getAttribute('data-testid')||'').slice(0,120),
    role:(element.getAttribute('role')||'').slice(0,120),
    label:Array.from(element.labels||[]).map(x=>x.innerText.trim().slice(0,120)).join(' | '),
    text:element.tagName.toLowerCase()==='button'?(element.innerText||'').trim().slice(0,80):''};
  if(privateRe.test(Object.values(o).join(' ')))return;
  try {window.teaRecordEvent(o).catch(()=>{});}catch(_){}
 }
 document.addEventListener('click',send,true);
 document.addEventListener('change',send,true);
})();'''

def write_status(session,**fields):
 path=TRAIN/(session+'.status.json')
 try:d=json.loads(path.read_text(encoding='utf-8'))
 except Exception:d={'id':session}
 d.update(fields)
 path.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')

def main():
 parser=argparse.ArgumentParser()
 parser.add_argument('--account',required=True);parser.add_argument('--mode',choices=('new','update'),required=True)
 parser.add_argument('--target',choices=('demo','seller'),required=True)
 parser.add_argument('--session',required=True)
 args=parser.parse_args()
 if not len(args.session)==16 or not all(x in '0123456789abcdef' for x in args.session):return
 TRAIN.mkdir(parents=True,exist_ok=True)
 events=TRAIN/(args.session+'.events.jsonl')
 stop=TRAIN/(args.session+'.stop')
 a=get_account(args.account)
 allowed_host=urlparse(a['start_url']).hostname
 try:
  from playwright.sync_api import sync_playwright
  with sync_playwright() as p:
   with account_context(p,args.account) as ctx:
    def handler(source,payload):
     if not isinstance(payload,dict):return
     url=source['frame'].url
     parsed=urlparse(url)
     if args.target=='seller':
      if parsed.hostname != allowed_host:return
     elif parsed.scheme!='file':return
     safe={k:str(payload.get(k,''))[:120] for k in (
       'action','tag','type','id','name','placeholder','aria_label','test_id','role','label','text')}
     safe['when']=datetime.now().astimezone().isoformat(timespec='seconds')
     safe['host']=parsed.hostname or 'local_demo'
     with events.open('a',encoding='utf-8') as f:f.write(json.dumps(safe,ensure_ascii=False)+'\n')
    ctx.expose_binding('teaRecordEvent',handler)
    ctx.add_init_script(script=RECORDER)
    page=ctx.pages[0] if ctx.pages else ctx.new_page()
    if args.target=='demo':
     url=(ROOT.parent/'legacy'/'tea_ai_local'/'demo_product_form.html').resolve().as_uri()
    else:url=a['start_url']
    page.goto(url,wait_until='domcontentloaded',timeout=60000)
    # Ensure listeners are in this first page, even if the init-script ran very early.
    page.evaluate(RECORDER)
    write_status(args.session,status='recording',message='Đang ghi thao tác, không ghi nội dung bạn nhập')
    t0=time.time()
    while not stop.exists() and time.time()-t0<2*60*60:
     time.sleep(0.6)
    write_status(args.session,status='saving',message='Đang lưu DOM và các bước')
    fields=[]
    try:
     for p in ctx.pages:
      if not p.is_closed():
       fields+=scan_page(p)
    except Exception:pass
    steps=[json.loads(x) for x in events.read_text(encoding='utf-8').splitlines() if x.strip()] if events.exists() else []
    # No raw form values, passwords, screenshots, cookies or full HTML stored.
    result={'account_id':args.account,'mode':args.mode,'target':args.target,
       'source':'operator_recorded_dom_metadata','reviewed':False,
       'fields':fields[:250],'steps':steps[:500],
       'note':'Người dùng phải duyệt selector trước khi dùng lại; phần mềm không phát lại thao tác đăng.'}
    (TRAIN/(args.session+'.result.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    write_status(args.session,status='completed',message=f'Đã lưu {len(steps)} thao tác và {len(fields)} trường DOM')
 except Exception as exc:
  write_status(args.session,status='failed',message=f'{type(exc).__name__}: {str(exc)[:200]}')
 finally:
  stop.unlink(missing_ok=True)

if __name__=='__main__':main()
