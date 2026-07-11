"""Layer 1 access: connection, schema init, cursors, sense inserts."""
import json
from pathlib import Path

import psycopg

from . import config

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def get_conn() -> psycopg.Connection:
    # prepare_threshold=None: required by Supabase's transaction pooler
    # (pgbouncer can't hold prepared statements); harmless on direct conns.
    return psycopg.connect(config.database_url(), autocommit=True,
                           connect_timeout=15, prepare_threshold=None)


def init_schema(conn: psycopg.Connection) -> None:
    conn.execute(SCHEMA_PATH.read_text(encoding="utf-8"))


def get_cursor(conn: psycopg.Connection, sense: str, source_id: str) -> str | None:
    row = conn.execute(
        "SELECT last_item_id FROM sense_cursors WHERE sense = %s AND source_id = %s",
        (sense, source_id),
    ).fetchone()
    return row[0] if row else None


def set_cursor(conn: psycopg.Connection, sense: str, source_id: str, last_item_id: str) -> None:
    conn.execute(
        """
        INSERT INTO sense_cursors (sense, source_id, last_item_id, last_run_at)
        VALUES (%s, %s, %s, now())
        ON CONFLICT (sense, source_id)
        DO UPDATE SET last_item_id = EXCLUDED.last_item_id, last_run_at = now()
        """,
        (sense, source_id, last_item_id),
    )


def insert_sense_rows(conn: psycopg.Connection, table: str, rows: list[dict]) -> int:
    """Append observations. Idempotent: duplicates are skipped, never updated."""
    inserted = 0
    with conn.cursor() as cur:
        for r in rows:
            cur.execute(
                f"""
                INSERT INTO {table} (coin, observed_at, source_id, payload)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (r.get("coin"), r["observed_at"], r["source_id"], json.dumps(r["payload"])),
            )
            inserted += cur.rowcount
    return inserted
