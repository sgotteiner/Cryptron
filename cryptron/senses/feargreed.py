"""The Fear & Greed sense: the market-wide regime index into sense_feargreed.

alternative.me publishes one value per day, free, no key — and serves FULL
history, so the first run backfills years of regime data in one call.
This is fuel for the 'market-adjusted' condition finds already carry.

Run:  python -m cryptron.senses.feargreed
"""
import asyncio
from datetime import datetime, timezone

import httpx

from .. import config, db

SENSE = "feargreed"
TABLE = "sense_feargreed"
API = "https://api.alternative.me/fng/"


async def capture_target(client: httpx.AsyncClient, conn, target: dict) -> int:
    source_id = target["source_id"]
    resp = await client.get(API, params={"limit": int(target.get("limit", 0))})
    resp.raise_for_status()

    rows = [{
        "coin": None,  # market-wide by nature
        "observed_at": datetime.fromtimestamp(int(d["timestamp"]), tz=timezone.utc),
        "source_id": source_id,
        "payload": {"value": int(d["value"]),
                    "classification": d["value_classification"]},
    } for d in resp.json()["data"]]

    inserted = db.insert_sense_rows(conn, TABLE, rows)
    db.set_cursor(conn, SENSE, source_id, datetime.now(timezone.utc).isoformat())
    return inserted


async def capture_all(conn, targets: list[dict]) -> None:
    async with httpx.AsyncClient(timeout=30) as client:
        for target in targets:
            n = await capture_target(client, conn, target)
            print(f"{target['source_id']}: {n} index days captured")


async def main() -> None:
    targets = config.load_targets().get(SENSE, [])
    if not targets:
        raise SystemExit("No feargreed targets in targets.yaml")
    conn = db.get_conn()
    db.init_schema(conn)
    await capture_all(conn, targets)
    conn.close()


if __name__ == "__main__":
    asyncio.run(main())
