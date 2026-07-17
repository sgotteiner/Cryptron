"""The reasoning loop: user message -> LLM + tools -> reply, all captured."""
import json
from datetime import datetime, timezone

from .. import db
from ..hands import dex
from ..memory import finds, paths, recall
from ..senses import coingecko
from . import llm, outcomes, prompt, social, tools

MAX_STEPS = 8


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
            return await dex.price_summary(conn, **args)
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


async def answer(conn, chat_id: str, user_text: str) -> str:
    save_turn(conn, chat_id, "user", user_text)
    messages = history(conn, chat_id)
    system = system_prompt(conn)
    for _ in range(MAX_STEPS):
        raw = (await llm.complete(system, messages)).strip()
        action = extract_action(raw)
        if action is None:
            reply = raw  # model spoke plain text — accept it
            break
        if "reply" in action:
            reply = action["reply"]
            break
        name, args = action.get("tool"), action.get("args", {})
        print(f"  tool: {name}({json.dumps(args)[:100]})", flush=True)
        result = await run_tool(conn, name, args)
        messages.append({"role": "assistant", "content": raw})
        messages.append({"role": "user",
                         "content": f"TOOL RESULT {name}: {json.dumps(result)[:6000]}"})
    else:
        reply = "I ran out of steps mid-investigation — ask me to continue."
    save_turn(conn, chat_id, "assistant", reply)
    return reply
