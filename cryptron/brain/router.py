"""The cheap path: data question -> one retrieval -> numbers out.

His design: "get the top gain in a simple query -> pull the numbers it has in
the db or a short list of live lookups -> that's it." Most messages don't need
the full investigator context (~8K tokens/step); a tiny router picks ONE
retrieval, a tiny composer words the result. Judgment questions escalate to
the full brain unchanged.
"""
import json

from ..log import log
from . import llm

ROUTE = """You route one incoming message for a crypto research bot. Pick the \
CHEAPEST correct handling and output ONE JSON object, nothing else.

STORED DATA (Postgres; answer with one SELECT):
- call_outcomes(coin, source_id, called_at, organ, config, entry, peak_pct, \
low_pct, close_pct, win, pnl_pct, note) — labeled outcomes of telegram-group \
calls; source_id 'sangitagem' (CEX-listed) or 'crypto_gemsignals' (DEX gems).
- sense_coingecko(coin, observed_at, payload->>'sentiment_up_pct', \
'watchlist_users', 'telegram_users', 'reddit_subscribers', 'market_cap_rank')
- sense_cmc(coin, observed_at, payload) — market snapshots
- sense_dex(coin, observed_at, payload->>'name','price_usd','liquidity_usd',\
'fdv_usd','volume_24h_usd','created_at') — DEX pool snapshots; source_id \
'trending-*' = trending polls
- sense_feargreed(observed_at, payload->>'value') — market regime 0-100 daily
- sense_telegram(source_id, observed_at, payload->>'text') — raw group messages

LIVE lookups (one tool call): cmc_lookup{"symbols":[...]} price/cap/volume/rank \
now · sentiment{"coin"} votes/watchlist/community sizes · exchanges{"coin"} CEX \
listings · dex_search{"query"} pools/liquidity/age · mentions{"ticker","days"} \
attention across channels · fear_greed{} regime now vs averages · capabilities{} \
what the bot watches/senses/can do (use for "what tools/sources do you have") · \
graph{"topic": "..."} the closest taught situations + next steps for a topic, or \
all taught edges with no topic (use for "what do you know / what would you do \
for X / show your teachings") · trace{"n": 25} what just happened internally — \
steps, sims, tool calls, failures (use for "what went wrong / show the trace") · \
add_source{"kind": telegram|cmc|reddit|news|coingecko, ...} start watching \
something new (telegram: source_id+link+backfill; cmc/coingecko: symbols:[...]; \
reddit: source_id+subreddit; news: source_id+url) — use when he says "add/watch \
this group/coin/subreddit".

SQL notes: numeric outcome columns can be NULL (unpriceable coins) — always \
add NULLS LAST to ORDER BY ... DESC, or filter IS NOT NULL.

Output exactly one of:
{"sql": "SELECT ..."}            <- stored numbers answer it
{"tool": "<name>", "args": {..}} <- one live number answers it
{"escalate": "<short reason>"}   <- needs judgment: evaluations, verdicts, \
comparisons/analysis, multi-step investigation, teaching/corrections, anything \
not answerable by one retrieval."""

COMPOSE = """You word a data answer for a crypto research bot (Telegram, keep \
it short). Using ONLY numbers present in the RESULT, answer the QUESTION in \
plain language. If the result is empty or lacks it, say exactly that. Never \
add numbers of your own. Output plain text, no JSON."""

FAST_TOOLS = {"cmc_lookup", "sentiment", "exchanges", "dex_search",
              "mentions", "fear_greed", "capabilities", "add_source",
              "graph", "trace"}
VERBATIM = {"graph", "trace"}  # exact internals — no LLM rewording


async def route(user_text: str, recent: str) -> dict | None:
    try:
        raw = (await llm.complete(
            ROUTE, [{"role": "user",
                     "content": f"RECENT CONTEXT:\n{recent}\n\nMESSAGE:\n{user_text}"}]
        )).strip()
        return json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
    except Exception as e:
        log("route-err", f"{type(e).__name__}: {e}")
        return None


async def compose(user_text: str, result: dict) -> str:
    return (await llm.complete(
        COMPOSE, [{"role": "user",
                   "content": f"QUESTION:\n{user_text}\n\n"
                              f"RESULT:\n{json.dumps(result, default=str)[:3000]}"}]
    )).strip()
