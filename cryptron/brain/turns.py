"""Chat-turn memory: every turn captured (chat is a sense), history served
back, and the system prompt assembled with the playbook riding along."""
import json
from datetime import datetime, timezone

from .. import db
from ..memory import embed, paths
from . import prompt


def save_turn(conn, chat_id: str, role: str, text: str, message_id=None) -> None:
    db.insert_sense_rows(conn, "sense_chat", [{
        "coin": None, "observed_at": datetime.now(timezone.utc), "source_id": chat_id,
        "payload": {"role": role, "text": text, "message_id": message_id}}])


def history(conn, chat_id: str, n: int = 8, clip: int = 800) -> list:
    """Past turns as context — a SLICE, not the archive (memory_design §6).
    Assistant turns are served WRAPPED in the JSON protocol: the model
    imitates its own recent replies more strongly than any instruction, so
    every example of itself must demonstrate the protocol. Long turns clip;
    the full text is always in sense_chat if the brain needs to sql it."""
    rows = conn.execute("""
        SELECT payload->>'role', payload->>'text' FROM sense_chat
        WHERE source_id = %s
          AND coalesce(payload->>'fabricated', '') <> 'true'
        ORDER BY id DESC LIMIT %s""", (chat_id, n)).fetchall()
    out = []
    for role, text in reversed(rows):
        if len(text) > clip:
            text = text[:clip] + " …[clipped]"
        out.append({"role": role,
                    "content": json.dumps({"reply": text}, ensure_ascii=False)
                    if role == "assistant" else text})
    return out


async def system_prompt(conn, user_text: str = "") -> str:
    """Identity + the RELEVANT playbook slice — lessons retrieved by vector
    similarity to this message, never the whole book (memory_design §6)."""
    vec = None
    if user_text:
        try:
            vec = json.dumps(await embed.embed(user_text))
        except Exception:
            vec = None
    lessons = paths.load_guidance(conn, query_vec=vec, k=6)
    if not lessons:
        return prompt.SYSTEM
    book = "\n".join(f"- {l}" + (f" (why: {w})" if w else "") for l, w in lessons)
    return (f"{prompt.SYSTEM}\n\n## PLAYBOOK (the lessons most relevant to this "
            f"message — apply unasked; more exist, retrievable via sql):\n{book}")
