"""The CoinGecko sense: per-coin crowd sentiment into sense_coingecko.

The score the experiments can use: community bullish/bearish vote %, watchlist
users, telegram/reddit community size + activity. Free, keyless (tight rate
limit ~10/min — fine for lookups; a free demo key raises it if ever needed).
Votes are ephemeral: today's 50/50 is gone tomorrow — every lookup is captured,
and history accumulates from the day we start (§6.4: no second chance).

Run:  python -m cryptron.senses.coingecko
"""
import asyncio
from datetime import datetime, timezone

import httpx

from .. import config, db

SENSE = "coingecko"
TABLE = "sense_coingecko"
API = "https://api.coingecko.com/api/v3"
UA = {"User-Agent": "cryptron/1.0 (crypto research agent)", "Accept": "application/json"}


async def _fetch(client: httpx.AsyncClient, symbol: str) -> dict | None:
    """symbol -> the sentiment/community slice of CoinGecko's coin object."""
    found = await client.get(f"{API}/search", params={"query": symbol})
    found.raise_for_status()
    coins = [c for c in found.json()["coins"]
             if c["symbol"].upper() == symbol] or found.json()["coins"]
    if not coins:
        return None
    resp = await client.get(f"{API}/coins/{coins[0]['id']}", params={
        "localization": "false", "tickers": "false", "market_data": "false",
        "community_data": "true", "developer_data": "false"})
    resp.raise_for_status()
    d, com = resp.json(), resp.json().get("community_data") or {}
    return {
        "coingecko_id": d["id"], "name": d.get("name"),
        "sentiment_up_pct": d.get("sentiment_votes_up_percentage"),
        "sentiment_down_pct": d.get("sentiment_votes_down_percentage"),
        "watchlist_users": d.get("watchlist_portfolio_users"),
        "market_cap_rank": d.get("market_cap_rank"),
        "telegram_users": com.get("telegram_channel_user_count"),
        "reddit_subscribers": com.get("reddit_subscribers"),
        "reddit_posts_48h": com.get("reddit_average_posts_48h"),
        "reddit_comments_48h": com.get("reddit_average_comments_48h"),
    }


async def lookup(conn, coin: str) -> dict:
    """The brain's sentiment hand — and every lookup is captured."""
    symbol = coin.upper().strip().lstrip("$#")
    async with httpx.AsyncClient(headers=UA, timeout=30) as client:
        try:
            data = await _fetch(client, symbol)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                return {"error": "CoinGecko rate limit — retry in a minute"}
            raise
    if data is None:
        return {"coin": symbol, "error": "unknown to CoinGecko"}
    db.insert_sense_rows(conn, TABLE, [{
        "coin": symbol, "observed_at": datetime.now(timezone.utc),
        "source_id": "lookup", "payload": data}])
    return {"coin": symbol, **data,
            "note": "votes are today's snapshot; history accumulates in sense_coingecko"}


async def capture_all(conn, targets: list[dict]) -> None:
    for target in targets:
        for symbol in target["symbols"]:
            res = await lookup(conn, symbol)
            ok = "error" not in res
            print(f"{target['source_id']}: {symbol} "
                  f"{'captured' if ok else 'failed (' + res['error'] + ')'}")
            await asyncio.sleep(7)  # keyless budget: stay under ~10 calls/min


async def main() -> None:
    targets = config.load_targets().get(SENSE, [])
    if not targets:
        raise SystemExit("No coingecko targets in targets.yaml")
    conn = db.get_conn()
    db.init_schema(conn)
    await capture_all(conn, targets)
    conn.close()


if __name__ == "__main__":
    asyncio.run(main())
