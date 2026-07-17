"""The reasoning loop: user message -> LLM + tools -> reply, all captured."""
import json

from ..hands import background, dex, dex_price
from ..log import log
from ..memory import finds, paths, recall
from ..senses import coingecko
from . import llm, outcomes, reflex, social, tools, turns

MAX_STEPS = 12

PROTOCOL_NUDGE = (
    'PROTOCOL VIOLATION: your ENTIRE output must be ONE JSON object — '
    '{"tool": ..., "args": ...} or {"reply": "..."}. If you described tools or '
    'numbers in prose, you did NOT run them: no result exists. Run the real tool '
    'now, or wrap your answer in {"reply": "..."} containing ONLY facts that '
    'appear in a TOOL RESULT above.')


async def run_tool(conn, name: str, args: dict) -> dict:
    try:
        if name == "sources":
            return tools.sources(conn)
        if name == "calls":
            return tools.calls(conn, **args)
        if name == "price_summary":
            return await tools.price_summary(**args)
        if name == "score":
            return await tools.score(conn, **args)
        if name == "sql":
            return tools.sql(conn, **args)
        if name == "cmc_lookup":
            return await tools.cmc_lookup(conn, **args)
        if name == "exchanges":
            return await tools.exchanges(**args)
        if name == "dex_search":
            return await dex.search(conn, **args)
        if name == "dex_price_summary":
            return await dex_price.price_summary(conn, **args)
        if name == "dex_trending":
            return await dex.trending(conn, **args)
        if name == "mentions":
            return social.mentions(conn, **args)
        if name == "sentiment":
            return await coingecko.lookup(conn, **args)
        if name == "fear_greed":
            return social.fear_greed(conn)
        if name == "tv_search":
            return await tools.tv_search(**args)
        if name == "tv_ohlcv":
            return await tools.tv_ohlcv(**args)
        if name == "save_guidance":
            return paths.save_guidance(conn, **args)
        if name == "open_thread":
            return paths.open_thread(conn, **args)
        if name == "replay_thread":
            return paths.replay(conn, **args)
        if name == "capture_background":
            return await background.capture(conn, **args)
        if name == "label_calls":
            return await outcomes.label_calls(conn, **args)
        if name == "record_experiment":
            return await tools.record_experiment(conn, **args)
        if name == "save_find":
            return await finds.save_find(conn, **args)
        if name == "update_find":
            return await finds.update_find(conn, **args)
        if name == "recall":
            return await recall.recall(conn, **args)
        if name == "finds_in_scope":
            return recall.in_scope(conn, **args)
        if name == "read_find":
            return recall.read(conn, **args)
        return {"error": f"no such tool: {name}"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


async def call_tool(conn, name: str, args: dict) -> dict:
    """run_tool + the logbook: args in, result or FAILURE out — always visible."""
    log("tool", f"{name} {json.dumps(args, default=str)}")
    result = await run_tool(conn, name, args)
    if isinstance(result, dict) and result.get("error"):
        log("TOOL-FAIL", f"{name}: {result['error']}")
    else:
        log("result", json.dumps(result, default=str)[:800])
    return result


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


async def answer(conn, chat_id: str, user_text: str) -> str:
    log("user", user_text)
    turns.save_turn(conn, chat_id, "user", user_text)
    messages = turns.history(conn, chat_id)
    system = turns.system_prompt(conn)
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
                         "content": f"TOOL RESULT {name}: {json.dumps(result)[:6000]}"})
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
