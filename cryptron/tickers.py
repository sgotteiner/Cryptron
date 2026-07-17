"""Shared ticker extraction: which coins have the groups actually called?

Lives outside brain/ and senses/ so both can use it: the brain's calls()
tool and any sense that captures per-cohort (comparisons need the SAME
metrics across the whole called cohort, not just coins someone asked about).
"""
import re

TICKER_RE = re.compile(r"\$([A-Z][A-Z0-9]{1,9})\b")
SKIP = {"USDT", "USD", "K", "M", "B", "BTC", "ETH", "SOL", "BNB"}


def called_symbols(conn, source_ids: list[str], min_mentions: int = 3) -> list[str]:
    """Every ticker a group called (>= min_mentions), across the given groups."""
    rows = conn.execute("""
        SELECT payload->>'text' FROM sense_telegram
        WHERE source_id = ANY(%s)""", (source_ids,)).fetchall()
    count: dict[str, int] = {}
    for (text,) in rows:
        for t in set(TICKER_RE.findall(text or "")) - SKIP:
            count[t] = count.get(t, 0) + 1
    return sorted(t for t, n in count.items() if n >= min_mentions)
