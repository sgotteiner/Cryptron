"""The situation-graph walker: one taught step at a time, zero LLM tokens
while walking. Walks while teachings are confident; a 'verdict' edge triggers
the end analysis. When teachings run out it RETURNS what it found — the
turn layer (assist.py) always appends the next-step suggestion."""
import json
import os

from ..log import log
from ..memory import embed, paths
from ..tickers import find_tickers
from . import prompt, render, session
from .dispatch import call_tool

STEP_SIM_MIN = float(os.environ.get("STEP_SIM_MIN", "0.60"))
MAX_STEPS = 12


async def next_taught(conn, situation: str, done: set) -> dict | None:
    """Nearest taught step NOT already executed in this flow — a step is one
    bead on the path, never a drum loop."""
    vec = json.dumps(await embed.embed(situation, task="RETRIEVAL_QUERY"))
    rows = conn.execute("""
        SELECT id, situation, action, 1 - (embedding <=> %s::vector) AS sim
        FROM taught_steps WHERE active AND embedding IS NOT NULL
        ORDER BY embedding <=> %s::vector LIMIT 5""", (vec, vec)).fetchall()
    for row in rows:
        action = row[2]
        if (action.get("tool") or "") not in done or action.get("kind") == "verdict":
            return {"id": row[0], "situation": row[1], "action": action,
                    "sim": round(row[3], 3)}
    return None


def fill_args(hint: dict, task: str) -> dict | None:
    """Mechanical binding: {coin}/{source_id} resolved from the task text.
    Unresolvable placeholder -> None (can't walk this edge here)."""
    tickers = find_tickers(task)
    groups = [g for g in ("sangitagem", "crypto_gemsignals") if g in task.lower()]
    args = {}
    for k, v in (hint or {}).items():
        blob = json.dumps(v)
        if "{coin}" in blob:
            if not tickers:
                return None
            blob = blob.replace("{coin}", tickers[0])
        if "{source_id}" in blob:
            if not groups:
                return None
            blob = blob.replace("{source_id}", groups[0])
        args[k] = json.loads(blob)
    return args


async def run(conn, chat_id: str, task: str) -> str:
    """Walk taught edges from the current session state; stop honestly."""
    s = session.of(chat_id)
    failures = []
    for _ in range(MAX_STEPS):
        flow = session.task_steps(chat_id)
        situation = render.render(task, flow)
        done = {x["tool"] for x in flow}
        top = await next_taught(conn, situation, done)
        log("step", f"sim={top['sim'] if top else 'none'} "
            f"-> {json.dumps(top['action']) if top else 'no edges'}")
        if top is None or top["sim"] < STEP_SIM_MIN:
            found = "\n".join(f"- {x['text']}" for x in flow[-6:])
            return (f"Here's what I have so far:\n{found}"
                    if found else "I haven't checked anything for this yet.")
        action = top["action"]
        if action.get("kind") == "verdict":
            return await analyze(conn, task, flow, failures)
        args = fill_args(action.get("args_hint"), task)
        if args is None:
            return "I know the next step but can't fill its arguments — " \
                   f"teach me: {json.dumps(action)}"
        result = await call_tool(conn, action["tool"], args)
        if isinstance(result, dict) and result.get("error"):
            failures.append(f"{action['tool']}: {str(result['error'])[:120]}")
        text, _ = render.summarize(action["tool"], result)
        session.add_step(chat_id, action["tool"], text,
                         json.dumps(result, default=str))
    return await analyze(conn, task, flow, failures)


async def analyze(conn, task: str, state: list, failures: list) -> str:
    from . import llm
    gathered = "\n".join(f"- {x['tool']}: {x['raw']}" for x in state) or "(nothing)"
    try:  # the qualitative playbook informs judgment (top-relevant only)
        vec = json.dumps(await embed.embed(task, task="RETRIEVAL_QUERY"))
        lessons = paths.load_guidance(conn, query_vec=vec, k=4)
        book = "\n".join(f"- {l}" for l, _ in lessons)
    except Exception:
        book = ""
    reply = (await llm.complete(
        prompt.ANALYZE + (f"\nHis taught principles (apply):\n{book}" if book else ""),
        [{"role": "user", "content":
          f"TASK: {task}\n\nGATHERED DATA:\n{gathered}"}])).strip()
    if failures:
        reply += ("\n\n⚠️ System note — these checks FAILED (answer may be "
                  "incomplete): " + " | ".join(failures))
    return reply
