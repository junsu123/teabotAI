"""Local integration settings owned by Mars Studio.

Sensitive OpenAI keys and Telegram tokens live in the OS credential store (keyring).
Only non-sensitive settings live in a private JSON file under studio/data.
No raw secrets are returned by the web interface or logged.
"""
from __future__ import annotations
import json
import os
import re
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import quote

ROOT=Path(__file__).resolve().parent
SETTINGS=ROOT/"data"/"integrations.local.json"
SERVICE="tea-ai-mars-integrations-v1"
OPENAI_SECRET="openai-api-key"
TELEGRAM_SECRET="telegram-bot-token"
VALID_AGENTS=("ceo","strategy","compliance","research","creative","analyst")
VALID_MODELS=("gpt-6.1-sol","gpt-6-luna")
DEFAULT_MODELS={"ceo":"gpt-6.1-sol","strategy":"gpt-6.1-sol",
 "compliance":"gpt-6.1-sol","research":"gpt-6-luna",
 "creative":"gpt-6-luna","analyst":"gpt-6-luna"}
DEFAULT={"openai_agents":[],"openai_models":DEFAULT_MODELS,"monthly_limit_usd":12.0,
         "telegram_allowed_ids":[],"telegram_autostart":False}


def keyring_backend():
    try:
        import keyring
        from keyring.backends.fail import Keyring as FailKeyring
        backend=keyring.get_keyring()
        if isinstance(backend,FailKeyring) or backend.priority <= 0:
            raise RuntimeError("Không có kho mật khẩu hệ điều hành khả dụng. Hãy chạy setup_windows.bat.")
        return keyring
    except ImportError as ex:
        raise RuntimeError("Cần cài keyring bằng setup_windows.bat trước.") from ex


def _get(name):
    try:
        return keyring_backend().get_password(SERVICE,name) or ""
    except Exception:
        # Status views must never crash the dashboard just because keyring is unavailable.
        return ""


def has_secret(name):
    return bool(_get(name))


def set_secret(name,value):
    if name not in (OPENAI_SECRET,TELEGRAM_SECRET):
        raise ValueError("Loại khóa không hợp lệ")
    if not isinstance(value,str):
        raise ValueError("Khóa phải là văn bản")
    val=value.strip()
    if not val or len(val)>4096 or any(x in val for x in "\r\n\x00 "):
        raise ValueError("Khóa không hợp lệ (không được có khoảng trắng hoặc xuống dòng)")
    keyring_backend().set_password(SERVICE,name,val)


def delete_secret(name):
    if name not in (OPENAI_SECRET,TELEGRAM_SECRET):
        raise ValueError("Loại khóa không hợp lệ")
    kr=keyring_backend()
    try: kr.delete_password(SERVICE,name)
    except Exception:
        if kr.get_password(SERVICE,name):
            raise


def read():
    config={**DEFAULT,"openai_models":dict(DEFAULT_MODELS)}
    if SETTINGS.exists():
        try:
            saved=json.loads(SETTINGS.read_text(encoding="utf-8"))
            if isinstance(saved,dict):
                for field in ("openai_agents","openai_models","monthly_limit_usd",
                              "telegram_allowed_ids","telegram_autostart"):
                    if field in saved:config[field]=saved[field]
        except (OSError,ValueError):
            raise RuntimeError("Không đọc được cấu hình tích hợp; cần kiểm tra tệp integrations.local.json.")
    return config


def _write(d):
    SETTINGS.parent.mkdir(parents=True,exist_ok=True)
    fd,path=tempfile.mkstemp(prefix="integrations-",suffix=".tmp",dir=SETTINGS.parent)
    try:
        if os.name!="nt":os.fchmod(fd,0o600)
        with os.fdopen(fd,"w",encoding="utf-8") as file:
            json.dump(d,file,ensure_ascii=False,indent=2)
        os.replace(path,SETTINGS)
    finally:
        if os.path.exists(path):os.unlink(path)


def parse_ids(input_value):
    if isinstance(input_value,list):
        tokens=[str(x).strip() for x in input_value]
    elif isinstance(input_value,str):
        tokens=[x.strip() for x in input_value.split(",") if x.strip()]
    else:
        raise ValueError("Telegram User ID cần là số, phân cách bằng dấu phẩy")
    if len(tokens)>20 or any(not re.fullmatch(r"[1-9][0-9]{4,19}",x) for x in tokens):
        raise ValueError("Telegram User ID phải là số dương (5–20 chữ số), tối đa 20 ID")
    return list(dict.fromkeys(tokens))


def save_openai(body):
    agents=body.get("openai_agents",[])
    if not isinstance(agents,list) or any(a not in VALID_AGENTS for a in agents):
        raise ValueError("Danh sách agent OpenAI không hợp lệ")
    agents=list(dict.fromkeys(agents))
    models=body.get("openai_models",{})
    if not isinstance(models,dict):
        raise ValueError("Cấu hình model không hợp lệ")
    selected={a:models.get(a,DEFAULT_MODELS[a]) for a in VALID_AGENTS}
    if any(v not in VALID_MODELS for v in selected.values()):
        raise ValueError("Chỉ cho phép model OpenAI đã hỗ trợ trong phần mềm")
    try: limit=float(body.get("monthly_limit_usd",12))
    except (TypeError,ValueError):raise ValueError("Ngân sách USD không hợp lệ")
    if not 0<limit<=1000:raise ValueError("Ngân sách cần lớn hơn 0 và tối đa 1000 USD")
    secret=body.get("api_key","")
    if secret: set_secret(OPENAI_SECRET,secret)
    if agents and not has_secret(OPENAI_SECRET):
        raise ValueError("Hãy nhập và lưu OpenAI API key trước khi bật agent")
    d=read()
    d.update(openai_agents=agents,openai_models=selected,monthly_limit_usd=limit)
    _write(d)
    return status()


def save_telegram(body):
    ids=parse_ids(body.get("telegram_allowed_ids",[]))
    autostart=body.get("telegram_autostart",False)
    if type(autostart) is not bool:raise ValueError("Tự chạy Telegram phải là true/false")
    secret=body.get("bot_token","")
    if secret: set_secret(TELEGRAM_SECRET,secret)
    d=read()
    d.update(telegram_allowed_ids=ids,telegram_autostart=autostart)
    _write(d)
    return status()


def status():
    d=read()
    return {
        "openai_agents":d["openai_agents"],
        "openai_models":d["openai_models"],
        "monthly_limit_usd":d["monthly_limit_usd"],
        "openai_key_configured":has_secret(OPENAI_SECRET),
        "telegram_token_configured":has_secret(TELEGRAM_SECRET),
        "telegram_allowed_ids":d["telegram_allowed_ids"],
        "telegram_autostart":d["telegram_autostart"],
        # Never expose keys, token or secret previews.
    }


def openai_env(base=None):
    """Model router accepts a mapping; GUI settings have precedence over legacy env vars."""
    base=os.environ if base is None else base
    env=dict(base)
    d=read()
    env["TEA_OPENAI_AGENTS"]=",".join(d["openai_agents"])
    env["TEA_OPENAI_MONTHLY_LIMIT_USD"]=str(d["monthly_limit_usd"])
    for agent,model in d["openai_models"].items():
        env["TEA_OPENAI_MODEL_"+agent.upper()]=model
    env["OPENAI_API_KEY"]=_get(OPENAI_SECRET)
    return env


def telegram_env():
    d=read()
    token=_get(TELEGRAM_SECRET)
    if not token:
        raise ValueError("Chưa lưu Telegram Bot Token")
    # Bootstrap: without authorized IDs only /myid is accessible.
    # Every operational command remains blocked by the bot allowlist.
    return {"TEA_TELEGRAM_TOKEN":token,
            "TEA_TELEGRAM_ALLOWED_IDS":",".join(d["telegram_allowed_ids"])}



def remove_openai_key():
    d=read()
    d["openai_agents"]=[]
    _write(d)
    delete_secret(OPENAI_SECRET)
    return status()

def remove_telegram_token():
    d=read()
    d["telegram_autostart"]=False
    _write(d)
    delete_secret(TELEGRAM_SECRET)
    return status()

def test_openai(http=None):
    """Read-only models listing; no token generation or billed inference."""
    key=_get(OPENAI_SECRET)
    if not key:raise ValueError("Hãy lưu OpenAI API key trước khi kiểm tra")
    request=Request("https://api.openai.com/v1/models",
                    headers={"Authorization":"Bearer "+key,"Accept":"application/json"})
    try:
        if http is None:
            with urlopen(request,timeout=9) as r:
                content=json.loads(r.read(200000).decode("utf-8"))
        else:content=http(request)
    except HTTPError as e:
        raise ValueError("OpenAI từ chối kết nối (HTTP "+str(e.code)+"). Kiểm tra API key/quyền truy cập.") from None
    except (URLError,TimeoutError,OSError) as e:
        raise ValueError("Không thể kết nối OpenAI. Kiểm tra mạng và thử lại.") from None
    if not isinstance(content,dict) or not isinstance(content.get("data"),list):
        raise ValueError("Phản hồi OpenAI không hợp lệ")
    models={str(x.get("id","")) for x in content["data"] if isinstance(x,dict)}
    selected={d["openai_models"][a] for a in d["openai_agents"]} if (d:=read()) else set()
    missing=sorted(selected-models)
    return {"ok":True,"message":"API key được OpenAI chấp nhận; chưa gọi mô hình tính phí.",
            "unlisted_models":missing}


def test_telegram(http=None):
    """Read-only Telegram getMe, never echo secret token in errors."""
    token=_get(TELEGRAM_SECRET)
    if not token:raise ValueError("Hãy lưu Telegram Bot Token trước khi kiểm tra")
    # Telegram Bot API token is unavoidably part of Bot API URL; it is never logged.
    url="https://api.telegram.org/bot"+quote(token,safe=":")+"/getMe"
    request=Request(url,headers={"Accept":"application/json"})
    try:
        if http is None:
            with urlopen(request,timeout=9) as r:
                content=json.loads(r.read(150000).decode("utf-8"))
        else:content=http(request)
    except HTTPError as e:
        raise ValueError("Telegram không chấp nhận token (HTTP "+str(e.code)+").") from None
    except (URLError,TimeoutError,OSError):
        raise ValueError("Không thể kết nối Telegram, kiểm tra mạng và thử lại.") from None
    if not isinstance(content,dict) or content.get("ok") is not True:
        raise ValueError("Token Telegram không hợp lệ hoặc Bot API từ chối yêu cầu")
    bot=content.get("result") or {}
    return {"ok":True,"bot_username":str(bot.get("username",""))[:100],
            "message":"Đã xác minh Bot Token với Telegram (getMe)."}
