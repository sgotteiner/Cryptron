"""The dialogue: Telegram bot listener -> LLM brain -> tools -> reply.

Run:  python -m cryptron.brain.chat
Only answers the configured TELEGRAM_CHAT_ID. Every turn (both sides) is
captured into sense_chat — the user's guidance is evidence.
"""
import asyncio
import json
import os
from datetime import datetime, timezone

import httpx

from .. import config, db
from . import llm, prompt, tools

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
        if name == "record_experiment":
            return tools.record_experiment(conn, **args)
        if name == "save_find":
            return tools.save_find(**args)
        return {"error": f"no such tool: {name}"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def save_turn(conn, chat_id: str, role: str, text: str, message_id=None) -> None:
    db.insert_sense_rows(conn, "sense_chat", [{
        "coin": None, "observed_at": datetime.now(timezone.utc), "source_id": chat_id,
        "payload": {"role": role, "text": text, "message_id": message_id}}])


def history(conn, chat_id: str, n: int = 16) -> list:
    rows = conn.execute("""
        SELECT payload->>'role', payload->>'text' FROM sense_chat
        WHERE source_id = %s ORDER BY id DESC LIMIT %s""", (chat_id, n)).fetchall()
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]


async def answer(conn, chat_id: str, user_text: str) -> str:
    save_turn(conn, chat_id, "user", user_text)
    messages = history(conn, chat_id)
    for _ in range(MAX_STEPS):
        raw = (await llm.complete(prompt.SYSTEM, messages)).strip()
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            action = json.loads(raw)
        except json.JSONDecodeError:
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


async def main() -> None:
    token = config.require("TELEGRAM_BOT_TOKEN")
    chat_id = config.require("TELEGRAM_CHAT_ID")
    api = f"https://api.telegram.org/bot{token}"
    conn = None
    for attempt in range(5):  # transient network blips must not kill the ear
        try:
            conn = db.get_conn()
            break
        except Exception as e:
            print(f"db connect failed ({e}); retry {attempt + 1}/5", flush=True)
            await asyncio.sleep(10)
    if conn is None:
        raise SystemExit("could not reach memory after 5 attempts")
    db.init_schema(conn)
    offset = db.get_cursor(conn, "chat", chat_id)
    offset = int(offset) + 1 if offset else None
    print("Cryptron dialogue listening...", flush=True)

    async with httpx.AsyncClient(timeout=70) as client:
        while True:
            r = await client.get(f"{api}/getUpdates",
                                 params={"timeout": 50, **({"offset": offset} if offset else {})})
            for upd in r.json().get("result", []):
                offset = upd["update_id"] + 1
                db.set_cursor(conn, "chat", chat_id, str(upd["update_id"]))
                msg = upd.get("message") or {}
                if str(msg.get("chat", {}).get("id")) != chat_id or not msg.get("text"):
                    continue
                print(f"user: {msg['text'][:80]}", flush=True)
                try:
                    reply = await answer(conn, chat_id, msg["text"])
                except Exception as e:
                    reply = f"Brain error: {type(e).__name__}: {e}"
                await client.post(f"{api}/sendMessage",
                                  json={"chat_id": chat_id, "text": reply[:4000]})
                print(f"cryptron: {reply[:80]}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
