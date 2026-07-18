"""Body self-management from the chat (his rule: never edit yaml by hand).

capabilities(): what the creature senses, watches and can do — live counts.
add_source(): grow the watch config and capture the new source immediately.
targets.yaml becomes machine-managed (comments don't survive rewrites).
"""
import yaml

from .. import config, db
from ..brain import prompt

KINDS = {"telegram", "cmc", "reddit", "news", "coingecko", "feargreed",
         "dex_trending"}


def capabilities(conn) -> dict:
    targets = config.load_targets()
    senses = {}
    for t in ("sense_telegram", "sense_cmc", "sense_reddit", "sense_news",
              "sense_coingecko", "sense_feargreed", "sense_dex", "sense_chat"):
        n, latest = conn.execute(
            f"SELECT count(*), max(observed_at)::date FROM {t}").fetchone()
        senses[t] = {"rows": n, "latest": str(latest) if latest else None}
    edges = conn.execute("SELECT count(*) FROM taught_steps WHERE active").fetchone()[0]
    lessons = conn.execute("SELECT count(*) FROM guidance WHERE active").fetchone()[0]
    return {"watching": {k: v for k, v in targets.items() if v},
            "senses": senses,
            "tools": prompt.TOOLS + " · capabilities() this overview · "
                     "add_source(kind, ...) watch something new from chat",
            "memory": {"taught_steps": edges, "playbook_lessons": lessons,
                       "note": "finds vault + call_outcomes queryable via sql"}}


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
