"""Canonical situation rendering (his design): the embedded situation must
differ only where differences MEAN something.

Names -> placeholders ("the coin"), raw values -> log form + class word
("cap 10^6.9 (small)"), so PEPE and BONK land on the same vector while a
small-cap and a large-cap land apart. Raw features also returned structurally
(stored beside the embedding) so thresholds can later use numeric distance.
"""
import math

from ..tickers import TICKER_RE, find_tickers

CAP_CLASSES = [(1e7, "micro"), (1e8, "small"), (1e9, "mid"), (float("inf"), "large")]
VOL_CLASSES = [(1e5, "thin"), (1e6, "modest"), (1e7, "active"), (float("inf"), "liquid")]


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def logfmt(v, classes) -> tuple[str, float | None]:
    v = _num(v)
    if not v or v <= 0:
        return "unknown", None
    word = next(w for cap, w in classes if v < cap)
    lg = round(math.log10(v), 1)
    return f"10^{lg} ({word})", lg


def canon_task(task: str) -> str:
    """The task with coin names abstracted away — meaning, not identity."""
    out = TICKER_RE.sub("the coin", task)
    for t in find_tickers(out):
        out = out.replace(t, "the coin")
    return out


def summarize(tool: str, result: dict) -> tuple[str, dict]:
    """One canonical line + raw features for a tool result."""
    f = {}
    if tool == "cmc_lookup" and isinstance(result, dict):
        coin = next(iter(result.values()), {})
        if isinstance(coin, dict) and "market_cap" in coin:
            cap, f["log_cap"] = logfmt(coin.get("market_cap"), CAP_CLASSES)
            vol, f["log_vol"] = logfmt(coin.get("volume_24h"), VOL_CLASSES)
            return f"market cap {cap}, 24h volume {vol}, rank {coin.get('rank')}", f
    if tool == "sentiment" and "sentiment_up_pct" in result:
        f["bullish_pct"] = _num(result.get("sentiment_up_pct"))
        wl, f["log_watchlist"] = logfmt(result.get("watchlist_users"), VOL_CLASSES)
        return (f"crowd sentiment {result.get('sentiment_up_pct')}% bullish, "
                f"watchlist {wl}, cap rank {result.get('market_cap_rank')}"), f
    if tool == "dex_search" and result.get("pools"):
        p = max(result["pools"], key=lambda x: _num(x.get("liquidity_usd")) or 0)
        liq, f["log_liquidity"] = logfmt(p.get("liquidity_usd"), VOL_CLASSES)
        return (f"DEX pool exists: liquidity {liq}, fdv "
                f"{logfmt(p.get('fdv_usd'), CAP_CLASSES)[0]}, "
                f"created {p.get('created_at', 'unknown')[:10]}"), f
    if tool == "exchanges":
        n = len(result.get("listed_on", []))
        f["cex_listings"] = n
        return (f"listed on {n} CEXes" if n else "not CEX-listed (DEX-only)"), f
    if tool == "mentions":
        ch = result.get("channels_with_mentions", 0)
        f["attention_channels"] = ch
        return f"attention in {ch} channels (recent vs prior window measured)", f
    if tool in ("score", "label_calls") and "winrate" in str(result):
        f["winrate"] = _num(result.get("winrate"))
        f["n"] = _num(result.get("n") or result.get("labeled"))
        return (f"scored under {result.get('organ')}: winrate "
                f"{result.get('winrate')}, n={f['n']}, avg pnl "
                f"{result.get('avg_pnl_pct')}%"), f
    if tool == "fear_greed" and "value" in result:
        f["regime"] = _num(result.get("value"))
        return f"market regime {result.get('classification')} ({result.get('value')})", f
    if tool == "sql":
        return f"query returned {result.get('count', 0)} rows", f
    text = str(result)[:200]
    return f"{tool}: {text}", f


def render(task: str, state: list) -> str:
    """The canonical situation: abstracted task + what has been learned."""
    lines = [f"TASK: {canon_task(task)}"]
    if not state:
        lines.append("Nothing checked yet.")
    for i, step in enumerate(state, 1):
        lines.append(f"{i}. {step['tool']} -> {step['text']}")
    return "\n".join(lines)
