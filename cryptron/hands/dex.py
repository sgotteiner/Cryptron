"""The DEX hand: price/liquidity for coins CEXes can't see, via GeckoTerminal.

Free, no key. This is the gems hand: crypto_gemsignals calls DEX-only coins
that price.py returns None for — this hand can finally score them.
Every search snapshot is captured into sense_dex (a gem pool's price/
liquidity/fdv is exactly the ephemeral data memory exists to keep).
"""
import asyncio
from datetime import datetime, timedelta, timezone

import httpx

from .. import db

API = "https://api.geckoterminal.com/api/v2"
UA = {"User-Agent": "cryptron/1.0 (crypto research agent)", "Accept": "application/json"}


async def _get(client: httpx.AsyncClient, url: str, params: dict | None = None):
    """GET with escalating retries on 429 — the free tier's rolling window
    needs real backoff, not one hopeful nudge."""
    for wait in (15, 45):
        resp = await client.get(url, params=params)
        if resp.status_code != 429:
            return resp
        await asyncio.sleep(float(resp.headers.get("retry-after", wait)))
    return await client.get(url, params=params)


def _pool_summary(pool: dict) -> dict:
    a = pool["attributes"]
    # pool id is '{network}_{address}'; split on the address (network ids may
    # themselves contain underscores, e.g. 'polygon_pos')
    net = pool["id"].removesuffix(f"_{a['address']}")
    return {
        "pool_id": pool["id"], "network": net, "address": a["address"],
        "name": a.get("name"),
        "price_usd": a.get("base_token_price_usd"),
        "liquidity_usd": a.get("reserve_in_usd"),
        "fdv_usd": a.get("fdv_usd"),
        "volume_24h_usd": (a.get("volume_usd") or {}).get("h24"),
        "created_at": a.get("pool_created_at"),
    }


async def search(conn, query: str, top: int = 5) -> dict:
    """Find pools for a symbol/name/address — and capture what was sensed."""
    query = query.upper().strip().lstrip("$#")
    now = datetime.now(timezone.utc)
    async with httpx.AsyncClient(headers=UA, timeout=30) as client:
        resp = await _get(client, f"{API}/search/pools", {"query": query})
        if resp.status_code != 200:
            return {"error": f"GeckoTerminal returned {resp.status_code}"}
        pools = [_pool_summary(p) for p in resp.json()["data"][:top]]

    if not pools:
        return {"query": query, "pools": [], "note": "no DEX pool found"}
    db.insert_sense_rows(conn, "sense_dex", [
        {"coin": query, "observed_at": now, "source_id": "lookup", "payload": p}
        for p in pools])
    return {"query": query, "pools": pools}


async def trending(conn, network: str | None = None, top: int = 10) -> dict:
    """Currently-trending DEX pools — the gem radar. Captured like any lookup."""
    path = f"/networks/{network}/trending_pools" if network else "/networks/trending_pools"
    now = datetime.now(timezone.utc)
    async with httpx.AsyncClient(headers=UA, timeout=30) as client:
        resp = await _get(client, f"{API}{path}")
        if resp.status_code != 200:
            return {"error": f"GeckoTerminal returned {resp.status_code}"}
        pools = [_pool_summary(p) for p in resp.json()["data"][:top]]

    source_id = f"trending-{network or 'all'}"
    db.insert_sense_rows(conn, "sense_dex", [
        {"coin": (p["name"] or "").split("/")[0].strip().lstrip("$") or None,
         "observed_at": now, "source_id": source_id, "payload": p}
        for p in pools])
    return {"network": network or "all", "pools": pools}


async def fetch_ohlcv(network: str, address: str, timeframe: str = "hour",
                      before: datetime | None = None, limit: int = 1000) -> list:
    """Candles for one pool, ascending [unix_sec, o, h, l, c, volume]."""
    params = {"aggregate": 1, "limit": min(limit, 1000), "currency": "usd"}
    if before:
        params["before_timestamp"] = int(before.timestamp())
    async with httpx.AsyncClient(headers=UA, timeout=30) as client:
        resp = await _get(
            client, f"{API}/networks/{network}/pools/{address}/ohlcv/{timeframe}",
            params)
        resp.raise_for_status()
    candles = resp.json()["data"]["attributes"]["ohlcv_list"]
    return sorted(candles, key=lambda c: c[0])
