"""The Twitter/X sense: capture tweets matching watched queries into sense_twitter.

The attention sense. Stream sense — tweets have native ids; capture is
idempotent, so each run just fetches the latest batch and duplicates are
skipped. Size `backfill` so runs overlap rather than gap.

Uses twikit (unofficial, logs in with your X account) — the only workable
free read path. Flakier than official APIs; treat failures as expected.
Needs TWITTER_USERNAME / TWITTER_EMAIL / TWITTER_PASSWORD in .env.
Run:  python -m cryptron.senses.twitter

STATUS (2026-07): blocked. X now fingerprints the connection itself (not
just login) — twikit and twscrape both fail before/at login even with a
valid logged-in session's cookies (ct0 + auth_token), because plain HTTP
clients don't pass the browser-fingerprint check. Confirmed not a
credentials issue. Fix needs a real browser: Firecrawl (already an MCP
hand here) or Playwright. Deferred — Telegram + CMC are enough for the
first experiment; this is the attention sense, wanted later.
"""
import asyncio
from email.utils import parsedate_to_datetime

from twikit import Client

from .. import config, db

SENSE = "twitter"
TABLE = "sense_twitter"
COOKIES = config.ROOT / "twitter.cookies"
PAGE_SIZE = 20


def _observed_at(tweet):
    dt = getattr(tweet, "created_at_datetime", None)
    return dt if dt is not None else parsedate_to_datetime(tweet.created_at)


def _row(source_id: str, coin: str | None, t) -> dict:
    return {
        "coin": coin,
        "observed_at": _observed_at(t),
        "source_id": source_id,
        "payload": {
            "tweet_id": int(t.id),
            "text": t.text,
            "user": t.user.screen_name if t.user else None,
            "user_followers": t.user.followers_count if t.user else None,
            "replies": t.reply_count,
            "retweets": t.retweet_count,
            "likes": t.favorite_count,
            "views": getattr(t, "view_count", None),
        },
    }


async def capture_target(client: Client, conn, target: dict) -> int:
    source_id = target["source_id"]
    coin = target.get("coin")
    want = int(target.get("backfill", 50))

    rows, page = [], await client.search_tweet(target["query"], "Latest", count=PAGE_SIZE)
    while page:
        rows.extend(_row(source_id, coin, t) for t in page)
        if len(rows) >= want:
            break
        page = await page.next()

    inserted = db.insert_sense_rows(conn, TABLE, rows[:want])
    if rows:
        db.set_cursor(conn, SENSE, source_id, str(max(r["payload"]["tweet_id"] for r in rows)))
    return inserted


async def capture_all(conn, targets: list[dict]) -> None:
    client = Client("en-US")
    if COOKIES.exists():
        client.load_cookies(str(COOKIES))
    else:
        await client.login(
            auth_info_1=config.require("TWITTER_USERNAME"),
            auth_info_2=config.require("TWITTER_EMAIL"),
            password=config.require("TWITTER_PASSWORD"),
        )
        client.save_cookies(str(COOKIES))

    for target in targets:
        try:
            n = await capture_target(client, conn, target)
            print(f"{target['source_id']}: {n} new tweets captured")
        except Exception as e:  # unofficial API — one bad query must not kill the run
            print(f"{target['source_id']}: FAILED ({e})")


async def main() -> None:
    targets = config.load_targets().get(SENSE, [])
    if not targets:
        raise SystemExit("No twitter targets in targets.yaml")
    conn = db.get_conn()
    db.init_schema(conn)
    await capture_all(conn, targets)
    conn.close()


if __name__ == "__main__":
    asyncio.run(main())
