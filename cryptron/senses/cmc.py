"""The CMC sense: snapshot market state per watched coin into sense_cmc.

Snapshot sense — no native item id. observed_at is fetch time; every run
appends. This data is ephemeral: not captured now means gone forever.

Uses the official CoinMarketCap API (free tier). Needs CMC_API_KEY in .env.
Run:  python -m cryptron.senses.cmc
"""
import asyncio
from datetime import datetime, timezone

import httpx

from .. import config, db

SENSE = "cmc"
TABLE = "sense_cmc"
API = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"


async def capture_target(client: httpx.AsyncClient, conn, target: dict) -> int:
    source_id = target["source_id"]
    symbols = [s.upper() for s in target["symbols"]]
    now = datetime.now(timezone.utc)

    resp = await client.get(API, params={"symbol": ",".join(symbols), "convert": "USD"})
    resp.raise_for_status()
    data = resp.json()["data"]

    rows = []
    for symbol in symbols:
        coin = data.get(symbol)
        if coin is None:  # unknown symbol — skip, don't fail the batch
            print(f"{source_id}: CMC doesn't know {symbol}, skipped")
            continue
        rows.append({
            "coin": symbol,
            "observed_at": now,
            "source_id": source_id,
            "payload": coin,  # full API object: quote.USD, cmc_rank, supply, ...
        })

    inserted = db.insert_sense_rows(conn, TABLE, rows)
    db.set_cursor(conn, SENSE, source_id, now.isoformat())
    return inserted


async def lookup(conn, symbols: list[str]) -> dict:
    """On-demand market lookup for ANY coin — and capture what was sensed.

    The brain's live CMC hand. Every lookup is also written to sense_cmc
    (source_id 'lookup'): ephemeral data, saved the moment it is seen.
    """
    headers = {"X-CMC_PRO_API_KEY": config.require("CMC_API_KEY")}
    symbols = [s.upper().lstrip("$") for s in symbols]
    now = datetime.now(timezone.utc)
    async with httpx.AsyncClient(headers=headers, timeout=30) as client:
        resp = await client.get(API, params={"symbol": ",".join(symbols),
                                             "convert": "USD"})
        if resp.status_code != 200:
            return {"error": f"CMC returned {resp.status_code}"}
        data = resp.json()["data"]

    out, rows = {}, []
    for s in symbols:
        coin = data.get(s)
        if not coin:
            out[s] = {"error": "unknown to CMC"}
            continue
        q = coin["quote"]["USD"]
        out[s] = {"price": q["price"], "market_cap": q["market_cap"],
                  "volume_24h": q["volume_24h"],
                  "change_24h_pct": q["percent_change_24h"],
                  "rank": coin.get("cmc_rank")}
        rows.append({"coin": s, "observed_at": now, "source_id": "lookup",
                     "payload": coin})
    if rows:
        db.insert_sense_rows(conn, TABLE, rows)
    return out


async def capture_all(conn, targets: list[dict]) -> None:
    headers = {"X-CMC_PRO_API_KEY": config.require("CMC_API_KEY")}
    async with httpx.AsyncClient(headers=headers, timeout=30) as client:
        for target in targets:
            n = await capture_target(client, conn, target)
            print(f"{target['source_id']}: {n} snapshots captured")


async def main() -> None:
    targets = config.load_targets().get(SENSE, [])
    if not targets:
        raise SystemExit("No cmc targets in targets.yaml")
    conn = db.get_conn()
    db.init_schema(conn)
    await capture_all(conn, targets)
    conn.close()


if __name__ == "__main__":
    asyncio.run(main())
