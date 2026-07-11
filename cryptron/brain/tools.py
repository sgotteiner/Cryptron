"""The brain's tools: what Cryptron can actually DO during the dialogue.

Every tool returns a compact JSON-able dict. The embodiment principle rules:
these are ALL the hands there are — anything else must be honestly refused.
"""
import json
import re
from datetime import datetime, timedelta, timezone

from ..hands import price, tradingview
from ..hands.organs import ORGANS
from ..memory import embed
from ..senses import cmc


async def cmc_lookup(conn, symbols: list[str]) -> dict:
    return await cmc.lookup(conn, symbols)


async def exchanges(coin: str) -> dict:
    return await price.listed_on(coin)


def save_guidance(conn, lesson: str, why: str = "", provenance: str = "user") -> dict:
    conn.execute("INSERT INTO guidance (lesson, why, provenance) VALUES (%s, %s, %s)",
                 (lesson, why, provenance))
    return {"learned": lesson}


def load_guidance(conn) -> list:
    return conn.execute("""
        SELECT lesson, why FROM guidance WHERE active ORDER BY id LIMIT 40""").fetchall()

TICKER_RE = re.compile(r"\$([A-Z][A-Z0-9]{1,9})\b")
SKIP = {"USDT", "USD", "K", "M", "B", "BTC", "ETH", "SOL", "BNB"}


def sources(conn) -> dict:
    rows = conn.execute("""
        SELECT source_id, count(*), min(observed_at)::date, max(observed_at)::date
        FROM sense_telegram GROUP BY source_id""").fetchall()
    return {"telegram": [{"source_id": r[0], "messages": r[1],
                          "from": str(r[2]), "to": str(r[3])} for r in rows]}


def calls(conn, source_id: str, min_mentions: int = 3) -> dict:
    rows = conn.execute("""
        SELECT observed_at, payload->>'text' FROM sense_telegram
        WHERE source_id = %s ORDER BY observed_at""", (source_id,)).fetchall()
    first, count = {}, {}
    for at, text in rows:
        for t in set(TICKER_RE.findall(text or "")) - SKIP:
            first.setdefault(t, at)
            count[t] = count.get(t, 0) + 1
    out = [{"ticker": t, "first_seen": first[t].isoformat(), "mentions": count[t]}
           for t in sorted(first, key=lambda x: first[x]) if count[t] >= min_mentions]
    return {"source_id": source_id, "calls": out}


async def price_summary(coin: str, since_iso: str, days_before: float = 7,
                        days_after: float = 14) -> dict:
    since = datetime.fromisoformat(since_iso).replace(tzinfo=timezone.utc)
    start = since - timedelta(days=days_before)
    data = await price.fetch_ohlcv(coin, "1h", since=start,
                                   days=days_before + days_after)
    if not data:
        return {"coin": coin, "error": "not listed on any exchange I can read (CEX only)"}
    before = [c for c in data["candles"] if c[0] < since.timestamp() * 1000]
    after = [c for c in data["candles"] if c[0] >= since.timestamp() * 1000]
    if not after:
        return {"coin": coin, "error": "no candles after that moment"}
    entry = after[0][4]
    out = {"coin": data["symbol"], "exchange": data["exchange"], "entry": entry,
           "after": {"peak_pct": round((max(c[2] for c in after) / entry - 1) * 100, 1),
                     "low_pct": round((min(c[3] for c in after) / entry - 1) * 100, 1),
                     "close_pct": round((after[-1][4] / entry - 1) * 100, 1)}}
    if before:
        out["trend_before"] = {
            "days": days_before,
            "change_pct": round((entry / before[0][4] - 1) * 100, 1)}
    return out


async def score(conn, source_id: str, organ: str, config: dict) -> dict:
    if organ not in ORGANS:
        return {"error": f"unknown organ; available: {list(ORGANS)}"}
    per_call, results = [], []
    for c in calls(conn, source_id)["calls"]:
        at = datetime.fromisoformat(c["first_seen"])
        data = await price.fetch_ohlcv(c["ticker"], "1h", since=at,
                                       days=config.get("timeframe_days", 14) or 14)
        if not data:
            per_call.append({"ticker": c["ticker"], "skipped": "not on CEX"})
            continue
        r = ORGANS[organ](data["candles"], data["candles"][0][4], config)
        if r.win is not None:
            results.append(r)
        per_call.append({"ticker": c["ticker"], "win": r.win, "pnl_pct": r.pnl_pct})
    wins = sum(1 for r in results if r.win)
    return {"organ": organ, "config": config, "n": len(results),
            "winrate": round(wins / len(results), 2) if results else None,
            "avg_pnl_pct": round(sum(r.pnl_pct for r in results) / len(results), 1)
            if results else None, "per_call": per_call}


async def tv_search(query: str) -> dict:
    return await tradingview.search(query)


async def tv_ohlcv(symbol: str, timeframe: str = "60", bars: int = 200) -> dict:
    res = await tradingview.fetch_ohlcv(symbol, timeframe, bars)
    b = res.get("bars")
    if b and len(b) > 30:  # keep the prompt slim: summarize long series
        closes = [x[4] if isinstance(x, list) else x.get("close") for x in b]
        res = {"symbol": symbol, "timeframe": timeframe, "n_bars": len(b),
               "first_close": closes[0], "last_close": closes[-1],
               "max_close": max(closes), "min_close": min(closes)}
    return res


def sql(conn, query: str) -> dict:
    q = query.strip().rstrip(";")
    if not q.lower().startswith("select"):
        return {"error": "read-only: SELECT queries only"}
    rows = conn.execute(q + (" LIMIT 50" if "limit" not in q.lower() else "")).fetchall()
    return {"rows": [[str(v) for v in r] for r in rows], "count": len(rows)}


async def record_experiment(conn, hypothesis: str, config: dict, result: dict,
                            reading: str, thread_id: str | None = None,
                            testing_organ: dict | None = None, sample: str = "in",
                            market_adjusted: bool = False) -> dict:
    n = conn.execute("SELECT count(*) FROM experiments").fetchone()[0]
    exp_id = f"exp-{n + 1:04d}"
    try:  # recall spans experiments — but an embed hiccup must not lose the record
        vec = json.dumps(await embed.embed(
            f"{hypothesis}\n{reading}\n{json.dumps(result, default=str)}"))
    except Exception:
        vec = None  # reindex backfills later
    conn.execute("""
        INSERT INTO experiments (id, thread_id, hypothesis, config, testing_organ,
                                 sample, market_adjusted, result, reading, embedding)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector)""",
        (exp_id, thread_id, hypothesis, json.dumps(config),
         json.dumps(testing_organ) if testing_organ else None,
         sample, market_adjusted, json.dumps(result), reading, vec))
    return {"recorded": exp_id, "sample": sample, "market_adjusted": market_adjusted}
