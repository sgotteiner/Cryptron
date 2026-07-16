"""The DEX-trending sense: snapshot GeckoTerminal's trending pools per run.

Snapshot sense — trending is ephemeral by definition: which pools the DEX
crowd is piling into RIGHT NOW is gone the moment it changes (§6.4). Free,
no key. This is the gem radar: attention on-chain, before CEXes see it.

Run:  python -m cryptron.senses.dex_trending
"""
import asyncio

from .. import config, db
from ..hands import dex

SENSE = "dex_trending"


async def capture_all(conn, targets: list[dict]) -> None:
    for target in targets:
        res = await dex.trending(conn, network=target.get("network"),
                                 top=int(target.get("top", 20)))
        if "error" in res:
            print(f"{target['source_id']}: failed ({res['error']})")
        else:
            print(f"{target['source_id']}: {len(res['pools'])} trending pools captured")
        await asyncio.sleep(2)  # GeckoTerminal free tier: 30 calls/min


async def main() -> None:
    targets = config.load_targets().get(SENSE, [])
    if not targets:
        raise SystemExit("No dex_trending targets in targets.yaml")
    conn = db.get_conn()
    db.init_schema(conn)
    await capture_all(conn, targets)
    conn.close()


if __name__ == "__main__":
    asyncio.run(main())
