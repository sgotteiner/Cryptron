"""The reasoning loops: fast path for data questions, the investigator loop
for judgment — every action logged, every failure disclosed."""
import json

from ..log import log
from . import llm, reflex, router, turns
from .dispatch import call_tool

MAX_STEPS = 12

PROTOCOL_NUDGE = (
    'PROTOCOL VIOLATION: your ENTIRE output must be ONE JSON object — '
    '{"tool": ..., "args": ...} or {"reply": "..."}. If you described tools or '
    'numbers in prose, you did NOT run them: no result exists. Run the real tool '
    'now, or wrap your answer in {"reply": "..."} containing ONLY facts that '
    'appear in a TOOL RESULT above.')


def extract_action(raw: str) -> dict | None:
    """Find the JSON action even when the model wraps it in prose."""
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    decoder = json.JSONDecoder()
    idx = 0
    while (start := raw.find("{", idx)) != -1:
        try:
            obj, _ = decoder.raw_decode(raw[start:])
            if isinstance(obj, dict) and ("tool" in obj or "reply" in obj):
                return obj
        except json.JSONDecodeError:
            pass
        idx = start + 1
    return None


async def fast_path(conn, user_text: str, messages: list) -> str | None:
    """His design: data question -> ONE simple retrieval -> the numbers. The
    full investigator brain is reserved for judgment; escalation is the router
    saying so. Returns the reply, or None to escalate."""
    recent = "\n".join(m["content"][:200] for m in messages[-4:])
    plan = await router.route(user_text, recent)
    if not plan or "escalate" in plan:
        log("route", f"escalate: {(plan or {}).get('escalate', 'router failed')}")
        return None
    if "sql" in plan:
        name, args = "sql", {"query": plan["sql"]}
    elif plan.get("tool") in router.FAST_TOOLS:
        name, args = plan["tool"], plan.get("args", {})
    else:
        return None
    result = await call_tool(conn, name, args)
    if isinstance(result, dict) and result.get("error"):
        return None  # cheap path failed — let the full brain handle it
    return await router.compose(user_text, result)


async def answer(conn, chat_id: str, user_text: str) -> str:
    log("user", user_text)
    turns.save_turn(conn, chat_id, "user", user_text)
    messages = turns.history(conn, chat_id)
    reply = await fast_path(conn, user_text, messages)
    if reply is not None:
        lesson = await reflex.learn(conn, user_text)
        if lesson:
            reply += f"\n\n📘 Learned (will apply automatically): {lesson}"
        log("reply", reply[:500])
        turns.save_turn(conn, chat_id, "assistant", reply)
        return reply
    system = await turns.system_prompt(conn, user_text)
    failures, tools_run, bounces = [], 0, 0
    for _ in range(MAX_STEPS):
        raw = (await llm.complete(system, messages)).strip()
        action = extract_action(raw)
        if action is None:  # protocol break: bounce it back, don't accept prose
            log("plaintext", raw[:300])
            if bounces < 2:
                bounces += 1
                messages.append({"role": "assistant", "content": raw})
                messages.append({"role": "user", "content": PROTOCOL_NUDGE})
                continue
            reply = raw  # refused thrice — the no-tools footer below discloses
            break
        if "reply" in action:
            reply = action["reply"]
            break
        name, args = action.get("tool"), action.get("args", {})
        result = await call_tool(conn, name, args)
        tools_run += 1
        if isinstance(result, dict) and result.get("error"):
            failures.append(f"{name}: {str(result['error'])[:150]}")
        messages.append({"role": "assistant", "content": raw})
        messages.append({"role": "user",
                         "content": f"TOOL RESULT {name}: {json.dumps(result)[:2500]}"})
    else:
        reply = "I ran out of steps mid-investigation — ask me to continue."

    # Mechanical honesty: disclosures reach the user by CODE, not model choice.
    if failures:
        reply += ("\n\n⚠️ System note — these checks FAILED this turn (my answer "
                  "may be incomplete): " + " | ".join(failures))
    if tools_run == 0:
        reply += ("\n\n⚠️ System note — NO checks were run this turn: the above "
                  "comes from conversation memory, not fresh data.")
    lesson = await reflex.learn(conn, user_text)
    if lesson:
        reply += f"\n\n📘 Learned (will apply automatically): {lesson}"
    log("reply", reply[:500])
    turns.save_turn(conn, chat_id, "assistant", reply)
    return reply
