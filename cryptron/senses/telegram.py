"""The Telegram sense: capture group messages into sense_telegram.

Dumb and reliable (memory_design.md §7): no parsing, no filtering beyond
service messages. Raw capture at sense-time; enrichment happens later.

Run:  python -m cryptron.senses.telegram
First run asks for the Telegram login code (interactive, once); the session
file is reused afterwards.
"""
import asyncio

from telethon import TelegramClient

from .. import config, db

SENSE = "telegram"
TABLE = "sense_telegram"
SESSION = str(config.ROOT / "cryptron")


def _row(source_id: str, m) -> dict:
    return {
        "coin": None,  # filled by enrichment later, not by the collector
        "observed_at": m.date,
        "source_id": source_id,
        "payload": {
            "message_id": m.id,
            "text": m.message or "",
            "sender_id": getattr(m, "sender_id", None),
            "has_media": m.media is not None,
            "views": getattr(m, "views", None),
            "forwards": getattr(m, "forwards", None),
            "reply_to": m.reply_to_msg_id,
        },
    }


async def capture_target(client: TelegramClient, conn, target: dict) -> int:
    source_id = target["source_id"]
    entity = await client.get_entity(target["link"])
    cursor = db.get_cursor(conn, SENSE, source_id)

    if cursor is None:
        # First run: backfill the latest N messages.
        kwargs = {"limit": int(target.get("backfill", 200))}
    else:
        # Resume: everything newer than the cursor.
        kwargs = {"min_id": int(cursor)}

    rows, max_id = [], int(cursor) if cursor else 0
    async for m in client.iter_messages(entity, **kwargs):
        if m.action is not None:  # service message (join/pin/...), not content
            continue
        rows.append(_row(source_id, m))
        max_id = max(max_id, m.id)

    inserted = db.insert_sense_rows(conn, TABLE, rows)
    if max_id:
        db.set_cursor(conn, SENSE, source_id, str(max_id))
    return inserted


async def main() -> None:
    targets = config.load_targets().get(SENSE, [])
    if not targets:
        raise SystemExit("No telegram targets in targets.yaml")

    conn = db.get_conn()
    db.init_schema(conn)

    api_id, api_hash, phone = config.telegram_credentials()
    client = TelegramClient(SESSION, api_id, api_hash)
    await client.start(phone=phone)

    async with client:
        for target in targets:
            n = await capture_target(client, conn, target)
            print(f"{target['source_id']}: {n} new messages captured")
    conn.close()


if __name__ == "__main__":
    asyncio.run(main())
