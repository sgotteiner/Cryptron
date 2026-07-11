"""The retrieval contract (memory_design.md §6): three access paths.

scope-match — "what applies to this situation?" (exact match on the address)
vector recall — "what's LIKE this?" (similarity proposes, status/confidence decide trust)
spine/link-walk — "why do we believe X? what path led here?"

Entry by similarity, expansion by links — never SELECT-everything (§6: the
retrieval unit is the PATH, not the fact).
"""
import json
import re

from . import embed, finds


async def recall(conn, text: str, k: int = 6) -> dict:
    """Vector nearest-neighbor over finds AND past experiments."""
    vec = json.dumps(await embed.embed(text, task="RETRIEVAL_QUERY"))
    fs = conn.execute("""
        SELECT id, kind, statement, status, confidence,
               1 - (embedding <=> %s::vector) AS sim
        FROM finds WHERE embedding IS NOT NULL
        ORDER BY embedding <=> %s::vector LIMIT %s""", (vec, vec, k)).fetchall()
    es = conn.execute("""
        SELECT id, hypothesis, reading, 1 - (embedding <=> %s::vector) AS sim
        FROM experiments WHERE embedding IS NOT NULL
        ORDER BY embedding <=> %s::vector LIMIT %s""", (vec, vec, k)).fetchall()
    out = ([{"type": "find", "id": r[0], "kind": r[1], "statement": r[2],
             "status": r[3], "confidence": r[4], "sim": round(r[5], 3)} for r in fs]
           + [{"type": "experiment", "id": r[0], "hypothesis": r[1],
               "reading": (r[2] or "")[:300], "sim": round(r[3], 3)} for r in es])
    out.sort(key=lambda x: -x["sim"])
    return {"matches": out[:k],
            "hint": "similarity is an entry point — read_find(id) and walk its links to replay the path"}


def _fits(find_scope: dict, want: dict) -> bool:
    """A missing key or '*' on the find means 'applies everywhere' on that axis."""
    for key, val in want.items():
        have = find_scope.get(key)
        if have is not None and have != "*" and str(have) != str(val):
            return False
    return True


def in_scope(conn, scope: dict) -> dict:
    """Everything known that applies at this address (dead/retired excluded)."""
    rows = conn.execute("""
        SELECT id, kind, scope, statement, status, confidence FROM finds
        WHERE status NOT IN ('dead', 'retired')""").fetchall()
    hits = [{"id": r[0], "kind": r[1], "scope": r[2], "statement": r[3],
             "status": r[4], "confidence": r[5]} for r in rows if _fits(r[2], scope)]
    out = {"scope": scope, "finds": hits}
    if not hits:
        out["note"] = ("thin result IS a signal: unknown territory — "
                       "consider opening a classification thread first")
    return out


def read(conn, find_id: str) -> dict:
    """The spine walk: the full find + its evidence chain + its link edges."""
    meta, body = finds.parse(finds.find_path(find_id))
    ev = meta.get("evidence") or {}
    ids = list(ev.get("supporting") or []) + list(ev.get("contradicting") or [])
    chain = conn.execute("""
        SELECT id, hypothesis, sample, market_adjusted, result, reading
        FROM experiments WHERE id = ANY(%s)""", (ids,)).fetchall() if ids else []
    return {"find": meta, "body": body,
            "evidence_chain": [{"id": r[0], "hypothesis": r[1], "sample": r[2],
                                "market_adjusted": r[3], "result": r[4],
                                "reading": r[5]} for r in chain],
            "links": re.findall(r"\[\[([^\]]+)\]\]",
                                json.dumps(meta.get("links", [])) + body)}


async def reindex(conn) -> dict:
    """Rebuild the index from the vault files; backfill experiment embeddings."""
    finds.FINDS_DIR.mkdir(exist_ok=True)
    seen = []
    for path in sorted(finds.FINDS_DIR.glob("*.md")):
        meta, body = finds.parse(path)
        await finds.index_find(conn, meta, body)
        seen.append(meta["id"])
    conn.execute("DELETE FROM finds WHERE NOT (id = ANY(%s))", (seen or [""],))
    todo = conn.execute("SELECT id, hypothesis, reading, result FROM experiments "
                        "WHERE embedding IS NULL").fetchall()
    for eid, hyp, reading, result in todo:
        vec = await embed.embed(f"{hyp}\n{reading or ''}\n{json.dumps(result or {}, default=str)}")
        conn.execute("UPDATE experiments SET embedding = %s::vector WHERE id = %s",
                     (json.dumps(vec), eid))
    return {"finds_indexed": len(seen), "experiments_embedded": len(todo)}
