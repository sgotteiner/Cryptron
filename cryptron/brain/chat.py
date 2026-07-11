"""The dialogue transport: Telegram long-poll in, replies out.

Run:  python -m cryptron.brain.chat
Only answers the configured TELEGRAM_CHAT_ID. The reasoning lives in
agent.py; this file is pure plumbing, built to survive network blips.
"""
import asyncio

import httpx

from .. import config, db
from .agent import answer


async def connect_memory():
    for attempt in range(5):
        try:
            return db.get_conn()
        except Exception as e:
            print(f"db connect failed ({e}); retry {attempt + 1}/5", flush=True)
            await asyncio.sleep(10)
    raise SystemExit("could not reach memory after 5 attempts")


async def main() -> None:
    token = config.require("TELEGRAM_BOT_TOKEN")
    chat_id = config.require("TELEGRAM_CHAT_ID")
    api = f"https://api.telegram.org/bot{token}"
    conn = await connect_memory()
    db.init_schema(conn)
    offset = db.get_cursor(conn, "chat", chat_id)
    offset = int(offset) + 1 if offset else None
    print("Cryptron dialogue listening...", flush=True)

    async with httpx.AsyncClient(timeout=70) as client:
        while True:
            try:  # a network blip must never kill the ear
                r = await client.get(f"{api}/getUpdates",
                                     params={"timeout": 50,
                                             **({"offset": offset} if offset else {})})
                updates = r.json().get("result", [])
            except Exception as e:
                print(f"poll error ({type(e).__name__}); retrying in 5s", flush=True)
                await asyncio.sleep(5)
                continue
            for upd in updates:
                offset = upd["update_id"] + 1
                msg = upd.get("message") or {}
                try:
                    db.set_cursor(conn, "chat", chat_id, str(upd["update_id"]))
                except Exception:  # memory connection died — reconnect once
                    conn = await connect_memory()
                    db.set_cursor(conn, "chat", chat_id, str(upd["update_id"]))
                if str(msg.get("chat", {}).get("id")) != chat_id or not msg.get("text"):
                    continue
                print(f"user: {msg['text'][:80]}", flush=True)
                try:
                    reply = await answer(conn, chat_id, msg["text"])
                except Exception as e:
                    reply = f"Brain error: {type(e).__name__}: {e}"
                try:
                    await client.post(f"{api}/sendMessage",
                                      json={"chat_id": chat_id, "text": reply[:4000]})
                except Exception as e:
                    print(f"send failed ({type(e).__name__}): {reply[:60]}", flush=True)
                print(f"cryptron: {reply[:80]}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
