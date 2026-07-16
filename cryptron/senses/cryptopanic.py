"""The CryptoPanic sense: aggregated crypto news WITH community votes.

Stream sense — posts have native ids. This is per-coin news + bullish/bearish
crowd sentiment in one feed. Free developer token (sign up at
https://cryptopanic.com/developers/api/) — CRYPTOPANIC_TOKEN in .env.
A conditional sense: no token means it skips politely, never crashes the body.

Run:  python -m cryptron.senses.cryptopanic
"""
import asyncio
import os
from datetime import datetime, timezone

import httpx

from .. import config, db

SENSE = "cryptopanic"
TABLE = "sense_cryptopanic"
API = "https://cryptopanic.com/api/developer/v2/posts/"


def to_row(source_id: str, post: dict) -> dict:
    # v2 attaches 'instruments', v1 'currencies' — accept either shape.
    coins = [c.get("code") for c in
             (post.get("instruments") or post.get("currencies") or [])]
    return {
        "coin": coins[0].upper() if len(coins) == 1 and coins[0] else None,
        "observed_at": datetime.fromisoformat(
            post["published_at"].replace("Z", "+00:00")),
        "source_id": source_id,
        "payload": {**post, "id": str(post["id"])},
    }


async def capture_target(client: httpx.AsyncClient, conn, target: dict,
                         token: str) -> int:
    source_id = target["source_id"]
    params = {"auth_token": token, "public": "true"}
    if target.get("filter"):
        params["filter"] = target["filter"]
    resp = await client.get(API, params=params)
    resp.raise_for_status()

    rows = [to_row(source_id, p) for p in resp.json().get("results", [])]
    inserted = db.insert_sense_rows(conn, TABLE, rows)
    db.set_cursor(conn, SENSE, source_id, datetime.now(timezone.utc).isoformat())
    return inserted


async def capture_all(conn, targets: list[dict]) -> None:
    token = os.environ.get("CRYPTOPANIC_TOKEN", "").strip()
    if not token:
        print("cryptopanic: no CRYPTOPANIC_TOKEN in .env — sense skipped "
              "(free token: https://cryptopanic.com/developers/api/)")
        return
    async with httpx.AsyncClient(timeout=30) as client:
        for target in targets:
            n = await capture_target(client, conn, target, token)
            print(f"{target['source_id']}: {n} new posts captured")
            await asyncio.sleep(1)


async def main() -> None:
    targets = config.load_targets().get(SENSE, [])
    if not targets:
        raise SystemExit("No cryptopanic targets in targets.yaml")
    conn = db.get_conn()
    db.init_schema(conn)
    await capture_all(conn, targets)
    conn.close()


if __name__ == "__main__":
    asyncio.run(main())
