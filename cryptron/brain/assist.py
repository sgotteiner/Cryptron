"""His turn contract (verbatim, 2026-07-18): every message -> (1) detect
guidance and ASK before banking, (2) do what he asked, (3) ALWAYS suggest a
next step for his approval. 'go' runs it AND teaches the edge; 'bank' saves
the guide. The assistant behavior lives here; execution lives elsewhere."""
import json

from ..log import log
from ..memory import paths
from ..tickers import find_tickers
from . import llm, prompt, render, session, steps
from .dispatch import call_tool

GO = {"go", "yes", "ok", "do it", "ok do it", "approve", "sure"}


async def handle_approvals(conn, chat_id: str, text: str) -> str | None:
    """'bank' saves the pending guide; 'go'/'yes' runs the pending next step
    (and teaches it as an edge). Returns a reply, or None if not an approval."""
    s = session.of(chat_id)
    low = text.lower().strip().rstrip("!.")
    if low.startswith("bank") and s["bank"]:
        lesson = s.pop("bank") or {}
        s["bank"] = None
        saved = await paths.save_guidance(conn, lesson=lesson["lesson"],
                                          why=lesson.get("why", ""))
        note = "banked" if "learned" in saved else "already in the playbook"
        return f"📘 {note}: {lesson['lesson']}" + await suggest_next(conn, chat_id)
    is_go = low in GO or ("go" in low.split() and find_tickers(text))
    if is_go and s["next"]:
        action = s["next"]
        if find_tickers(text):  # 'RECALL, go' — the coin arrives with the go
            s["task"] = f"{s['task']} {find_tickers(text)[0]}".strip()
        args = steps.fill_args(action.get("args_hint"), s["task"])
        if args is None:  # placeholder unresolvable — never run literals
            return ("Which coin/group is this about? Say it with the go "
                    "(e.g. 'RECALL, go') and I'll run the step.")
        s["next"] = None
        result = await call_tool(conn, action["tool"], args)
        text_, feats = render.summarize(action["tool"], result)
        session.add_step(chat_id, action["tool"], text_,
                         json.dumps(result, default=str))
        failed = isinstance(result, dict) and result.get("error")
        if not failed:  # approved + worked -> a taught edge (his teaching)
            situation = render.render(s["task"], session.task_steps(chat_id)[:-1])
            hint = json.dumps(action.get("args_hint", {}))
            for t in find_tickers(s["task"]):
                hint = hint.replace(t, "{coin}")
            await paths.teach_step(conn, situation,
                                   {"tool": action["tool"],
                                    "args_hint": json.loads(hint)},
                                   lesson_src="approved next step")
            log("edge", f"taught: {action['tool']}")
        from . import router
        reply = await router.compose(s["task"] or "the requested check", result)
        return reply + await suggest_next(conn, chat_id)
    return None


async def detect_guidance(conn, chat_id: str, text: str) -> str:
    """Returns the ask-to-bank line (or '') — NEVER banks on its own."""
    from . import reflex
    lesson = await reflex.detect(text)
    if not lesson:
        return ""
    session.of(chat_id)["bank"] = lesson
    return (f"\n\n📘 Guide detected: \"{lesson['lesson']}\" — say 'bank' to save "
            f"it to the playbook.")


async def suggest_next(conn, chat_id: str) -> str:
    """The always-on next step (his rule #3): from the taught graph when it
    knows, from reasoning when it doesn't. 'go' approves."""
    s = session.of(chat_id)
    flow = session.task_steps(chat_id)
    situation = render.render(s["task"] or "ongoing investigation", flow)
    done = {x["tool"] for x in flow}
    action, source = None, ""
    try:
        top = await steps.next_taught(conn, situation, done)
        if top and top["sim"] >= steps.STEP_SIM_MIN and \
                top["action"].get("kind") != "verdict":
            action, source = top["action"], f"your teaching, sim={top['sim']}"
    except Exception as e:
        log("suggest-err", f"{type(e).__name__}: {e}")
    if action is None:
        try:
            raw = (await llm.complete(prompt.SUGGEST, [
                {"role": "user", "content": situation}])).strip()
            sug = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
            if sug.get("tool"):
                action = {"tool": sug["tool"], "args_hint": sug.get("args", {})}
                source = sug.get("why", "my reasoning")
        except Exception as e:
            log("suggest-err", f"{type(e).__name__}: {e}")
    if action is None:
        return ""
    s["next"] = action
    return (f"\n\n▶ Next I suggest: {action['tool']}"
            f"({json.dumps(action.get('args_hint', {}))}) — {source}. "
            f"Say 'go', or tell me what to check instead.")
