"""Anthropic Claude Messages API adapter for Mars Studio.

This is used ONLY after explicit activation in the local GUI and requires an
Anthropic API key stored in Windows Credential Manager via integration_settings.
It does not execute external actions or expose user login credentials.
"""
from __future__ import annotations
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

VALID_MODELS = ("claude-sonnet-4-6", "claude-opus-4-6", "claude-haiku-4-5")
MODEL_PRICES = {  # Standard USD per million uncached input/output tokens.
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-opus-4-6": (5.0, 25.0),
    "claude-haiku-4-5": (1.0, 5.0),
}
DEFAULT_MODELS = {
    "ceo": "claude-sonnet-4-6",
    "strategy": "claude-sonnet-4-6",
    "compliance": "claude-sonnet-4-6",
    "research": "claude-sonnet-4-6",
    "creative": "claude-haiku-4-5",
    "analyst": "claude-haiku-4-5",
}
API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"


def usd(model, input_tokens, output_tokens):
    a,b=MODEL_PRICES[model]
    return (max(0,int(input_tokens))*a + max(0,int(output_tokens))*b)/1_000_000


def connection(db_file):
    path=Path(db_file)
    path.parent.mkdir(parents=True,exist_ok=True)
    c=sqlite3.connect(path,timeout=15)
    c.execute("PRAGMA busy_timeout=15000")
    c.execute("""CREATE TABLE IF NOT EXISTS claude_usage(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      month TEXT NOT NULL, agent TEXT NOT NULL, model TEXT NOT NULL,
      input_tokens INTEGER NOT NULL, output_tokens INTEGER NOT NULL,
      estimated_usd REAL NOT NULL, created_at TEXT NOT NULL)""")
    return c


def usage_month(db_file):
    month=datetime.now(timezone.utc).strftime("%Y-%m")
    with connection(db_file) as c:
        row=c.execute("""SELECT COUNT(*),COALESCE(SUM(estimated_usd),0)
          FROM claude_usage WHERE month=?""",(month,)).fetchone()
    return {"month":month,"calls":int(row[0]),"estimated_usd":round(row[1],5)}


def call(agent,prompt,db_file,*,key,model,limit_usd=12.0,transport=None):
    if model not in VALID_MODELS:
        raise ValueError("Mô hình Claude không được hỗ trợ")
    if not isinstance(key,str) or not key.strip():
        raise RuntimeError("Chưa cấu hình Claude API key trong phần mềm")
    cap=float(limit_usd)
    if not 0 < cap <= 1000:
        raise ValueError("Ngân sách Claude USD phải lớn hơn 0 và không quá 1000")
    # Local estimate only; it is NOT a provider-enforced spending cap.
    current=usage_month(db_file)
    max_tokens=1250
    preflight=usd(model,max(1,len(str(prompt))//2),max_tokens)
    if current["estimated_usd"]+preflight > cap:
        raise RuntimeError("Claude đã gần ngưỡng chi phí ước tính tháng này. Kiểm tra ngân sách trước khi tiếp tục.")
    from main import AGENTS
    from model_router import VIETNAMESE_RULES
    system=AGENTS[agent]+"\n"+VIETNAMESE_RULES
    payload={"model":model,"max_tokens":max_tokens,"system":system,
             "messages":[{"role":"user","content":str(prompt)[:20000]}]}
    request=Request(API_URL,
        data=json.dumps(payload,ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={"x-api-key":key,"anthropic-version":API_VERSION,
                 "content-type":"application/json","accept":"application/json"})
    try:
        if transport is None:
            with urlopen(request,timeout=100) as response:
                result=json.loads(response.read(2_000_000).decode("utf-8"))
        else:
            result=transport(request)
    except HTTPError as error:
        raise RuntimeError("Claude API từ chối yêu cầu (HTTP "+str(error.code)+"). Kiểm tra key, model và hạn mức.") from None
    except (URLError,TimeoutError,OSError) as error:
        raise RuntimeError("Không thể kết nối Anthropic Claude API. Kiểm tra mạng và thử lại.") from None
    if not isinstance(result,dict):
        raise RuntimeError("Claude API trả về dữ liệu không hợp lệ")
    texts=[c.get("text","") for c in result.get("content",[])
           if isinstance(c,dict) and c.get("type")=="text" and isinstance(c.get("text"),str)]
    answer="\n".join(texts).strip()
    if not answer:
        raise RuntimeError("Claude API không trả về văn bản. Kiểm tra tài khoản hoặc max_tokens.")
    usage=result.get("usage",{}) or {}
    input_tokens=int(usage.get("input_tokens",0) or 0)
    output_tokens=int(usage.get("output_tokens",0) or 0)
    cost=usd(model,input_tokens,output_tokens)
    at=datetime.now(timezone.utc).isoformat(timespec="seconds")
    with connection(db_file) as c:
        c.execute("""INSERT INTO claude_usage
          (month,agent,model,input_tokens,output_tokens,estimated_usd,created_at)
          VALUES (?,?,?,?,?,?,?)""",
          (at[:7],agent,model,input_tokens,output_tokens,cost,at))
    return answer
