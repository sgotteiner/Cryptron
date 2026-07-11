"""Rebuild the layer-2 index from the vault:  python -m cryptron.memory

The finds/ markdown files are the source of truth; this re-derives the
DB index (scope + embeddings) from them and backfills experiment embeddings.
"""
import asyncio

from .. import db
from . import recall


async def main() -> None:
    conn = db.get_conn()
    db.init_schema(conn)
    print(await recall.reindex(conn))
    conn.close()


if __name__ == "__main__":
    asyncio.run(main())
