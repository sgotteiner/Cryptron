"""Chat-turn memory: every turn captured (chat is a sense), a clipped slice
served back as context."""
import json
from datetime import datetime, timezone

from .. import db


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


