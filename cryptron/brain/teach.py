"""Teaching by approval (his design): a pending suggestion + his reply =
a new taught edge. Failed steps are never taught; args are canonicalized
against the whole flow; near-duplicate edges are absorbed, not added."""
import json

from ..log import log
from ..memory import paths
from ..tickers import find_tickers
from . import render, steps
from .dispatch import call_tool
from .steps import PENDING, fill_args


async def resume(conn, chat_id: str, user_text: str) -> str | None:
    """If a suggestion is pending, his reply teaches: approve -> record edge +
    continue; correction with a tool name -> record HIS step; else drop pending."""
    p = PENDING.pop(chat_id, None)
    if p is None:
        return None
    low = user_text.lower()
    action = None
    if any(w in low for w in ("yes", "ok", "approve", "do it", "go")):
        s = p["suggestion"]
        action = {"tool": s.get("tool"), "args_hint": s.get("args", {})}
    else:
        named = [t for t in ("sentiment", "mentions", "dex_search", "cmc_lookup",
                             "exchanges", "price_summary", "dex_price_summary",
                             "score", "label_calls", "sql", "fear_greed")
                 if t in low]
        if named:
            action = {"tool": named[0], "args_hint": {}}
    if action is None or not action.get("tool"):
        return None  # not about the suggestion — normal flow handles it
    args = dict(action.get("args_hint") or {})
    result = await call_tool(conn, action["tool"],
                             fill_args(args, p["task"]) or args)
    text, features = render.summarize(action["tool"], result)
    p["state"].append({"tool": action["tool"], "text": text, "features": features,
                       "raw": json.dumps(result, default=str)[:1500]})
    failed = isinstance(result, dict) and result.get("error")
    if not failed:  # a FAILED step is never taught — edges must be walkable
        flow_text = p["task"] + " " + " ".join(s["raw"] for s in p["state"])
        hint = json.dumps(args)
        for t in find_tickers(flow_text):  # canonicalize against the WHOLE flow
            hint = hint.replace(f'"{t}"', '"{coin}"').replace(t, "{coin}")
        hint = json.loads(hint)
        known = {"{coin}", "{source_id}"}
        bad = [v for v in json.dumps(hint).split('"')
               if v.startswith("{") and v.endswith("}") and v not in known]
        if not bad:
            taught = await paths.teach_step(
                conn, p["situation"], {"tool": action["tool"], "args_hint": hint},
                lesson_src=f"approved in chat: {user_text[:120]}")
            log("edge", f"{'dup-absorbed' if 'already_taught' in taught else 'taught'}: "
                f"{action['tool']} {json.dumps(hint)}")
    return await steps.run(conn, chat_id, p["task"], p["state"])
