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
    """Show safe structured Groq error metadata, never raw server messages or keys.

    A provider may echo a user-supplied prompt or token in its error.message.
    Render only strictly validated code/type tokens or fixed diagnostic phrases.
    """
    import re
    try:
        raw=error.read(8192)
    except (AttributeError,OSError):
        return ""
    try:
        data=json.loads(raw.decode("utf-8",errors="replace"))
        info=data.get("error",{}) if isinstance(data,dict) else {}
        if not isinstance(info,dict):
            return ""
    except (ValueError,TypeError):
        # A 403 HTML page typically originates from an access-control layer.
        # Do not assume Cloudflare or blame a country without evidence.
        return ("Phản hồi không phải JSON từ API (có thể là lớp bảo vệ mạng/IP). "
                "Thử tắt proxy/VPN và kiểm tra bằng mạng khác." if
                raw.lstrip()[:15].lower().startswith((b"<!doctype html",b"<html")) else "")
    code=info.get("code","")
    kind=info.get("type","")
    message=info.get("message","")
    if code=="model_permission_blocked_org":
        return "Model bị chặn ở cấp tổ chức. Vào console.groq.com/settings/limits để cấp quyền."
    if code=="model_permission_blocked_project":
        return "Model bị chặn ở cấp dự án. Vào console.groq.com/settings/project/limits để cấp quyền."
    if isinstance(message,str) and any(v in message.lower() for v in
        ("region is not supported","country is not supported","geographical restriction",
         "not available in your region","not available in your country")):
        return "Groq báo hạn chế vùng truy cập. Kiểm tra vị trí mạng/IP và chính sách truy cập của Groq."
    parts=[]
    if kind=="permissions_error":
        parts.append("Groq báo lỗi loại permissions_error.")
    def safe_token(value):
        return value if isinstance(value,str) and re.fullmatch(r"[A-Za-z0-9_.-]{1,64}",value) else ""
    clean_code=safe_token(code)
    clean_kind=safe_token(kind)
    if clean_code:
        parts.append("Mã lỗi Groq: "+clean_code+".")
    if clean_kind and clean_kind!="permissions_error":
        parts.append("Loại lỗi: "+clean_kind+".")
    if parts:
        return " ".join(parts)
    return ""


def _request_json(request, transport=None, timeout=60):
    try:
        if transport is None:
            with urlopen(request,timeout=timeout) as resp:
                return json.loads(resp.read(1_500_000).decode("utf-8"))
        return transport(request)
    except HTTPError as ex:
        code=ex.code
        google="googleapis.com" in request.full_url
        reasons={
            400:"Yêu cầu hoặc tham số model không hợp lệ.",
            401:("API key Gemini không hợp lệ. Hãy kiểm tra tại Google AI Studio." if google else
                 "API key Groq không hợp lệ hoặc thuộc dịch vụ khác. Hãy dùng key từ console.groq.com/keys."),
            403:("Google từ chối quyền truy cập Gemini API. Kiểm tra dự án, quyền API key và cài đặt Google AI Studio." if google else
                 "API key/tài khoản Groq không có quyền. Kiểm tra quyền và giới hạn dự án trên GroqCloud."),
            404:"Đường dẫn API hoặc model không tồn tại.",
            429:"Hết lượt hoặc vượt giới hạn tốc độ API; có thể thử lại.",
            498:"Nhà cung cấp tạm hết năng lực phục vụ."
        }
        detail=reasons.get(code,"Máy chủ từ chối yêu cầu hoặc tạm gián đoạn.")
        if code==403 and not google:
            provider_hint=_provider_error_hint(ex)
            if provider_hint:
                detail=provider_hint
            if request.full_url.endswith("/models"):
                detail+=" Đây là lỗi tại bước đọc danh sách model, chưa phải lỗi sử dụng GPT-OSS. "
                detail+="Thử một câu ở console.groq.com/playground để phân biệt lỗi API và lỗi phần mềm."
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


def _groq_sdk_json(key, *, payload=None, timeout=60):
    """Real Groq requests use the official SDK, matching the working standalone script.

    The transport-injection branch in callers exists only for offline tests.
    All exceptions exposed to the UI omit the API key, raw provider error
    messages, request URL with query strings and the original prompt.
    """
    try:
        import groq
    except ImportError:
        raise RuntimeError("Chưa cài thư viện Groq SDK. Đóng phần mềm và chạy lại setup_windows.bat.") from None
    client=None
    try:
        client=groq.Groq(api_key=key,timeout=float(timeout),max_retries=0)
        if payload is None:
            response=client.models.list()
        else:
            response=client.chat.completions.create(**payload)
        if isinstance(response,dict):
            data=response
        elif hasattr(response,"model_dump"):
            data=response.model_dump()
        elif hasattr(response,"to_dict"):
            data=response.to_dict()
        else:
            raise RuntimeError("Groq SDK trả dữ liệu chưa hỗ trợ. Hãy cập nhật thư viện Groq.")
        if not isinstance(data,dict):
            raise RuntimeError("Groq SDK trả dữ liệu không hợp lệ")
        return data
    except groq.APIStatusError as error:
        code=error.status_code
        fixed={
            400:"Nội dung yêu cầu hoặc tham số model không hợp lệ.",
            401:"Khóa Groq trong database không hợp lệ hoặc đã bị thu hồi; hãy lưu khóa mới.",
            403:"Groq từ chối quyền truy cập. Nếu mã mẫu Python chạy được, kiểm tra khóa đã lưu trong database và quyền Project.",
            404:"Groq không nhận ra model hoặc đường dẫn API.",
            429:"Groq hết hạn mức hoặc giới hạn tốc độ.",
        }.get(code,"Groq tạm không xử lý được yêu cầu.")
        # Use a documented status code only; do not echo raw response text.
        if code==429 or 500<=code<=599:
            raise TemporaryProviderError("Groq SDK HTTP "+str(code)+": "+fixed) from None
        raise RuntimeError("Groq SDK HTTP "+str(code)+": "+fixed) from None
    except groq.APIConnectionError:
        raise TemporaryProviderError("Groq SDK không kết nối được (mạng/proxy/DNS/TLS). "
                                     "Thử lại bằng mạng đang chạy đoạn Python mẫu.") from None
    except groq.APIError:
        raise RuntimeError("Groq SDK phát sinh lỗi API. Kiểm tra phiên bản SDK, tài khoản và cấu hình model.") from None
    finally:
        if client is not None:
            client.close()



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
    # GPT-OSS can spend part of max_completion_tokens on internal reasoning.
    # Low effort leaves more room for the actual final Vietnamese answer.
    data={"model":model,"temperature":0.3,"max_completion_tokens":1600,
          "messages":[{"role":"system","content":_system(agent)},
                      {"role":"user","content":str(prompt)[:20000]}]}
    if model.startswith("openai/gpt-oss-"):
        data["reasoning_effort"]="low"
        data["include_reasoning"]=False
    if transport is None:
        response=_groq_sdk_json(key,payload=data,timeout=90)
    else:
        req=Request(GROQ_ENDPOINT,method="POST",
            data=json.dumps(data,ensure_ascii=False).encode("utf-8"),
            headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"})
        response=_request_json(req,transport)
    if not isinstance(response,dict):raise RuntimeError("Groq trả về dữ liệu không hợp lệ")
    choices=response.get("choices") or []
    answer=(choices[0].get("message",{}).get("content") or "").strip() if choices else ""
    if not answer:
        finish=choices[0].get("finish_reason","") if choices and isinstance(choices[0],dict) else ""
        if finish=="length":
            raise RuntimeError("Groq đã dùng hết giới hạn token trước khi tạo câu trả lời. Thử giảm yêu cầu hoặc chia nhiệm vụ.")
        raise RuntimeError("Groq không trả về nội dung văn bản. Model đã phản hồi nhưng không có câu trả lời.")
    return answer


def test_saved_groq_agent(key,agent,model,transport=None):
    """Small explicit paid-or-free-tier test using exactly the CEO runtime path.

    Uses the *saved* key and the selected model; no input key override accepted.
    The prompt is intentionally tiny, but the API payload matches groq_chat().
    """
    from model_router import VALID_AGENTS
    if agent not in VALID_AGENTS or model not in GROQ_MODELS:
        raise ValueError("Agent hoặc model Groq không hợp lệ")
    output=groq_chat(agent,
                     "Hãy trả lời bằng một câu tiếng Việt ngắn: Kết nối AI hoạt động.",
                     key=key,model=model,transport=transport)
    return {"ok":True,"agent":agent,"model":model,
            "message":"Khóa đã lưu trong database và model của agent kết nối Groq thành công.",
            "sample":output[:120]}


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


def test_groq_chat(key,transport=None):
    """User-initiated tiny chat test; this consumes API tokens and quota."""
    if not isinstance(key,str) or not key.strip():
        raise ValueError("Chưa nhập hoặc lưu Groq API key")
    key=key.strip()
    if key.startswith("xai-"):
        raise ValueError("Đây có vẻ là khóa Grok của xAI, không phải GroqCloud.")
    # Match the minimal user-verified Python SDK call exactly, without
    # a system prompt, custom temperature or reasoning parameters.
    model="openai/gpt-oss-120b"
    payload={
        "model":model,
        "messages":[{"role":"user","content":"Reply with exactly: GROQ API OK"}],
        "max_completion_tokens":100,
    }
    request=Request(GROQ_ENDPOINT,method="POST",
        data=json.dumps(payload,ensure_ascii=False).encode("utf-8"),
        headers={"Authorization":"Bearer "+key,"Content-Type":"application/json",
                 "Accept":"application/json"})
    response=(_groq_sdk_json(key,payload=payload,timeout=30) if transport is None
              else _request_json(request,transport,timeout=20))
    if not isinstance(response,dict) or not isinstance(response.get("choices"),list) or not response["choices"]:
        raise ValueError("Groq không trả về kết quả Chat Completions hợp lệ")
    message=response["choices"][0].get("message",{})
    answer=message.get("content") if isinstance(message,dict) else None
    snippet=(answer[:100] if isinstance(answer,str) else "")
    return {"ok":True,"model":model,"sample":snippet,
            "message":"Groq SDK đã gọi thành công GPT-OSS-120B theo cấu hình mã Python mẫu. "
                      "Phép thử có tiêu thụ một ít token/quota."}


def test_groq(key,transport=None):
    if not key:raise ValueError("Chưa lưu hoặc chưa nhập Groq API key. Hãy dán key vào phần Cài đặt và bấm Kiểm tra.")
    key=key.strip()
    if key.startswith("xai-"):
        raise ValueError("Đây có vẻ là API key Grok của xAI. GroqCloud là dịch vụ khác; hãy tạo key tại console.groq.com/keys.")
    request=Request("https://api.groq.com/openai/v1/models",
                    headers={"Authorization":"Bearer "+key})
    response=(_groq_sdk_json(key,timeout=15) if transport is None
              else _request_json(request,transport,timeout=10))
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
