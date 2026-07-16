"""Run every configured sense once:  python -m cryptron

Each sense whose key appears in targets.yaml gets captured; the rest are
skipped. One sense failing must not stop the others from sensing.
"""
import asyncio

from . import config, db
from .senses import (cmc, coingecko, dex_trending, feargreed, news, reddit,
                     telegram, twitter)

SENSES = {
    telegram.SENSE: telegram,
    cmc.SENSE: cmc,
    twitter.SENSE: twitter,
    reddit.SENSE: reddit,
    news.SENSE: news,
    feargreed.SENSE: feargreed,
    dex_trending.SENSE: dex_trending,
    coingecko.SENSE: coingecko,
}


async def main() -> None:
    targets = config.load_targets()
    conn = db.get_conn()
    db.init_schema(conn)

    for name, module in SENSES.items():
        if not targets.get(name):
            continue
        print(f"— {name} —")
        try:
            await module.capture_all(conn, targets[name])
        except Exception as e:
            print(f"{name}: sense failed ({e})")

    conn.close()


if __name__ == "__main__":
    asyncio.run(main())
