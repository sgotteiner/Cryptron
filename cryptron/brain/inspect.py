"""Introspection from the chat (his rule: full visibility from Telegram —
"I can't develop like that, I don't know what's going on in my system").

graph(topic?) — the closest taught situations + next steps for a topic
(dry-run, nothing executes), or the whole graph. trace(n) — what just
happened: the logbook's tail, exact sims, tools, failures, serving brain.
"""
import json

from ..log import LOG_DIR
from ..memory import embed
from . import render

KEEP = ("| user", "| route", "| step", "| tool", "| TOOL-FAIL", "| llm",
        "| edge", "| reflex", "| reply")


async def graph(conn, topic: str = "") -> dict:
    if topic:
        situation = f"TASK: {render.canon_task(topic)}\nNothing checked yet."
        vec = json.dumps(await embed.embed(situation, task="RETRIEVAL_QUERY"))
        rows = conn.execute("""
            SELECT id, situation, action, 1 - (embedding <=> %s::vector)
            FROM taught_steps WHERE active AND embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector LIMIT 5""", (vec, vec)).fetchall()
        lines = [f"My situation for '{topic}':\n  {situation.splitlines()[0]}",
                 "Closest teachings (sim | situation -> next step):"]
        for id_, sit, action, sim in rows:
            lines.append(f"  {sim:.2f} | [{id_}] {sit.splitlines()[0][:70]} -> "
                         f"{json.dumps(action)}")
        if not rows:
            lines.append("  (the graph is EMPTY — teach me by approving/"
                         "correcting my suggestions)")
        lines.append("Threshold to act without asking: 0.60")
        return {"text": "\n".join(lines)}
    rows = conn.execute("""
        SELECT id, situation, action FROM taught_steps WHERE active
        ORDER BY id LIMIT 30""").fetchall()
    n = conn.execute("SELECT count(*) FROM taught_steps WHERE active").fetchone()[0]
    lines = [f"Taught graph: {n} edges" + (" (showing 30)" if n > 30 else "")]
    for id_, sit, action in rows:
        lines.append(f"  [{id_}] {sit.splitlines()[0][:70]} -> {json.dumps(action)}")
    if not rows:
        lines.append("  EMPTY — teach me by approving/correcting suggestions")
    return {"text": "\n".join(lines)}


def playbook(conn) -> dict:
    """Every active lesson, verbatim — 'what guidance did you save?'"""
    rows = conn.execute("""
        SELECT id, lesson, coalesce(why, ''), provenance FROM guidance
        WHERE active ORDER BY id""").fetchall()
    lines = [f"Playbook: {len(rows)} active lessons"]
    for id_, lesson, why, prov in rows:
        lines.append(f"  [{id_}|{prov}] {lesson}" + (f" (why: {why})" if why else ""))
    return {"text": "\n".join(lines)}


def trace(n: int = 25) -> dict:
    """The last n meaningful logbook lines — exactly what the system did."""
    try:
        lines = (LOG_DIR / "cryptron.log").read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return {"text": "no log yet"}
    picked = [l for l in lines if any(k in l for k in KEEP)][-n:]
    return {"text": "What happened (last events):\n" + "\n".join(picked)}
