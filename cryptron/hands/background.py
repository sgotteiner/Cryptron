"""The background hand: snapshot everything knowable about recent calls, batched.

"Add data about the last N signals" is a batch job, not a chat loop — running it
tool-call-by-tool-call burns the brain's steps and bursts into rate limits. This
hand does the whole sweep in ONE call: for each of a group's recent calls, snapshot
its DEX pools (sense_dex) and crowd sentiment (sense_coingecko), paced to respect
the free-tier budgets. The knowledge base grows; comparisons JOIN on it later.
"""
import asyncio

from .. import tickers
from ..senses import coingecko
from . import dex

PACE_S = 16  # CoinGecko keyless is the binding budget: 2 calls/lookup, ~10/min


async def capture(conn, source_id: str, n: int = 10) -> dict:
    coins = tickers.recent_called(conn, [source_id], n)
    if not coins:
        return {"source_id": source_id, "error": "no calls found for this group"}
    results = []
    for coin in coins:
        pools = await dex.search(conn, coin)
        senti = await coingecko.lookup(conn, coin)
        if "rate limit" in str(senti.get("error", "")):
            await asyncio.sleep(65)
            senti = await coingecko.lookup(conn, coin)
        results.append({
            "coin": coin,
            "dex_pools": len(pools.get("pools", [])) or pools.get("error", 0),
            "sentiment": "captured" if "error" not in senti else senti["error"]})
        await asyncio.sleep(PACE_S)
    return {"source_id": source_id, "coins": len(results), "results": results,
            "note": "snapshots persisted (sense_dex + sense_coingecko); "
                    "JOIN against call_outcomes to compare"}
