"""Google Gemini and GroqCloud text chat adapters.

No API key is persisted, sent in URL/query params or exposed in exceptions.
Models chosen from documented allowlists; keys passed only in request headers.
"""
from __future__ import annotations
import json
import ssl
import socket
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

class TemporaryProviderError(RuntimeError):
    """Only network, rate-limit and provider outages may trigger backup."""
    pass

# Only models documented with free-tier text input and output eligibility.
# API calls may still be billed if the user's Google project is on paid tier.
GEMINI_MODELS=("gemini-3.8-flash","gemini-3.6-flash","gemini-3.5-flash-lite",
               "gemini-3.1-flash-lite","gemini-2.5-flash","gemini-2.5-flash-lite")
# Listed under Groq's free-plan rate limits. Not guaranteed free on paid accounts.
GROQ_MODELS=("openai/gpt-oss-120b","openai/gpt-oss-20b","qwen/qwen3.8-27b")
GEMINI_FREE_TIER_MODELS=frozenset(GEMINI_MODELS)
GROQ_FREE_TIER_MODELS=frozenset(GROQ_MODELS)
GEMINI_DEFAULT={a:("gemini-3.5-flash-lite" if a in ("creative","analyst") else "gemini-3.8-flash")
 for a in ("ceo","strategy","compliance","research","creative","analyst")}
GROQ_DEFAULT={a:("openai/gpt-oss-20b" if a in ("creative","analyst") else "openai/gpt-oss-120b")
 for a in GEMINI_DEFAULT}
GEMINI_ENDPOINT="https://generativelanguage.googleapis.com/v1beta/models/"
GROQ_ENDPOINT="https://api.groq.com/openai/v1/chat/completions"



def _provider_error_hint(error):
    """Extract only documented error codes/types; never display freeform server text.

    Provider error messages may contain echoed request data or credentials.
    Those raw messages must not be shown in UI, logs or raised exceptions.
    """
    try:
        raw=error.read(4096)
        data=json.loads(raw.decode("utf-8",errors="replace"))
        info=data.get("error",{}) if isinstance(data,dict) else {}
        if not isinstance(info,dict):
            return ""
        code=info.get("code","")
        kind=info.get("type","")
    except (ValueError,AttributeError,OSError,TypeError):
        return ""
    if code=="model_permission_blocked_org":
        return "Model bị chặn ở cấp tổ chức. Vào console.groq.com/settings/limits để cấp quyền."
    if code=="model_permission_blocked_project":
        return "Model bị chặn ở cấp dự án. Vào console.groq.com/settings/project/limits để cấp quyền."
    if kind=="permissions_error":
        return "Groq trả về permissions_error: kiểm tra quyền tổ chức, dự án và model."
    return ""

def _request_json(request, transport=None, timeout=60):
    try:
        if transport is None:
            with urlopen(request,timeout=timeout) as resp:
                return json.loads(resp.read(1_500_000).decode("utf-8"))
        return transport(request)
    except HTTPError as ex:
        code=ex.code
        reasons={
            400:"Yêu cầu hoặc tham số model không hợp lệ.",
            401:"API key không hợp lệ hoặc thuộc dịch vụ khác. Hãy tạo key tại console.groq.com/keys nếu dùng Groq.",
            403:"API key/tài khoản không có quyền. Kiểm tra quyền và giới hạn dự án trên GroqCloud.",
            404:"Đường dẫn API hoặc model không tồn tại.",
            429:"Hết lượt hoặc vượt giới hạn tốc độ API; có thể thử lại.",
            498:"Nhà cung cấp tạm hết năng lực phục vụ."
        }
        detail=reasons.get(code,"Máy chủ từ chối yêu cầu hoặc tạm gián đoạn.")
        if code==403:
            provider_hint=_provider_error_hint(ex)
            if provider_hint:
                detail=provider_hint
        if code in (429,498) or 500<=code<=599:
            raise TemporaryProviderError("HTTP "+str(code)+": "+detail) from None
        raise RuntimeError("HTTP "+str(code)+": "+detail) from None
    except (URLError,TimeoutError,OSError) as ex:
        reason=getattr(ex,"reason",ex)
        if isinstance(reason,ssl.SSLError):
            message="Lỗi chứng chỉ SSL/TLS khi kết nối API. Kiểm tra ngày giờ Windows, VPN hoặc phần mềm chặn HTTPS."
        elif isinstance(reason,socket.gaierror):
            message="Không phân giải được tên miền API (DNS). Kiểm tra Internet, DNS hoặc proxy."
        elif isinstance(reason,(TimeoutError,socket.timeout)):
            message="Hết thời gian chờ kết nối API. Kiểm tra kết nối Internet, proxy hoặc tường lửa."
        else:
            message="Không truy cập được API qua HTTPS. Kiểm tra Internet, proxy, VPN hoặc tường lửa."
        raise TemporaryProviderError(message) from None


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
    if not key:raise ValueError("Chưa lưu hoặc chưa nhập Groq API key. Hãy dán key vào phần Cài đặt và bấm Kiểm tra.")
    key=key.strip()
    if key.startswith("xai-"):
        raise ValueError("Đây có vẻ là API key Grok của xAI. GroqCloud là dịch vụ khác; hãy tạo key tại console.groq.com/keys.")
    request=Request("https://api.groq.com/openai/v1/models",
                    headers={"Authorization":"Bearer "+key})
    response=_request_json(request,transport,timeout=10)
    if not isinstance(response,dict) or not isinstance(response.get("data"),list):
        raise ValueError("Groq API phản hồi danh sách model không hợp lệ")
    found={m.get("id","") for m in response["data"] if isinstance(m,dict)}
    available=sorted(found.intersection(GROQ_MODELS))
    return {"ok":True,
        "message":("GroqCloud API key hợp lệ; đã đọc được "+str(len(found))+
                   " model trong tài khoản. Chưa tạo nội dung."),
        "supported_models":available,
        "warning":("" if available else
                   "Không có model nào trùng với danh sách phần mềm hỗ trợ. Hãy kiểm tra quyền model trong GroqCloud hoặc cập nhật phần mềm.")}
