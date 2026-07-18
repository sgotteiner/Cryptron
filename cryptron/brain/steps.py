"""The situation-graph loop (his design): one step at a time, zero LLM tokens
while walking. Embed the situation -> nearest TAUGHT step -> execute. LLM only
at the boundaries: the end analysis (verdict) and the suggestion fallback when
teachings run thin — his approval of a suggestion becomes a new taught edge.
"""
import json
import os

from ..log import log
from ..memory import embed, paths
from ..tickers import find_tickers
from . import prompt, render
from .dispatch import call_tool

STEP_SIM_MIN = float(os.environ.get("STEP_SIM_MIN", "0.60"))
MAX_STEPS = 12
PENDING: dict = {}  # chat_id -> {"task", "state", "suggestion"}


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
        key = action.get("tool") or action.get("kind")
        if key not in done or action.get("kind") == "verdict":
            return {"id": row[0], "situation": row[1], "action": action,
                    "sim": round(row[3], 3)}
    return None


def fill_args(hint: dict, task: str) -> dict | None:
    """Mechanical binding: {coin} from the task's ticker, {source_id} from a
    group name in the task. Unresolvable placeholder -> None (can't walk)."""
    tickers = find_tickers(task)
    groups = [g for g in ("sangitagem", "crypto_gemsignals") if g in task.lower()]
    args = {}
    for k, v in (hint or {}).items():
        if isinstance(v, str) and "{coin}" in v:
            if not tickers:
                return None
            v = v.replace("{coin}", tickers[0])
        if isinstance(v, str) and "{source_id}" in v:
            if not groups:
                return None
            v = v.replace("{source_id}", groups[0])
        if isinstance(v, list):
            v = [x.replace("{coin}", tickers[0]) if isinstance(x, str)
                 and "{coin}" in x and tickers else x for x in v]
            if any(isinstance(x, str) and "{" in x for x in v):
                return None
        args[k] = v
    return args


async def run(conn, chat_id: str, task: str, state: list | None = None) -> str:
    state, failures = state if state is not None else [], []
    for _ in range(MAX_STEPS - len(state)):
        situation = render.render(task, state)
        done = {s["tool"] for s in state}
        top = await next_taught(conn, situation, done)
        log("step", f"sim={top['sim'] if top else 'none'} "
            f"-> {json.dumps(top['action']) if top else 'no edges'}")
        if top is None or top["sim"] < STEP_SIM_MIN:
            return await _suggest(conn, chat_id, task, state, situation, top)
        action = top["action"]
        if action.get("kind") == "verdict":
            return await _analyze(conn, task, state, failures)
        args = fill_args(action.get("args_hint"), task)
        if args is None:
            return await _suggest(conn, chat_id, task, state, situation, top)
        result = await call_tool(conn, action["tool"], args)
        if isinstance(result, dict) and result.get("error"):
            failures.append(f"{action['tool']}: {str(result['error'])[:120]}")
        text, features = render.summarize(action["tool"], result)
        state.append({"tool": action["tool"], "text": text, "features": features,
                      "raw": json.dumps(result, default=str)[:1500]})
    return await _analyze(conn, task, state, failures)


async def _analyze(conn, task: str, state: list, failures: list) -> str:
    from . import llm
    gathered = "\n".join(f"- {s['tool']}: {s['raw']}" for s in state) or "(nothing)"
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
    if not state:
        reply += "\n\n⚠️ System note — NO checks were run for this answer."
    return reply


async def _suggest(conn, chat_id, task, state, situation, top) -> str:
    from . import llm
    raw = (await llm.complete(prompt.SUGGEST, [{"role": "user", "content":
           f"{situation}\n\nNearest teaching (too far, sim="
           f"{top['sim'] if top else 'none'}): "
           f"{json.dumps(top['action']) if top else 'none'}"}])).strip()
    try:
        s = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
    except Exception:
        s = {"tool": None, "why": raw[:200]}
    PENDING[chat_id] = {"task": task, "state": state, "suggestion": s,
                       "situation": situation}
    found = "\n".join(f"- {x['text']}" for x in state) or "- nothing yet"
    return (f"My teachings don't cover this situation. Found so far:\n{found}\n\n"
            f"I suggest next: {s.get('tool')}({json.dumps(s.get('args', {}))}) — "
            f"{s.get('why', '')}\nApprove, or teach me what to do instead.\n"
            f"(ask 'what can you do' for tools · 'show trace' for internals · "
            f"'what do you know about X' for my teachings)")
