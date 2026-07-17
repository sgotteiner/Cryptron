"""Coin-level DEX pricing on top of the pool API (dex.py): pick the right
pool, serve candles in the CEX hand's shape, summarize a moment.

This is what makes gem coins priceable: the fallback venue for outcomes
labeling and the DEX twin of price_summary for the brain.
"""
from datetime import datetime, timedelta, timezone

from . import dex


async def best_pool(conn, coin: str) -> dict | None:
    """The coin's most liquid pool — exact base-symbol match only (search
    matches substrings: 'WIF' also finds 'WIFSEM')."""
    found = await dex.search(conn, coin, top=10)
    symbol = coin.upper().strip().lstrip("$#")
    exact = [p for p in found.get("pools", [])
             if (p["name"] or "").upper().split("/")[0].strip().lstrip("$") == symbol]
    return max(exact, key=lambda p: float(p["liquidity_usd"] or 0)) if exact else None


async def coin_ohlcv(conn, coin: str, since: datetime, days: float) -> dict | None:
    """Candles for a coin from its best DEX pool, in the CEX hand's shape
    ([ms, o, h, l, c, v], from `since`) — the pricing fallback for gems."""
    pool = await best_pool(conn, coin)
    if pool is None:
        return None
    end = min(since + timedelta(days=days), datetime.now(timezone.utc))
    timeframe = "hour" if days <= 40 else "day"  # 1000-candle API cap
    try:  # ask only for the window's candles — OHLCV is the throttled endpoint
        candles = await dex.fetch_ohlcv(pool["network"], pool["address"],
                                        timeframe, before=end,
                                        limit=int(days * 24) + 24)
    except Exception as e:  # one stubborn pool must cost one row, not the sweep
        print(f"  dex fallback {coin}: {type(e).__name__}: {e}", flush=True)
        return None
    candles = [[c[0] * 1000] + c[1:] for c in candles
               if c[0] >= since.timestamp()]
    if not candles:
        return None
    return {"exchange": f"dex:{pool['network']}", "symbol": pool["name"],
            "timeframe": timeframe, "candles": candles}


async def price_summary(conn, coin: str, since_iso: str, days_before: float = 7,
                        days_after: float = 30) -> dict:
    """What the coin did around a moment — the DEX twin of price_summary."""
    pool = await best_pool(conn, coin)
    if pool is None:
        return {"coin": coin, "error": "no DEX pool whose base token is exactly "
                "this symbol"}

    since = datetime.fromisoformat(since_iso.replace("Z", "+00:00"))
    if since.tzinfo is None:
        since = since.replace(tzinfo=timezone.utc)
    end = min(since + timedelta(days=days_after), datetime.now(timezone.utc))
    window_days = days_before + (end - since).days + 1
    timeframe = "hour" if window_days <= 40 else "day"  # 1000-candle API cap

    candles = await dex.fetch_ohlcv(pool["network"], pool["address"], timeframe,
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
