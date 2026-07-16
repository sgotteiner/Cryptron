"""Brain tools over the sentiment senses: attention across channels, regime.

mentions() is the multi-channel attention measure find-0042's directive asks
for (channels >= 2, vs baseline): one call counts a ticker across telegram,
reddit, news and cryptopanic, split into a recent window vs the period before.
"""
import re
from datetime import datetime, timezone

# source table -> the payload text fields a ticker can appear in
CHANNELS = {
    "sense_telegram": ["text"],
    "sense_reddit": ["title", "selftext"],
    "sense_news": ["title", "summary"],
    "sense_cryptopanic": ["title"],
}


def mentions(conn, ticker: str, days: float = 7) -> dict:
    """Mentions per channel: last `days` vs the same-length window before it."""
    ticker = re.sub(r"[^A-Za-z0-9]", "", ticker).upper()
    if not ticker:
        return {"error": "empty ticker"}
    pattern = rf"\m\$?{ticker}\M"

    out, channels_active = {}, 0
    for table, fields in CHANNELS.items():
        text = " || ' ' || ".join(f"coalesce(payload->>'{f}', '')" for f in fields)
        row = conn.execute(f"""
            SELECT count(*) FILTER (WHERE observed_at >= now() - %s * interval '1 day'),
                   count(*) FILTER (WHERE observed_at <  now() - %s * interval '1 day'
                                    AND observed_at >= now() - %s * interval '1 day'),
                   max(observed_at)
            FROM {table} WHERE ({text}) ~* %s""",
            (days, days, days * 2, pattern)).fetchone()
        recent, baseline, last = row
        if recent or baseline:
            channels_active += 1
        out[table.removeprefix("sense_")] = {
            "recent": recent, "baseline_prior_window": baseline,
            "last_seen": last.isoformat() if last else None}

    titles = conn.execute("""
        SELECT observed_at::date, source_id, payload->>'title' FROM sense_news
        WHERE coalesce(payload->>'title','') ~* %s
        ORDER BY observed_at DESC LIMIT 3""", (pattern,)).fetchall()
    return {"ticker": ticker, "window_days": days, "channels": out,
            "channels_with_mentions": channels_active,
            "recent_headlines": [f"{d} [{s}] {t}" for d, s, t in titles]}


def fear_greed(conn) -> dict:
    """Market regime: today's Fear & Greed index vs its recent averages."""
    latest = conn.execute("""
        SELECT observed_at::date, payload->>'value', payload->>'classification'
        FROM sense_feargreed ORDER BY observed_at DESC LIMIT 1""").fetchone()
    if not latest:
        return {"error": "sense_feargreed is empty — run: python -m cryptron.senses.feargreed"}
    avgs = conn.execute("""
        SELECT round(avg((payload->>'value')::int) FILTER
                 (WHERE observed_at >= now() - interval '7 days'), 1),
               round(avg((payload->>'value')::int) FILTER
                 (WHERE observed_at >= now() - interval '30 days'), 1)
        FROM sense_feargreed""").fetchone()
    return {"date": str(latest[0]), "value": int(latest[1]),
            "classification": latest[2],
            "avg_7d": float(avgs[0]) if avgs[0] is not None else None,
            "avg_30d": float(avgs[1]) if avgs[1] is not None else None,
            "note": "0=extreme fear, 100=extreme greed; daily, market-wide"}
