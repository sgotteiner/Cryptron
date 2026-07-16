"""The news sense: capture crypto news headlines from RSS feeds into sense_news.

Stream sense — items have native guids/links. Free forever: RSS needs no key,
no scraping service. A tiny stdlib parser covers both RSS 2.0 and Atom;
feeds that break it are skipped loudly, never silently.

Run:  python -m cryptron.senses.news
"""
import asyncio
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import httpx

from .. import config, db

SENSE = "news"
TABLE = "sense_news"
UA = {"User-Agent": "cryptron/1.0 (crypto research agent)"}
TAG_RE = re.compile(r"<[^>]+>")
ATOM = "{http://www.w3.org/2005/Atom}"


def _text(el, *names) -> str:
    for name in names:
        found = el.find(name)
        if found is not None and (found.text or "").strip():
            return found.text.strip()
    return ""


def _when(raw: str) -> datetime:
    for parse in (parsedate_to_datetime, datetime.fromisoformat):
        try:
            dt = parse(raw)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
    return datetime.now(timezone.utc)


def parse_feed(source_id: str, xml: str) -> list[dict]:
    root = ET.fromstring(xml)
    items = root.iter("item")  # RSS 2.0
    if root.tag == f"{ATOM}feed":  # Atom
        items = root.iter(f"{ATOM}entry")
    rows = []
    for item in items:
        title = _text(item, "title", f"{ATOM}title")
        link = _text(item, "link") or next(
            (l.get("href") for l in item.iter(f"{ATOM}link") if l.get("href")), "")
        summary = TAG_RE.sub("", _text(item, "description", f"{ATOM}summary"))[:1000]
        published = _text(item, "pubDate", f"{ATOM}published", f"{ATOM}updated")
        item_id = _text(item, "guid", f"{ATOM}id") or link
        if not (title and item_id):
            continue
        rows.append({
            "coin": None,
            "observed_at": _when(published),
            "source_id": source_id,
            "payload": {"item_id": item_id, "title": title,
                        "summary": summary.strip(), "link": link},
        })
    return rows


async def capture_target(client: httpx.AsyncClient, conn, target: dict) -> int:
    resp = await client.get(target["url"])
    resp.raise_for_status()
    rows = parse_feed(target["source_id"], resp.text)
    inserted = db.insert_sense_rows(conn, TABLE, rows)
    db.set_cursor(conn, SENSE, target["source_id"],
                  datetime.now(timezone.utc).isoformat())
    return inserted


async def capture_all(conn, targets: list[dict]) -> None:
    async with httpx.AsyncClient(headers=UA, timeout=30,
                                 follow_redirects=True) as client:
        for target in targets:
            try:
                n = await capture_target(client, conn, target)
                print(f"{target['source_id']}: {n} new items captured")
            except Exception as e:  # one broken feed must not stop the rest
                print(f"{target['source_id']}: feed failed ({e})")


async def main() -> None:
    targets = config.load_targets().get(SENSE, [])
    if not targets:
        raise SystemExit("No news targets in targets.yaml")
    conn = db.get_conn()
    db.init_schema(conn)
    await capture_all(conn, targets)
    conn.close()


if __name__ == "__main__":
    asyncio.run(main())
