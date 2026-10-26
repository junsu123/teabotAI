"""Explicit opt-in OpenAI Responses API router for the Mars Studio agents.

All local by default. No OpenAI request unless the operator sets
TEA_OPENAI_AGENTS and OPENAI_API_KEY deliberately.
No marketplace API calls, tool execution or cookie access.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

VALID_AGENTS = frozenset({"ceo","research","strategy","creative","analyst","compliance"})
DEFAULT_MODELS = {
    "ceo": "gpt-6.1-sol",
    "strategy": "gpt-6.1-sol",
    "compliance": "gpt-6.1-sol",
    "research": "gpt-6-luna",
    "creative": "gpt-6-luna",
    "analyst": "gpt-6-luna",
}
# Approximate standard text prices in USD per million tokens, current at integration.
# Not an invoice, not a hard budget guarantee; provider rates may change.
PRICES = {
    "gpt-6.1-sol": (2.0, 10.0),
    "gpt-6-luna": (0.1, 0.5),
}
VIETNAMESE_RULES = (
    "Ngôn ngữ bắt buộc: TIẾNG VIỆT. Viết 100% phần diễn giải, câu hỏi, "
    "phản biện, ý kiến và kết luận bằng tiếng Việt tự nhiên, đủ dấu. "
    "Chỉ giữ nguyên tên riêng, mã kỹ thuật, URL, tên model và tên trường JSON. "
    "Nếu cần xuất JSON, giữ khóa JSON theo yêu cầu, nhưng giá trị giải thích phải bằng tiếng Việt. "
    "Mọi tuyên bố thực tế cần phân biệt dữ liệu được xác minh và giả thuyết. "
    "Không bịa nguồn, số liệu, doanh thu, công dụng y tế hay hành động đã thực hiện. "
    "Chỉ AI CEO có quyền chốt phương án. Không tự đăng hàng, chi tiền hoặc thay đổi gian hàng. "
    "Mọi nhân viên chỉ báo cáo nội bộ cho AI CEO."
)

def enabled_agents(env=None):
    env = os.environ if env is None else env
    raw = (env.get("TEA_OPENAI_AGENTS") or "").strip().lower()
    if not raw or raw in {"none", "off", "0"}:
        return frozenset()
    items = frozenset(x.strip() for x in raw.split(",") if x.strip())
    invalid = items - VALID_AGENTS
    if invalid:
        raise ValueError("TEA_OPENAI_AGENTS chứa agent không hợp lệ: " + ", ".join(sorted(invalid)))
    return items

def model_for(agent, env=None):
    env = os.environ if env is None else env
    if agent not in VALID_AGENTS:
        raise ValueError("Agent không hợp lệ")
    model = (env.get("TEA_OPENAI_MODEL_" + agent.upper()) or DEFAULT_MODELS[agent]).strip()
    if model not in PRICES:
        raise ValueError("Model chưa được phê duyệt trong bộ định tuyến: " + model)
    return model

def provider_for(agent, env=None):
    if agent not in VALID_AGENTS:
        raise ValueError("Agent không hợp lệ")
    # GUI provider selection overrides old OPENAI_AGENT environment conventions.
    explicit=(env.get("TEA_AGENT_PROVIDER_"+agent.upper()) or "").strip().lower()
    if explicit:
        if explicit not in {"auto","gemini","groq","claude","openai","ollama"}:
            raise ValueError("Nhà cung cấp AI không hợp lệ cho "+agent)
        return explicit
    return "openai" if agent in enabled_agents(env) else "ollama"

def _usage_db(db_file):
    path = Path(db_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=15)
    con.execute("PRAGMA busy_timeout=15000")
    con.execute("""CREATE TABLE IF NOT EXISTS openai_usage(
         id INTEGER PRIMARY KEY AUTOINCREMENT,
         month TEXT NOT NULL, agent TEXT NOT NULL, model TEXT NOT NULL,
         input_tokens INTEGER NOT NULL, output_tokens INTEGER NOT NULL,
         estimated_usd REAL NOT NULL, created_at TEXT NOT NULL)""")
    return con

def usage_month(db_file):
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    with _usage_db(db_file) as con:
        row = con.execute(
            "SELECT COUNT(*),COALESCE(SUM(estimated_usd),0) FROM openai_usage WHERE month=?",
            (month,)).fetchone()
    return {"month": month, "calls": row[0], "estimated_usd": round(row[1], 5)}

def estimate_usd(model, input_tokens, output_tokens):
    inp, out = PRICES[model]
    return (max(0,input_tokens)*inp + max(0,output_tokens)*out) / 1_000_000

def _maximum_budget(env):
    try:
        value = float(env.get("TEA_OPENAI_MONTHLY_LIMIT_USD", "12"))
    except ValueError as exc:
        raise ValueError("Giới hạn ngân sách OpenAI phải là một số USD hợp lệ") from exc
    if not 0 < value <= 1000:
        raise ValueError("Giới hạn ngân sách OpenAI phải lớn hơn 0 và tối đa 1000 USD")
    return value

def _read_text(data):
    chunks = []
    for item in data.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                chunks.append(content["text"])
    return "\n".join(chunks).strip()

def _openai_chat(agent, prompt, db_file, env=None, transport=None):
    env = os.environ if env is None else env
    key = env.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Chưa có OPENAI_API_KEY. OpenAI chưa được kích hoạt; không phát sinh phí.")
    model = model_for(agent, env)
    summary = usage_month(db_file)
    cap = _maximum_budget(env)
    # Conservative preflight reserve for a bounded response, to avoid a new
    # expensive request close to the local limit. This is approximate only.
    max_output = 1600
    projected = estimate_usd(model, max(1,len(prompt)//2), max_output)
    if summary["estimated_usd"] + projected > cap:
        raise RuntimeError("Đã gần giới hạn ngân sách OpenAI trên máy. CEO dừng tác vụ để bạn kiểm tra.")
    from main import AGENTS
    instructions = AGENTS[agent] + "\n" + VIETNAMESE_RULES
    body = {
        "model": model,
        "instructions": instructions,
        "input": str(prompt)[:20000],
        "reasoning": {"effort": "medium" if agent in ("ceo","strategy","compliance") else "low"},
        "max_output_tokens": max_output,
        "store": False,
    }
    data = json.dumps(body,ensure_ascii=False).encode("utf-8")
    req = Request("https://api.openai.com/v1/responses", data=data, method="POST",
                  headers={"Authorization": "Bearer "+key,
                           "Content-Type": "application/json"})
    try:
        if transport is None:
            with urlopen(req, timeout=100) as response:
                result = json.loads(response.read(2_000_000).decode("utf-8"))
        else:
            result = transport(req)
    except HTTPError as error:
        # No response body logging, to avoid secrets or untrusted contents.
        raise RuntimeError("OpenAI API từ chối yêu cầu; mã HTTP: "+str(error.code)) from error
    except (URLError,TimeoutError,OSError) as error:
        raise RuntimeError("Không kết nối được OpenAI API; kiểm tra mạng hoặc tài khoản thanh toán.") from error
    answer = _read_text(result)
    if not answer:
        raise RuntimeError("OpenAI không trả về văn bản. Hãy kiểm tra hạn mức output/model.")
    usage = result.get("usage") or {}
    input_tokens = int(usage.get("input_tokens") or 0)
    output_tokens = int(usage.get("output_tokens") or 0)
    estimated = estimate_usd(model,input_tokens,output_tokens)
    at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with _usage_db(db_file) as con:
        con.execute("""INSERT INTO openai_usage
            (month,agent,model,input_tokens,output_tokens,estimated_usd,created_at)
            VALUES(?,?,?,?,?,?,?)""",
            (at[:7],agent,model,input_tokens,output_tokens,estimated,at))
    return answer

def _priority(env):
    allowed=("gemini","groq","claude","openai","ollama")
    raw=env.get("TEA_PROVIDER_PRIORITY",",".join(allowed))
    items=[x.strip() for x in raw.split(",")]
    if len(items)!=len(allowed) or set(items)!=set(allowed):
        return allowed
    return tuple(items)


def _call_provider(provider,agent,prompt,local_chat,db_file,env,transport=None):
    if provider=="ollama":
        return local_chat(agent, VIETNAMESE_RULES+"\\n\\n"+prompt)
    if provider=="gemini" or provider=="groq":
        import free_cloud_providers as cloud
        key=env.get("GEMINI_API_KEY","") if provider=="gemini" else env.get("GROQ_API_KEY","")
        if provider=="gemini":
            model=env.get("TEA_GEMINI_MODEL_"+agent.upper(),cloud.GEMINI_DEFAULT[agent])
            return cloud.gemini_chat(agent,prompt,key=key,model=model,transport=transport)
        model=env.get("TEA_GROQ_MODEL_"+agent.upper(),cloud.GROQ_DEFAULT[agent])
        return cloud.groq_chat(agent,prompt,key=key,model=model,transport=transport)
    if provider=="claude":
        import claude_provider
        model=env.get("TEA_CLAUDE_MODEL_"+agent.upper(),claude_provider.DEFAULT_MODELS[agent])
        return claude_provider.call(agent,prompt,
            Path(db_file).with_name("claude_usage.sqlite3"),
            key=env.get("ANTHROPIC_API_KEY",""),model=model,
            limit_usd=env.get("TEA_CLAUDE_MONTHLY_LIMIT_USD","12"),transport=transport)
    if provider=="openai":
        return _openai_chat(agent,prompt,db_file,env=env,transport=transport)
    raise ValueError("Nhà cung cấp AI không hợp lệ")


def _available(provider,env):
    secrets={"gemini":"GEMINI_API_KEY","groq":"GROQ_API_KEY",
             "claude":"ANTHROPIC_API_KEY","openai":"OPENAI_API_KEY"}
    if provider=="ollama":return True
    return bool(env.get(secrets[provider]))


def _record_actual_provider(db_file,agent,provider):
    with sqlite3.connect(Path(db_file),timeout=15) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS model_routes(
            id INTEGER PRIMARY KEY AUTOINCREMENT,agent TEXT NOT NULL,
            provider TEXT NOT NULL,created_at TEXT NOT NULL)""")
        con.execute("INSERT INTO model_routes(agent,provider,created_at) VALUES(?,?,datetime('now'))",
                    (agent,provider))


def chat(agent, prompt, local_chat, db_file, env=None, transport=None):
    env=os.environ if env is None else env
    selected=provider_for(agent,env)
    if selected!="auto":
        result=_call_provider(selected,agent,prompt,local_chat,db_file,env,transport)
        _record_actual_provider(db_file,agent,selected)
        return result
    # Free-first auto routing: Gemini → Groq → Ollama.
    # Claude/OpenAI are included only with user's explicit paid-fallback opt-in.
    order=_priority(env)
    paid_allowed=env.get("TEA_ALLOW_PAID_FALLBACK","0")=="1"
    errors=[]
    for provider in order:
        if provider in ("claude","openai") and not paid_allowed:
            continue
        if not _available(provider,env):
            continue
        try:
            result=_call_provider(provider,agent,prompt,local_chat,db_file,env,transport)
            _record_actual_provider(db_file,agent,provider)
            return result
        except Exception as err:
            import free_cloud_providers as cloud
            # Fallback ONLY if a provider is temporarily unavailable.
            # Credential/permissions errors are surfaced rather than hidden.
            if isinstance(err,cloud.TemporaryProviderError):
                errors.append(provider+": tạm thời không sẵn sàng")
                continue
            raise
    raise RuntimeError("Không nhà cung cấp AI nào phản hồi được trong tuyến ưu tiên. "+
                       "; ".join(errors)[:450])


def configuration_status(env=None):
    env=os.environ if env is None else env
    import claude_provider
    import free_cloud_providers as cloud
    routes={}
    order=_priority(env)
    for agent in sorted(VALID_AGENTS):
        provider=provider_for(agent,env)
        if provider=="claude":
            model=env.get("TEA_CLAUDE_MODEL_"+agent.upper(),claude_provider.DEFAULT_MODELS[agent])
        elif provider=="openai":
            model=model_for(agent,env)
        elif provider=="gemini":
            model=env.get("TEA_GEMINI_MODEL_"+agent.upper(),cloud.GEMINI_DEFAULT[agent])
        elif provider=="groq":
            model=env.get("TEA_GROQ_MODEL_"+agent.upper(),cloud.GROQ_DEFAULT[agent])
        elif provider=="auto":
            model=" → ".join(p for p in order if p not in ("claude","openai")
                           or env.get("TEA_ALLOW_PAID_FALLBACK")=="1")
        else:model=""
        routes[agent]={"provider":provider,"model":model}
    return {"language":"vi",
       "priority":list(order),
       "allow_paid_fallback":env.get("TEA_ALLOW_PAID_FALLBACK","0")=="1",
       "openai_agents":[a for a,x in routes.items() if x["provider"]=="openai"],
       "claude_agents":[a for a,x in routes.items() if x["provider"]=="claude"],
       "auto_agents":[a for a,x in routes.items() if x["provider"]=="auto"],
       "routes":routes,
       "gemini_key_configured":bool(env.get("GEMINI_API_KEY")),
       "groq_key_configured":bool(env.get("GROQ_API_KEY")),
       "openai_key_configured":bool(env.get("OPENAI_API_KEY")),
       "claude_key_configured":bool(env.get("ANTHROPIC_API_KEY")),
       "monthly_limit_usd":_maximum_budget(env),
       "claude_monthly_limit_usd":float(env.get("TEA_CLAUDE_MONTHLY_LIMIT_USD","12"))}
