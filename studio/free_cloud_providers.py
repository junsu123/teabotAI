"""Google Gemini and GroqCloud text chat adapters.

No API key is persisted, sent in URL/query params or exposed in exceptions.
Models chosen from documented allowlists; keys passed only in request headers.
"""
from __future__ import annotations
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

class TemporaryProviderError(RuntimeError):
    """Only network, rate-limit and provider outages may trigger backup."""
    pass

GEMINI_MODELS=("gemini-3.8-flash","gemini-3.5-flash-lite")
GROQ_MODELS=("openai/gpt-oss-120b","openai/gpt-oss-20b","qwen/qwen3.8-27b")
GEMINI_DEFAULT={a:("gemini-3.5-flash-lite" if a in ("creative","analyst") else "gemini-3.8-flash")
 for a in ("ceo","strategy","compliance","research","creative","analyst")}
GROQ_DEFAULT={a:("openai/gpt-oss-20b" if a in ("creative","analyst") else "openai/gpt-oss-120b")
 for a in GEMINI_DEFAULT}
GEMINI_ENDPOINT="https://generativelanguage.googleapis.com/v1beta/models/"
GROQ_ENDPOINT="https://api.groq.com/openai/v1/chat/completions"


def _request_json(request, transport=None, timeout=60):
    try:
        if transport is None:
            with urlopen(request,timeout=timeout) as resp:
                return json.loads(resp.read(1_500_000).decode("utf-8"))
        return transport(request)
    except HTTPError as ex:
        if ex.code == 429 or 500 <= ex.code <= 599:
            raise TemporaryProviderError("API tạm không sẵn sàng hoặc hết hạn mức (HTTP "+str(ex.code)+")") from None
        raise RuntimeError("API từ chối yêu cầu (HTTP "+str(ex.code)+"). Kiểm tra khóa và mô hình.") from None
    except (URLError,TimeoutError,OSError):
        raise TemporaryProviderError("Không kết nối được nhà cung cấp AI; kiểm tra mạng hoặc thử nhà cung cấp phụ.") from None


def _system(agent):
    from main import AGENTS
    from model_router import VIETNAMESE_RULES
    return AGENTS[agent]+"\n"+VIETNAMESE_RULES


def gemini_chat(agent, prompt, *, key, model, transport=None):
    if model not in GEMINI_MODELS:raise ValueError("Mô hình Gemini chưa được phép")
    if not key:raise RuntimeError("Chưa lưu Gemini API key trong phần mềm")
    data={"systemInstruction":{"parts":[{"text":_system(agent)}]},
          "contents":[{"role":"user","parts":[{"text":str(prompt)[:20000]}]}],
          "generationConfig":{"maxOutputTokens":1100,"temperature":0.35}}
    req=Request(GEMINI_ENDPOINT+model+":generateContent",method="POST",
                data=json.dumps(data,ensure_ascii=False).encode("utf-8"),
                headers={"x-goog-api-key":key,"Content-Type":"application/json"})
    response=_request_json(req,transport)
    if not isinstance(response,dict):raise RuntimeError("Gemini trả về dữ liệu không hợp lệ")
    text="\n".join(p.get("text","") for c in response.get("candidates",[]) if isinstance(c,dict)
       for p in (c.get("content",{}).get("parts",[]) or [])
       if isinstance(p,dict) and isinstance(p.get("text"),str)).strip()
    if not text:
        reason=str(response.get("promptFeedback",{}).get("blockReason",""))[:90]
        raise RuntimeError("Gemini không trả về văn bản"+(" ("+reason+")" if reason else ""))
    return text


def groq_chat(agent, prompt, *, key, model, transport=None):
    if model not in GROQ_MODELS:raise ValueError("Mô hình Groq chưa được phép")
    if not key:raise RuntimeError("Chưa lưu Groq API key trong phần mềm")
    data={"model":model,"temperature":0.3,"max_completion_tokens":1050,
          "messages":[{"role":"system","content":_system(agent)},
                      {"role":"user","content":str(prompt)[:20000]}]}
    req=Request(GROQ_ENDPOINT,method="POST",
        data=json.dumps(data,ensure_ascii=False).encode("utf-8"),
        headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"})
    response=_request_json(req,transport)
    if not isinstance(response,dict):raise RuntimeError("Groq trả về dữ liệu không hợp lệ")
    choices=response.get("choices") or []
    answer=(choices[0].get("message",{}).get("content") or "").strip() if choices else ""
    if not answer:raise RuntimeError("Groq không trả về nội dung")
    return answer


def test_gemini(key,transport=None):
    if not key:raise ValueError("Chưa lưu Gemini API key")
    request=Request("https://generativelanguage.googleapis.com/v1beta/models?pageSize=100",
                    headers={"x-goog-api-key":key})
    response=_request_json(request,transport,timeout=10)
    if not isinstance(response,dict) or not isinstance(response.get("models"),list):
        raise ValueError("Danh sách model Gemini không hợp lệ")
    found={m.get("name","").removeprefix("models/") for m in response["models"] if isinstance(m,dict)}
    return {"ok":True,"message":"Gemini API key được chấp nhận. Chưa tạo nội dung.",
            "supported_models":sorted(found.intersection(GEMINI_MODELS))}


def test_groq(key,transport=None):
    if not key:raise ValueError("Chưa lưu Groq API key")
    request=Request("https://api.groq.com/openai/v1/models",
                    headers={"Authorization":"Bearer "+key})
    response=_request_json(request,transport,timeout=10)
    if not isinstance(response,dict) or not isinstance(response.get("data"),list):
        raise ValueError("Danh sách model Groq không hợp lệ")
    found={m.get("id","") for m in response["data"] if isinstance(m,dict)}
    return {"ok":True,"message":"Groq API key được chấp nhận. Chưa tạo nội dung.",
            "supported_models":sorted(found.intersection(GROQ_MODELS))}
