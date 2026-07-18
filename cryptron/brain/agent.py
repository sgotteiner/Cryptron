"""answer(): the three-way brain — pending teaching resumes, data questions
take the fast path, everything else walks the taught situation graph.
The old free-improvising loop is gone (his design: steps come from teachings;
the LLM only judges gathered data and suggests when teachings run thin)."""
from ..log import log
from . import reflex, router, steps, teach, turns
from .dispatch import call_tool


async def fast_path(conn, user_text: str, messages: list) -> str | None:
    """Data question -> ONE simple retrieval -> the numbers (his design).
    Returns the reply, or None to send the task to the situation graph."""
    recent = "\n".join(m["content"][:200] for m in messages[-4:])
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
    if name in router.VERBATIM:  # internals must reach him EXACT, unreworded
        return result.get("text", str(result))
    return await router.compose(user_text, result)


async def answer(conn, chat_id: str, user_text: str) -> str:
    log("user", user_text)
    turns.save_turn(conn, chat_id, "user", user_text)

    reply = await teach.resume(conn, chat_id, user_text)  # pending suggestion?
    if reply is None:
        messages = turns.history(conn, chat_id)
        reply = await fast_path(conn, user_text, messages)
    if reply is None:
        reply = await steps.run(conn, chat_id, user_text)

    lesson = await reflex.learn(conn, user_text)
    if lesson:
        reply += f"\n\n📘 Learned (will apply automatically): {lesson}"
    log("reply", reply[:500])
    turns.save_turn(conn, chat_id, "assistant", reply)
    return reply
