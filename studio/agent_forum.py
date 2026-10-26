"""Auditable, bounded internal agent discussion. No hidden reasoning or tool actions.

Only AI CEO may make the final decision. Staff agents exchange *public working
notes*, questions, objections and responses, not chain-of-thought. Each turn
is persisted as plain text in the local SQLite database and shown read-only.
"""
from __future__ import annotations
import os
import sqlite3
from datetime import datetime

MAX_TURNS = 2  # At most two question/rebuttal rounds; CPU/LLM budget bounded.
ALLOWED_KINDS = {"assignment", "proposal", "question", "response", "objection",
                 "revision", "decision", "error", "retry"}
KNOWN_AGENTS = {"ceo", "research", "strategy", "creative", "analyst", "compliance", "system"}

def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")

def _db(path):
    connection = sqlite3.connect(path, timeout=15)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout=15000")
    return connection

def setup(db_path):
    with _db(db_path) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS agent_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mission_id INTEGER NOT NULL,
            sender TEXT NOT NULL, recipient TEXT NOT NULL,
            kind TEXT NOT NULL, body TEXT NOT NULL,
            created_at TEXT NOT NULL)""")
        c.execute("""CREATE INDEX IF NOT EXISTS agent_messages_mission
                  ON agent_messages(mission_id,id)""")

def record(db_path, mission_id, sender, recipient, kind, message):
    if sender not in KNOWN_AGENTS or recipient not in KNOWN_AGENTS:
        raise ValueError("Agent không hợp lệ")
    if kind not in ALLOWED_KINDS:
        raise ValueError("Loại trao đổi không hợp lệ")
    if kind == "decision" and sender != "ceo":
        raise ValueError("Chỉ AI CEO được chốt phương án")
    if kind in {"assignment"} and sender != "ceo":
        raise ValueError("Chỉ AI CEO được phân công nội bộ")
    # Do not persist raw prompts, auth data, credentials, tokens or hidden reasoning.
    text = str(message or "").strip()[:5500]
    if not text:
        return None
    with _db(db_path) as c:
        cur = c.execute("""INSERT INTO agent_messages
            (mission_id,sender,recipient,kind,body,created_at)
            VALUES(?,?,?,?,?,?)""",
            (mission_id,sender,recipient,kind,text,now()))
        return cur.lastrowid

def get_messages(db_path, mission_id, limit=120):
    limit = max(1, min(int(limit), 160))
    with _db(db_path) as c:
        # Ascending chronology, bounded by last limit rows if a task is long.
        rows = list(c.execute("""SELECT id,mission_id,sender,recipient,kind,body,created_at
              FROM agent_messages WHERE mission_id=? ORDER BY id DESC LIMIT ?""",
              (int(mission_id), limit)))
    return [dict(r) for r in reversed(rows)]

def configured_rounds():
    try:
        return max(0, min(MAX_TURNS, int(os.environ.get("TEA_DEBATE_ROUNDS", "1"))))
    except ValueError:
        return 1

def _clip(text, n=3000):
    return str(text or "")[:n]

def debate(db_path, mission_id, chat, agents, outputs, context, rounds=None):
    """A asks B, B replies/objects, A responds. CEO sees all and adjudicates.

    Bounded calls: 3 per round, no agent chooses new agents, no recursive tasks.
    chat(agent, prompt) remains the existing Ollama callback.
    """
    rounds = configured_rounds() if rounds is None else max(0, min(MAX_TURNS, int(rounds)))
    if len(agents) < 2 or rounds == 0:
        return []
    a, b = agents[:2]
    exchange = []
    common = (
        "Bạn tham gia PHÒNG HỌP NỘI BỘ do AI CEO điều phối. "
        "Chỉ viết ý kiến công việc có thể chia sẻ (không phải suy luận nội tâm). "
        "Nêu rõ điều thiếu bằng chứng; không bịa số liệu. "
        "Không tự thực hiện hành động, không đăng hàng, không chi tiền, không vượt xác minh. "
        "Mọi đề xuất là bản nháp; CEO là người DUY NHẤT chốt phương án. "
        "Trả lời tiếng Việt, tối đa 180 từ.\n"
        + _clip(context, 2000)
    )
    for i in range(rounds):
        history = "\n".join(f"{x['sender']} → {x['recipient']}: {_clip(x['body'],800)}" for x in exchange[-4:])
        prompt_a = (common +
            f"\nBạn là {a}. Ý kiến ban đầu của bạn: {_clip(outputs[a],1800)}. "
            f"Ý kiến của {b}: {_clip(outputs[b],1800)}.\n"
            f"Trao đổi đã có:\n{history}\n"
            f"Đặt đúng 1 câu hỏi quan trọng cho {b}, chỉ ra một rủi ro hoặc điểm chưa thống nhất; "
            "không yêu cầu thông tin bí mật.")
        question = chat(a, prompt_a)
        if not isinstance(question,str) or not question.strip():
            raise RuntimeError(f"{a} không tạo được câu hỏi phản biện")
        record(db_path, mission_id, a, b, "question", question)
        exchange.append({"sender":a,"recipient":b,"kind":"question","body":question})

        prompt_b = (common +
            f"\nBạn là {b}. Ý kiến ban đầu của bạn: {_clip(outputs[b],1800)}. "
            f"Ý kiến {a}: {_clip(outputs[a],1800)}.\n"
            f"{a} hỏi: {_clip(question,1600)}\nTrao đổi trước:\n{history}\n"
            f"Hãy trả lời thẳng câu hỏi, đưa ra một phản biện hoặc hỏi ngược {a}. "
            "Nêu căn cứ và điều chưa chắc chắn.")
        response = chat(b, prompt_b)
        if not isinstance(response,str) or not response.strip():
            raise RuntimeError(f"{b} không trả lời phản biện")
        record(db_path, mission_id, b, a, "objection", response)
        exchange.append({"sender":b,"recipient":a,"kind":"objection","body":response})

        prompt_reply = (common +
            f"\nBạn là {a}. Ý kiến ban đầu: {_clip(outputs[a],1200)}.\n"
            f"{b} đã phản biện: {_clip(response,2200)}.\n"
            "Hãy trả lời hoặc sửa đề xuất của mình dựa trên phản biện; "
            "nêu điểm đã thống nhất, điểm còn khác biệt. Không tự tuyên bố chiến thắng.")
        reply = chat(a, prompt_reply)
        if not isinstance(reply,str) or not reply.strip():
            raise RuntimeError(f"{a} không phản hồi được")
        record(db_path, mission_id, a, "ceo", "revision", reply)
        exchange.append({"sender":a,"recipient":"ceo","kind":"revision","body":reply})
    return exchange
