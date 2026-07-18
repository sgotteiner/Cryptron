"""Shared ticker extraction: which coins have the groups actually called?

Lives outside brain/ and senses/ so both can use it: the brain's calls()
tool and any sense that captures per-cohort (comparisons need the SAME
metrics across the whole called cohort, not just coins someone asked about).
"""
import re

TICKER_RE = re.compile(r"\$([A-Z][A-Z0-9]{1,9})\b")
BARE_RE = re.compile(r"\b([A-Z][A-Z0-9]{2,9})\b")
SKIP = {"USDT", "USD", "K", "M", "B", "BTC", "ETH", "SOL", "BNB"}
_WORDS = {"THE", "AND", "FOR", "NOT", "GOOD", "BAD", "CEX", "DEX", "TASK",
          "API", "OK", "SQL", "TP", "SL", "PNL", "FDV"} | SKIP


def find_tickers(text: str) -> list[str]:
    """$-prefixed tickers first; else bare ALL-CAPS words that look like one."""
    dollar = [t for t in TICKER_RE.findall(text) if t not in SKIP]
    if dollar:
        return dollar
    return [t for t in BARE_RE.findall(text) if t not in _WORDS]


def called_symbols(conn, source_ids: list[str], min_mentions: int = 3) -> list[str]:
    """Every ticker a group called (>= min_mentions), across the given groups."""
    return sorted(_mentions(conn, source_ids, min_mentions))


def recent_called(conn, source_ids: list[str], n: int = 10,
                  min_mentions: int = 1) -> list[str]:
    """The n most recently first-called tickers, newest first."""
    first = _mentions(conn, source_ids, min_mentions)
    return sorted(first, key=lambda t: first[t], reverse=True)[:n]


def _mentions(conn, source_ids: list[str], min_mentions: int) -> dict:
    """ticker -> first-seen time, for tickers with >= min_mentions."""
    rows = conn.execute("""
        SELECT observed_at, payload->>'text' FROM sense_telegram
        WHERE source_id = ANY(%s) ORDER BY observed_at""", (source_ids,)).fetchall()
    first, count = {}, {}
    for at, text in rows:
        for t in set(TICKER_RE.findall(text or "")) - SKIP:
            first.setdefault(t, at)
            count[t] = count.get(t, 0) + 1
    return {t: first[t] for t, c in count.items() if c >= min_mentions}
