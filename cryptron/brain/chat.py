"""The dialogue transport: Telegram long-poll in, replies out — with inline
buttons for his approvals (his design): 📘 Bank the detected guide, ▶ Go run
the suggested next step, ✖ Close to dismiss so nothing gets pressed by
mistake. Buttons vanish once used. Reasoning lives in agent.py.

Run:  python -m cryptron.brain.chat
"""
import asyncio

import httpx

from .. import config, db
from . import session
from .agent import answer


async def connect_memory():
    for attempt in range(5):
        try:
            return db.get_conn()
        except Exception as e:
            print(f"db connect failed ({e}); retry {attempt + 1}/5", flush=True)
            await asyncio.sleep(10)
    raise SystemExit("could not reach memory after 5 attempts")


def keyboard(chat_id: str) -> dict | None:
    """Buttons for whatever approvals are pending after this turn."""
    s = session.of(chat_id)
    row = []
    if s.get("bank"):
        row.append({"text": "📘 Bank guide", "callback_data": "bank"})
    if s.get("next"):
        row.append({"text": "▶ Go", "callback_data": "go"})
    if row:
        row.append({"text": "✖", "callback_data": "close"})
        return {"inline_keyboard": [row]}
    return None


async def send(client, api: str, chat_id: str, text: str) -> None:
    payload = {"chat_id": chat_id, "text": text[:4000]}
    kb = keyboard(chat_id)
    if kb:
        payload["reply_markup"] = kb
    await client.post(f"{api}/sendMessage", json=payload)


async def handle(conn, client, api: str, chat_id: str, text: str) -> None:
    print(f"user: {text[:80]}", flush=True)
    try:
        reply = await answer(conn, chat_id, text)
    except Exception as e:
        reply = f"Brain error: {type(e).__name__}: {e}"
    try:
        await send(client, api, chat_id, reply)
    except Exception as e:
        print(f"send failed ({type(e).__name__}): {reply[:60]}", flush=True)
    print(f"cryptron: {reply[:80]}", flush=True)


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
                try:
                    db.set_cursor(conn, "chat", chat_id, str(upd["update_id"]))
                except Exception:  # memory connection died — reconnect once
                    conn = await connect_memory()
                    db.set_cursor(conn, "chat", chat_id, str(upd["update_id"]))

                cq = upd.get("callback_query")
                if cq and str(cq["message"]["chat"]["id"]) == chat_id:
                    await client.post(f"{api}/answerCallbackQuery",
                                      json={"callback_query_id": cq["id"]})
                    await client.post(f"{api}/editMessageReplyMarkup", json={
                        "chat_id": chat_id,
                        "message_id": cq["message"]["message_id"]})
                    if cq["data"] == "close":
                        s = session.of(chat_id)
                        s["next"], s["bank"] = None, None
                        continue
                    await handle(conn, client, api, chat_id, cq["data"])
                    continue

                msg = upd.get("message") or {}
                if str(msg.get("chat", {}).get("id")) != chat_id or not msg.get("text"):
                    continue
                await handle(conn, client, api, chat_id, msg["text"])


if __name__ == "__main__":
    asyncio.run(main())
