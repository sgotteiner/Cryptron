"""The price hand: fetch OHLCV history for a coin around a moment in time.

Stateless — price history is always re-fetchable (memory_design §3: the one
non-ephemeral data), so nothing is stored here. Experiments call this hand
and record what they concluded, not the candles.

Tries exchanges in priority order; a coin unknown to all of them returns None
(embodiment principle: report the sense's limit, don't guess).
"""
import asyncio
from datetime import datetime, timedelta, timezone

import ccxt.async_support as ccxt

EXCHANGE_PRIORITY = ["binance", "bybit", "kucoin", "gate", "mexc", "okx"]

_exchanges: dict = {}


def normalize_symbol(coin: str) -> str:
    """'ROGE' -> 'ROGE/USDT'; 'SOL/USDT' stays as is."""
    coin = coin.upper().strip().lstrip("$#")
    if "/" in coin:
        return coin
    for suffix in ("USDT", "USDC", "USD"):
        if coin.endswith(suffix) and len(coin) > len(suffix):
            coin = coin[: -len(suffix)]
            break
    return f"{coin}/USDT"


async def _get_exchange(name: str):
    if name not in _exchanges:
        cls = getattr(ccxt, name, None)
        if cls is None:
            return None
        _exchanges[name] = cls({"enableRateLimit": True})
    return _exchanges[name]


async def close_all() -> None:
    for ex in _exchanges.values():
        try:
            await ex.close()
        except Exception:
            pass
    _exchanges.clear()


async def fetch_ohlcv(
    coin: str,
    timeframe: str = "1h",
    since: datetime | None = None,
    days: float = 14,
) -> dict | None:
    """Fetch candles for `coin` starting at `since` (default: now - days).

    Returns {"exchange", "symbol", "timeframe", "candles"} where each candle
    is [ms_timestamp, open, high, low, close, volume] — or None if no
    exchange we know lists the coin.
    """
    symbol = normalize_symbol(coin)
    if since is None:
        since = datetime.now(timezone.utc) - timedelta(days=days)
    since_ms = int(since.timestamp() * 1000)
    until_ms = int((since + timedelta(days=days)).timestamp() * 1000)

    for name in EXCHANGE_PRIORITY:
        ex = await _get_exchange(name)
        if ex is None:
            continue
        try:
            candles = []
            cursor = since_ms
            while cursor < until_ms:
                batch = await ex.fetch_ohlcv(symbol, timeframe, since=cursor, limit=1000)
                if not batch:
                    break
                candles.extend(c for c in batch if c[0] < until_ms)
                if batch[-1][0] <= cursor:  # no forward progress
                    break
                cursor = batch[-1][0] + 1
            if candles:
                return {"exchange": name, "symbol": symbol,
                        "timeframe": timeframe, "candles": candles}
        except Exception:
            continue  # not listed here / hiccup — try the next exchange
    return None


async def listed_on(coin: str) -> dict:
    """Which of our exchanges list this coin (checked live, in parallel)."""
    symbol = normalize_symbol(coin)

    async def probe(name):
        ex = await _get_exchange(name)
        try:
            t = await ex.fetch_ticker(symbol)
            return name, t.get("last")
        except Exception:
            return None

    hits = [r for r in await asyncio.gather(*(probe(n) for n in EXCHANGE_PRIORITY)) if r]
    return {"symbol": symbol,
            "listed_on": [{"exchange": n, "last_price": p} for n, p in hits],
            "not_listed_anywhere_we_read": not hits}


if __name__ == "__main__":
    async def _demo():
        data = await fetch_ohlcv("BTC", "1h", days=2)
        print(f"{data['symbol']} via {data['exchange']}: {len(data['candles'])} candles,"
              f" last close ${data['candles'][-1][4]:,.0f}")
        await close_all()

    asyncio.run(_demo())
