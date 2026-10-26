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
CLAUDE_SECRET="claude-api-key"
GEMINI_SECRET="gemini-api-key"
GROQ_SECRET="groq-api-key"
TELEGRAM_SECRET="telegram-bot-token"
VALID_AGENTS=("ceo","strategy","compliance","research","creative","analyst")
from claude_provider import DEFAULT_MODELS as CLAUDE_MODELS, VALID_MODELS as CLAUDE_VALID_MODELS
from free_cloud_providers import GEMINI_DEFAULT, GROQ_DEFAULT, GEMINI_MODELS, GROQ_MODELS
VALID_MODELS=("gpt-6.1-sol","gpt-6-luna")
DEFAULT_MODELS={"ceo":"gpt-6.1-sol","strategy":"gpt-6.1-sol",
 "compliance":"gpt-6.1-sol","research":"gpt-6-luna",
 "creative":"gpt-6-luna","analyst":"gpt-6-luna"}
DEFAULT={"openai_agents":[],"openai_models":DEFAULT_MODELS,"monthly_limit_usd":12.0,
         "telegram_allowed_ids":[],"telegram_autostart":False,
         "agent_providers":{a:"auto" for a in VALID_AGENTS},
         "provider_priority":["gemini","groq","claude","openai","ollama"],
         "allow_paid_fallback":False,"free_only":True,
         "gemini_models":GEMINI_DEFAULT,"groq_models":GROQ_DEFAULT,
         "claude_models":CLAUDE_MODELS,"claude_monthly_limit_usd":12.0}


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
    if name not in (OPENAI_SECRET,CLAUDE_SECRET,GEMINI_SECRET,GROQ_SECRET,TELEGRAM_SECRET):
        raise ValueError("Loại khóa không hợp lệ")
    if not isinstance(value,str):
        raise ValueError("Khóa phải là văn bản")
    val=value.strip()
    if not val or len(val)>4096 or any(x in val for x in "\r\n\x00 "):
        raise ValueError("Khóa không hợp lệ (không được có khoảng trắng hoặc xuống dòng)")
    keyring_backend().set_password(SERVICE,name,val)


def delete_secret(name):
    if name not in (OPENAI_SECRET,CLAUDE_SECRET,GEMINI_SECRET,GROQ_SECRET,TELEGRAM_SECRET):
        raise ValueError("Loại khóa không hợp lệ")
    kr=keyring_backend()
    try: kr.delete_password(SERVICE,name)
    except Exception:
        if kr.get_password(SERVICE,name):
            raise


def read():
    config={**DEFAULT,"openai_models":dict(DEFAULT_MODELS),
            "claude_models":dict(CLAUDE_MODELS),"agent_providers":dict(DEFAULT["agent_providers"]),
            "gemini_models":dict(GEMINI_DEFAULT),"groq_models":dict(GROQ_DEFAULT),
            "provider_priority":list(DEFAULT["provider_priority"])}
    if SETTINGS.exists():
        try:
            saved=json.loads(SETTINGS.read_text(encoding="utf-8"))
            if isinstance(saved,dict):
                for field in ("openai_agents","openai_models","monthly_limit_usd",
                              "telegram_allowed_ids","telegram_autostart","agent_providers",
                              "claude_models","claude_monthly_limit_usd",
                              "gemini_models","groq_models","provider_priority","allow_paid_fallback","free_only"):
                    if field in saved:config[field]=saved[field]
        except (OSError,ValueError):
            raise RuntimeError("Không đọc được cấu hình tích hợp; cần kiểm tra tệp integrations.local.json.")
        if "agent_providers" not in saved:
            # Existing v2 installs retain their previously selected OpenAI agents.
            config["agent_providers"]={a:("openai" if a in config["openai_agents"] else "ollama")
                                       for a in VALID_AGENTS}
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
    for a in VALID_AGENTS:
        if a in agents:d["agent_providers"][a]="openai"
        elif d["agent_providers"].get(a)=="openai":d["agent_providers"][a]="ollama"
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
        "agent_providers":d["agent_providers"],
        "claude_models":d["claude_models"],
        "claude_monthly_limit_usd":d["claude_monthly_limit_usd"],
        "claude_key_configured":has_secret(CLAUDE_SECRET),
        "gemini_key_configured":has_secret(GEMINI_SECRET),
        "groq_key_configured":has_secret(GROQ_SECRET),
        "gemini_models":d["gemini_models"],
        "groq_models":d["groq_models"],
        "provider_priority":d["provider_priority"],
        "allow_paid_fallback":d["allow_paid_fallback"],
        "free_only":d["free_only"],
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
    env["ANTHROPIC_API_KEY"]=_get(CLAUDE_SECRET)
    env["GEMINI_API_KEY"]=_get(GEMINI_SECRET)
    env["GROQ_API_KEY"]=_get(GROQ_SECRET)
    env["TEA_ALLOW_PAID_FALLBACK"]="1" if d["allow_paid_fallback"] else "0"
    env["TEA_FREE_ONLY"]="1" if d["free_only"] else "0"
    env["TEA_PROVIDER_PRIORITY"]=",".join(d["provider_priority"])
    env["TEA_CLAUDE_MONTHLY_LIMIT_USD"]=str(d["claude_monthly_limit_usd"])
    for agent in VALID_AGENTS:
        env["TEA_AGENT_PROVIDER_"+agent.upper()]=d["agent_providers"].get(agent,"ollama")
        env["TEA_CLAUDE_MODEL_"+agent.upper()]=d["claude_models"].get(agent,CLAUDE_MODELS[agent])
        env["TEA_GEMINI_MODEL_"+agent.upper()]=d["gemini_models"].get(agent,GEMINI_DEFAULT[agent])
        env["TEA_GROQ_MODEL_"+agent.upper()]=d["groq_models"].get(agent,GROQ_DEFAULT[agent])
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
    for a in VALID_AGENTS:
        if d["agent_providers"].get(a)=="openai":d["agent_providers"][a]="ollama"
    _write(d)
    delete_secret(OPENAI_SECRET)
    return status()

def remove_telegram_token():
    d=read()
    d["telegram_autostart"]=False
    _write(d)
    delete_secret(TELEGRAM_SECRET)
    return status()

def _limit(value,label):
    try: v=float(value)
    except (TypeError,ValueError):raise ValueError("Ngân sách "+label+" phải là một số USD hợp lệ")
    if not 0 < v <= 1000:raise ValueError("Ngân sách "+label+" phải lớn hơn 0 và không quá 1000 USD")
    return v

def save_ai_providers(body):
    """Single GUI form: user explicitly chooses a provider for each agent."""
    providers=body.get("agent_providers",{})
    if not isinstance(providers,dict) or any(x not in VALID_AGENTS for x in providers):
        raise ValueError("Danh sách vị trí AI không hợp lệ")
    if any(providers.get(a,"auto") not in ("auto","gemini","groq","ollama","openai","claude") for a in VALID_AGENTS):
        raise ValueError("Nhà cung cấp AI không hợp lệ")
    o_models=body.get("openai_models",{})
    c_models=body.get("claude_models",{})
    if not isinstance(o_models,dict) or not isinstance(c_models,dict):
        raise ValueError("Cấu hình model không hợp lệ")
    g_models=body.get("gemini_models",{})
    q_models=body.get("groq_models",{})
    if not isinstance(g_models,dict) or not isinstance(q_models,dict):
        raise ValueError("Cấu hình model Gemini/Groq không hợp lệ")
    selected_gemini={a:g_models.get(a,GEMINI_DEFAULT[a]) for a in VALID_AGENTS}
    selected_groq={a:q_models.get(a,GROQ_DEFAULT[a]) for a in VALID_AGENTS}
    if any(v not in GEMINI_MODELS for v in selected_gemini.values()):
        raise ValueError("Model Gemini không được hỗ trợ")
    if any(v not in GROQ_MODELS for v in selected_groq.values()):
        raise ValueError("Model Groq không được hỗ trợ")
    priority=body.get("provider_priority",list(DEFAULT["provider_priority"]))
    expected=set(DEFAULT["provider_priority"])
    if not isinstance(priority,list) or len(priority)!=len(expected) or set(priority)!=expected:
        raise ValueError("Danh sách ưu tiên AI phải chứa mỗi nhà cung cấp đúng một lần")
    allow_paid=body.get("allow_paid_fallback",False)
    if type(allow_paid) is not bool:
        raise ValueError("Chế độ dự phòng trả phí phải là đúng/sai")
    free_only=body.get("free_only",True)
    if type(free_only) is not bool:
        raise ValueError("Chế độ chỉ model có gói miễn phí phải là đúng/sai")
    if free_only and (allow_paid or any(providers.get(a,"auto") in ("claude","openai") for a in VALID_AGENTS)):
        raise ValueError("Đang chọn CHỈ MODEL CÓ GÓI MIỄN PHÍ; không thể dùng Claude/OpenAI API trả phí. Hãy bỏ chế độ này nếu thật sự muốn dùng trả phí.")
    selected_openai={a:o_models.get(a,DEFAULT_MODELS[a]) for a in VALID_AGENTS}
    selected_claude={a:c_models.get(a,CLAUDE_MODELS[a]) for a in VALID_AGENTS}
    if any(v not in VALID_MODELS for v in selected_openai.values()):
        raise ValueError("Model OpenAI không hỗ trợ")
    if any(v not in CLAUDE_VALID_MODELS for v in selected_claude.values()):
        raise ValueError("Model Claude không hỗ trợ")
    openai_limit=_limit(body.get("monthly_limit_usd",12),"OpenAI")
    claude_limit=_limit(body.get("claude_monthly_limit_usd",12),"Claude")
    g_key=body.get("gemini_api_key","") or ""
    q_key=body.get("groq_api_key","") or ""
    o_key=body.get("openai_api_key","") or ""
    c_key=body.get("claude_api_key","") or ""
    if g_key:set_secret(GEMINI_SECRET,g_key)
    if q_key:set_secret(GROQ_SECRET,q_key)
    if o_key:set_secret(OPENAI_SECRET,o_key)
    if c_key:set_secret(CLAUDE_SECRET,c_key)
    final={a:providers.get(a,"auto") for a in VALID_AGENTS}
    if "gemini" in final.values() and not has_secret(GEMINI_SECRET):
        raise ValueError("Hãy lưu Gemini API key để chọn Gemini trực tiếp.")
    if "groq" in final.values() and not has_secret(GROQ_SECRET):
        raise ValueError("Hãy lưu Groq API key để chọn Groq trực tiếp.")
    if "openai" in final.values() and not has_secret(OPENAI_SECRET):
        raise ValueError("Muốn dùng OpenAI, hãy nhập và lưu API key trước.")
    if "claude" in final.values() and not has_secret(CLAUDE_SECRET):
        raise ValueError("Muốn dùng Claude, hãy nhập và lưu Anthropic API key trước.")
    d=read()
    d.update(agent_providers=final,openai_agents=[a for a in VALID_AGENTS if final[a]=="openai"],
             openai_models=selected_openai,claude_models=selected_claude,
             gemini_models=selected_gemini,groq_models=selected_groq,
             provider_priority=priority,allow_paid_fallback=allow_paid,free_only=free_only,
             monthly_limit_usd=openai_limit,claude_monthly_limit_usd=claude_limit)
    _write(d)
    return status()

def remove_claude_key():
    d=read()
    for a in VALID_AGENTS:
        if d["agent_providers"].get(a)=="claude":
            d["agent_providers"][a]="ollama"
    _write(d)
    delete_secret(CLAUDE_SECRET)
    return status()

def remove_gemini_key():
    d=read()
    for a in VALID_AGENTS:
        if d["agent_providers"].get(a)=="gemini":
            d["agent_providers"][a]="auto"
    _write(d)
    delete_secret(GEMINI_SECRET)
    return status()

def remove_groq_key():
    d=read()
    for a in VALID_AGENTS:
        if d["agent_providers"].get(a)=="groq":
            d["agent_providers"][a]="auto"
    _write(d)
    delete_secret(GROQ_SECRET)
    return status()

def test_gemini(http=None, key_override=None):
    """Read-only API-key test. A pasted unsaved key is tested without persistence."""
    from free_cloud_providers import test_gemini as call_test
    if key_override is not None:
        if not isinstance(key_override,str) or len(key_override)>4096:
            raise ValueError("Định dạng Gemini API key không hợp lệ")
        key=key_override.strip() or _get(GEMINI_SECRET)
    else:
        key=_get(GEMINI_SECRET)
    return call_test(key,transport=http)

def test_groq(http=None, key_override=None):
    """Test a pasted key without saving it; otherwise use the Windows vault."""
    from free_cloud_providers import test_groq as call_test
    if key_override is not None:
        if not isinstance(key_override,str) or len(key_override)>4096:
            raise ValueError("Định dạng Groq API key không hợp lệ")
        key=key_override.strip() or _get(GROQ_SECRET)
    else:
        key=_get(GROQ_SECRET)
    return call_test(key,transport=http)

def test_groq_chat(http=None,key_override=None):
    """Live test is user-initiated only and uses the same key as the list test."""
    from free_cloud_providers import test_groq_chat as call_test
    if key_override is not None:
        if not isinstance(key_override,str) or len(key_override)>4096:
            raise ValueError("Định dạng Groq API key không hợp lệ")
        key=key_override.strip() or _get(GROQ_SECRET)
    else:
        key=_get(GROQ_SECRET)
    return call_test(key,transport=http)


def test_claude(http=None):
    """Anthropic models.list is a read-only authentication and availability test."""
    key=_get(CLAUDE_SECRET)
    if not key:raise ValueError("Hãy lưu Claude API key trước khi kiểm tra")
    request=Request("https://api.anthropic.com/v1/models?limit=100",
       headers={"x-api-key":key,"anthropic-version":"2023-06-01","accept":"application/json"})
    try:
        if http is None:
            with urlopen(request,timeout=10) as response:
                content=json.loads(response.read(300000).decode("utf-8"))
        else:content=http(request)
    except HTTPError as ex:
        raise ValueError("Claude API trả về HTTP "+str(ex.code)+". Kiểm tra key và quyền truy cập.") from None
    except (URLError,TimeoutError,OSError):
        raise ValueError("Không thể kết nối Claude API. Kiểm tra Internet.") from None
    if not isinstance(content,dict) or not isinstance(content.get("data"),list):
        raise ValueError("Claude API trả về danh sách model không hợp lệ")
    found={str(x.get("id","")) for x in content["data"] if isinstance(x,dict)}
    d=read()
    selected={d["claude_models"][a] for a in VALID_AGENTS if d["agent_providers"].get(a)=="claude"}
    return {"ok":True,
            "message":"Claude API đã chấp nhận khóa. Chưa tạo câu trả lời có tính phí.",
            "unlisted_models":sorted(selected-found)}

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
