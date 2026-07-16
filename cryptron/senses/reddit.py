"""The Reddit sense: capture new posts from watched subreddits into sense_reddit.

Stream sense — posts have native ids. Reddit blocks unauthenticated JSON
(403) but serves public RSS freely, so we ride the Atom feed via the news
sense's parser. Trade-off, accepted: no score/num_comments without OAuth —
what attention needs (post velocity + text per ticker) survives.

Run:  python -m cryptron.senses.reddit
"""
import asyncio
from datetime import datetime, timezone

import httpx

from .. import config, db
from .news import parse_feed

SENSE = "reddit"
TABLE = "sense_reddit"
UA = {"User-Agent": "windows:cryptron:1.0 (crypto research agent)"}


def to_row(source_id: str, item: dict) -> dict:
    p = item["payload"]
    return {
        "coin": None,  # enricher work, not the collector's
        "observed_at": item["observed_at"],
        "source_id": source_id,
        "payload": {
            "post_id": p["item_id"],           # e.g. 't3_abc123'
            "title": p["title"],
            "selftext": p["summary"][:2000],   # RSS content, tags stripped
            "url": p["link"],
        },
    }


async def capture_target(client: httpx.AsyncClient, conn, target: dict) -> int:
    source_id = target["source_id"]
    sub = target["subreddit"]

    resp = await client.get(f"https://www.reddit.com/r/{sub}/new.rss",
                            params={"limit": 100})
    if resp.status_code == 429:  # rate-limited: wait once, retry once
        await asyncio.sleep(float(resp.headers.get("retry-after", 15)))
        resp = await client.get(f"https://www.reddit.com/r/{sub}/new.rss",
                                params={"limit": 100})
    resp.raise_for_status()
    items = parse_feed(source_id, resp.text)

    rows = [to_row(source_id, i) for i in items]
    inserted = db.insert_sense_rows(conn, TABLE, rows)
    db.set_cursor(conn, SENSE, source_id, datetime.now(timezone.utc).isoformat())
    return inserted


async def capture_all(conn, targets: list[dict]) -> None:
    async with httpx.AsyncClient(headers=UA, timeout=30,
                                 follow_redirects=True) as client:
        for target in targets:
            try:
                n = await capture_target(client, conn, target)
                print(f"{target['source_id']}: {n} new posts captured")
            except Exception as e:  # one blocked sub must not stop the rest
                print(f"{target['source_id']}: capture failed ({e})")
            await asyncio.sleep(10)  # stay gentle; reddit rate-limits by IP


async def main() -> None:
    targets = config.load_targets().get(SENSE, [])
    if not targets:
        raise SystemExit("No reddit targets in targets.yaml")
    conn = db.get_conn()
    db.init_schema(conn)
    await capture_all(conn, targets)
    conn.close()


if __name__ == "__main__":
    asyncio.run(main())
