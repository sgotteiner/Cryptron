"""Body self-management from the chat (his rule: never edit yaml by hand).

capabilities(): what the creature senses, watches and can do — live counts.
add_source(): grow the watch config and capture the new source immediately.
targets.yaml becomes machine-managed (comments don't survive rewrites).
"""
import yaml

from .. import config, db

KINDS = {"telegram", "cmc", "reddit", "news", "coingecko", "feargreed",
         "dex_trending"}


TOOL_DOCS = [
    ("sources()", "message counts + date spans per telegram group"),
    ("calls(source_id)", "every $TICKER call of a group with first-seen time"),
    ("cmc_lookup([symbols])", "LIVE price, market cap, 24h volume, rank — any coin"),
    ("sentiment(coin)", "crowd votes %, watchlist count, telegram/reddit community size"),
    ("mentions(ticker)", "how much it's talked about per channel, this week vs last"),
    ("exchanges(coin)", "which of 6 big CEXes list it right now"),
    ("dex_search(name/ticker/address)", "its DEX pools: price, liquidity, FDV, pool age"),
    ("dex_price_summary(coin, since)", "what price did after a moment (DEX gems)"),
    ("price_summary(coin, since)", "same for CEX-listed coins, incl. trend before"),
    ("dex_trending(network)", "pools the DEX crowd piles into right now (gem radar)"),
    ("fear_greed()", "market regime 0-100 today vs 7d/30d averages"),
    ("score(group, organ, config)", "winrate/pnl of ALL a group's calls under one exit"),
    ("label_calls(...)", "same, but saved forever into call_outcomes"),
    ("sql(SELECT...)", "any stored data: outcomes, snapshots, messages"),
    ("recall(text)", "similar past finds + experiments (vector search)"),
    ("graph(topic)", "closest taught situations + next steps (my playbook of paths)"),
    ("playbook()", "every saved lesson verbatim"),
    ("trace()", "what I just did internally: steps, sims, tools, failures"),
    ("capabilities()", "this overview"),
    ("add_source(kind, ...)", "start watching a new group/coin/subreddit/feed"),
]


def capabilities(conn) -> dict:
    targets = config.load_targets()
    lines = ["WATCHING:"]
    for kind, items in targets.items():
        if not items:
            continue
        names = ", ".join(t.get("source_id", "") +
                          ("(" + ",".join(t.get("symbols", [])) + ")"
                           if t.get("symbols") else "") for t in items)
        lines.append(f"  {kind}: {names}")
    lines.append("SENSES (stored rows | freshest):")
    for t in ("sense_telegram", "sense_cmc", "sense_reddit", "sense_news",
              "sense_coingecko", "sense_feargreed", "sense_dex"):
        n, latest = conn.execute(
            f"SELECT count(*), max(observed_at)::date FROM {t}").fetchone()
        lines.append(f"  {t}: {n} | {latest}")
    edges = conn.execute("SELECT count(*) FROM taught_steps WHERE active").fetchone()[0]
    lessons = conn.execute("SELECT count(*) FROM guidance WHERE active").fetchone()[0]
    lines.append(f"MEMORY: {edges} taught steps · {lessons} lessons · finds vault "
                 "+ call_outcomes via sql")
    lines.append("TOOLS (what data each gets):")
    for sig, desc in TOOL_DOCS:
        lines.append(f"  {sig} — {desc}")
    return {"text": "\n".join(lines)}


async def add_source(conn, kind: str, **params) -> dict:
    """Add a watch target and capture it NOW. Examples:
    add_source('telegram', source_id='mygroup', link='https://t.me/x', backfill=200)
    add_source('cmc', symbols=['PEPE'])  — appended to the watchlist
    add_source('reddit', source_id='sats', subreddit='SatoshiStreetBets')"""
    if kind not in KINDS:
        return {"error": f"unknown kind; available: {sorted(KINDS)}"}
    targets = config.load_targets()
    section = targets.setdefault(kind, [])
    if kind in ("cmc", "coingecko") and "symbols" in params and section:
        new = [s.upper() for s in params["symbols"]
               if s.upper() not in section[0].get("symbols", [])]
        if not new:
            return {"already_watching": params["symbols"]}
        section[0]["symbols"].extend(new)
        target = section[0]
    else:
        if not params.get("source_id"):
            return {"error": "source_id is required"}
        if any(t.get("source_id") == params["source_id"] for t in section):
            return {"already_watching": params["source_id"]}
        target = params
        section.append(target)
    with open(config.ROOT / "targets.yaml", "w", encoding="utf-8") as f:
        yaml.safe_dump(targets, f, allow_unicode=True, sort_keys=False)

    from ..senses import (cmc, coingecko, dex_trending, feargreed, news,
                          reddit, telegram)
    mod = {"telegram": telegram, "cmc": cmc, "reddit": reddit, "news": news,
           "coingecko": coingecko, "feargreed": feargreed,
           "dex_trending": dex_trending}[kind]
    try:
        await mod.capture_all(conn, [target])
        captured = "captured"
    except Exception as e:
        captured = f"added to config, but first capture failed: {e}"
    return {"added": kind, "target": target, "capture": captured}
