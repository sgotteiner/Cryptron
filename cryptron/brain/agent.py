"""answer() — his turn contract: approvals first ('go'/'bank'), then do what
he asked (fast path or graph walk), then ALWAYS: guide-detection ask + a
suggested next step. The chat is both the assistant and the console."""
from ..log import log
from . import assist, router, session, steps, turns
from .dispatch import call_tool


async def fast_path(conn, chat_id: str, user_text: str, messages: list) -> str | None:
    """Data question -> ONE retrieval -> the numbers. Every executed tool also
    lands in the session state so suggestions and teachings see it."""
    recent = "\n".join(m["content"][:200] for m in messages[-6:])
    plan = await router.route(user_text, recent)
    if not plan or "escalate" in plan:
        log("route", f"to-graph: {(plan or {}).get('escalate', 'router failed')}")
        return None
    if "sql" in plan:
        name, args = "sql", {"query": plan["sql"]}
    elif plan.get("tool") in router.FAST_TOOLS:
        name, args = plan["tool"], plan.get("args", {})
    else:
        return None
    result = await call_tool(conn, name, args)
    if isinstance(result, dict) and result.get("error"):
        return None  # cheap path failed — the graph flow can handle it
    if name in router.VERBATIM:  # internals: exact, and NOT investigation steps
        return result.get("text", str(result))
    from . import render
    text, _ = render.summarize(name, result)
    import json
    session.add_step(chat_id, name, text, json.dumps(result, default=str))
    return await router.compose(user_text, result)


async def answer(conn, chat_id: str, user_text: str) -> str:
    log("user", user_text)
    turns.save_turn(conn, chat_id, "user", user_text)

    reply = await assist.handle_approvals(conn, chat_id, user_text)
    if reply is None:
        session.set_task(chat_id, user_text)
        guide = await assist.detect_guidance(conn, chat_id, user_text)
        messages = turns.history(conn, chat_id)
        reply = await fast_path(conn, chat_id, user_text, messages)
        if reply is None:
            if guide:  # a pure teaching asks to be banked — nothing to "do"
                reply = guide.strip()
                guide = ""
            else:
                reply = await steps.run(conn, chat_id, user_text)
        reply += guide
        reply += await assist.suggest_next(conn, chat_id)

    log("reply", reply[:500])
    turns.save_turn(conn, chat_id, "assistant", reply)
    return reply
