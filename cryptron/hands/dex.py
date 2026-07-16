"""The DEX hand: price/liquidity for coins CEXes can't see, via GeckoTerminal.

Free, no key. This is the gems hand: crypto_gemsignals calls DEX-only coins
that price.py returns None for — this hand can finally score them.
Every search snapshot is captured into sense_dex (a gem pool's price/
liquidity/fdv is exactly the ephemeral data memory exists to keep).
"""
from datetime import datetime, timedelta, timezone

import httpx

from .. import db

API = "https://api.geckoterminal.com/api/v2"
UA = {"User-Agent": "cryptron/1.0 (crypto research agent)", "Accept": "application/json"}


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
        resp = await client.get(f"{API}/search/pools", params={"query": query})
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
        resp = await client.get(f"{API}{path}")
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
        resp = await client.get(
            f"{API}/networks/{network}/pools/{address}/ohlcv/{timeframe}",
            params=params)
        resp.raise_for_status()
    candles = resp.json()["data"]["attributes"]["ohlcv_list"]
    return sorted(candles, key=lambda c: c[0])


async def price_summary(conn, coin: str, since_iso: str, days_before: float = 7,
                        days_after: float = 30) -> dict:
    """What the coin did around a moment — the DEX twin of price_summary."""
    found = await search(conn, coin, top=10)
    if not found.get("pools"):
        return {"coin": coin, "error": found.get("error", "no DEX pool found")}
    # search matches substrings ('WIF' also finds 'WIFSEM') — keep only pools
    # whose base symbol IS the coin, then take the most liquid one
    symbol = coin.upper().strip().lstrip("$#")
    exact = [p for p in found["pools"]
             if (p["name"] or "").upper().split("/")[0].strip().lstrip("$") == symbol]
    if not exact:
        return {"coin": coin, "error": "no pool whose base token is exactly this "
                "symbol; candidates: " + ", ".join(p["name"] for p in found["pools"][:5])}
    pool = max(exact, key=lambda p: float(p["liquidity_usd"] or 0))

    since = datetime.fromisoformat(since_iso.replace("Z", "+00:00"))
    if since.tzinfo is None:
        since = since.replace(tzinfo=timezone.utc)
    end = min(since + timedelta(days=days_after), datetime.now(timezone.utc))
    window_days = days_before + (end - since).days + 1
    timeframe = "hour" if window_days <= 40 else "day"  # 1000-candle API cap

    candles = await fetch_ohlcv(pool["network"], pool["address"], timeframe,
                                before=end)
    start_ts = (since - timedelta(days=days_before)).timestamp()
    candles = [c for c in candles if c[0] >= start_ts]
    before = [c for c in candles if c[0] < since.timestamp()]
    after = [c for c in candles if c[0] >= since.timestamp()]
    if not after:
        return {"coin": coin, "pool": pool["name"],
                "error": "no candles after that moment (pool younger than the call?)"}

    entry = after[0][4]
    out = {"coin": coin, "pool": pool["name"], "network": pool["network"],
           "liquidity_usd": pool["liquidity_usd"], "timeframe": timeframe,
           "entry": entry,
           "after": {"peak_pct": round((max(c[2] for c in after) / entry - 1) * 100, 1),
                     "low_pct": round((min(c[3] for c in after) / entry - 1) * 100, 1),
                     "close_pct": round((after[-1][4] / entry - 1) * 100, 1)}}
    if before:
        out["trend_before"] = {
            "days": days_before,
            "change_pct": round((entry / before[0][4] - 1) * 100, 1)}
    return out
