"""The outcomes knowledge base: label who won, who lost, and how — durably.

score() answers once and forgets; label_calls() writes each call's outcome
into call_outcomes so comparison experiments can JOIN outcomes against the
background senses captured (sentiment, attention, liquidity, regime).
Re-running refreshes rows (windows close, prices move on).
"""
import asyncio
import json
from datetime import datetime

from ..hands import dex_price, price
from ..hands.organs import ORGANS
from . import tools


async def label_calls(conn, source_id: str, organ: str, config: dict) -> dict:
    """Judge every call of a group under one way of trading; persist each row."""
    if organ not in ORGANS:
        return {"error": f"unknown organ; available: {list(ORGANS)}"}
    days = config.get("timeframe_days") or config.get("hold_days") or 14
    labeled, wins, unpriceable, final = 0, 0, 0, 0
    for call in tools.calls(conn, source_id)["calls"]:
        called_at = datetime.fromisoformat(call["first_seen"])
        done = conn.execute("""
            SELECT win FROM call_outcomes
            WHERE coin = %s AND source_id = %s AND called_at = %s
              AND organ = %s AND config = %s AND win IS NOT NULL
              AND called_at + %s * interval '1 day' < now()""",
            (call["ticker"], source_id, called_at, organ, json.dumps(config),
             days)).fetchone()
        if done:  # closed window, already priced: the outcome is FINAL
            final += 1
            wins += 1 if done[0] else 0
            continue
        data = await price.fetch_ohlcv(call["ticker"], "1h", since=called_at,
                                       days=days)
        if not (data and data["candles"]):  # gems live on DEXes, not CEXes
            data = await dex_price.coin_ohlcv(conn, call["ticker"], called_at, days)
            await asyncio.sleep(8)  # pace the sweep: GT free tier is ~30 calls/min
        row = {"entry": None, "peak_pct": None, "low_pct": None,
               "close_pct": None, "win": None, "pnl_pct": None,
               "note": "not priceable (no CEX listing, no DEX pool)"}
        if data and data["candles"]:
            candles = data["candles"]
            entry = candles[0][4]
            r = ORGANS[organ](candles, entry, config)
            row = {"entry": entry,
                   "peak_pct": round((max(c[2] for c in candles) / entry - 1) * 100, 1),
                   "low_pct": round((min(c[3] for c in candles) / entry - 1) * 100, 1),
                   "close_pct": round((candles[-1][4] / entry - 1) * 100, 1),
                   "win": r.win, "pnl_pct": r.pnl_pct,
                   "note": data["exchange"] if data["exchange"].startswith("dex:")
                           else None}
        conn.execute("""
            INSERT INTO call_outcomes (coin, source_id, called_at, organ, config,
                entry, peak_pct, low_pct, close_pct, win, pnl_pct, note)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (coin, source_id, called_at, organ, config)
            DO UPDATE SET entry = EXCLUDED.entry, peak_pct = EXCLUDED.peak_pct,
              low_pct = EXCLUDED.low_pct, close_pct = EXCLUDED.close_pct,
              win = EXCLUDED.win, pnl_pct = EXCLUDED.pnl_pct,
              note = EXCLUDED.note, computed_at = now()""",
            (call["ticker"], source_id, called_at, organ, json.dumps(config),
             row["entry"], row["peak_pct"], row["low_pct"], row["close_pct"],
             row["win"], row["pnl_pct"], row["note"]))
        labeled += 1
        wins += 1 if row["win"] else 0
        unpriceable += 1 if row["note"] and "not priceable" in row["note"] else 0
    return {"source_id": source_id, "organ": organ, "config": config,
            "labeled": labeled, "already_final": final, "wins": wins,
            "unpriceable": unpriceable,
            "note": "rows persisted in call_outcomes — JOIN against senses to "
                    "compare. Unpriceable rows retry on the next run (DEX candle "
                    "API is tightly rate-limited; sweeps converge across runs)."}
