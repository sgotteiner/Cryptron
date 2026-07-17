"""Chat-turn memory: every turn captured (chat is a sense), history served
back, and the system prompt assembled with the playbook riding along."""
from datetime import datetime, timezone

from .. import db
from ..memory import paths
from . import prompt


def save_turn(conn, chat_id: str, role: str, text: str, message_id=None) -> None:
    db.insert_sense_rows(conn, "sense_chat", [{
        "coin": None, "observed_at": datetime.now(timezone.utc), "source_id": chat_id,
        "payload": {"role": role, "text": text, "message_id": message_id}}])


def history(conn, chat_id: str, n: int = 16) -> list:
    rows = conn.execute("""
        SELECT payload->>'role', payload->>'text' FROM sense_chat
        WHERE source_id = %s ORDER BY id DESC LIMIT %s""", (chat_id, n)).fetchall()
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]


def system_prompt(conn) -> str:
    """Identity + the playbook: every taught lesson rides along on every call."""
    lessons = paths.load_guidance(conn)
    if not lessons:
        return prompt.SYSTEM
    book = "\n".join(f"- {l}" + (f" (why: {w})" if w else "") for l, w in lessons)
    return (f"{prompt.SYSTEM}\n\n## THE PLAYBOOK — lessons your user taught you. "
            f"Apply these AUTOMATICALLY in every investigation, unasked:\n{book}")
