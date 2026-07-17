"""The finds vault (memory_design.md §4-5): one markdown file per find.

The vault is the source of truth; the `finds` DB table is its index.
Every write goes file-first, then index. Uniform envelope, two kinds
(conclusion | config), one lifecycle — and the immune system is enforced
here: 'active' must be EARNED by an out-of-sample, market-adjusted experiment.
"""
import hashlib
import json
import re
from datetime import date

import yaml

from ..config import ROOT
from . import embed

FINDS_DIR = ROOT / "finds"


def parse(path) -> tuple[dict, str]:
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?(.*)$",
                 path.read_text(encoding="utf-8"), re.S)
    if not m:
        raise ValueError(f"{path.name}: no frontmatter envelope")
    return yaml.safe_load(m.group(1)), m.group(2).strip()


def render(meta: dict, body: str) -> str:
    front = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True, width=100)
    return f"---\n{front}---\n{body.strip()}\n"


def find_path(find_id: str):
    """Accepts a bare id ('find-0042') or a full link name ('find-0042-slug')."""
    hits = sorted(FINDS_DIR.glob(f"{find_id}*.md"))
    if not hits:
        raise FileNotFoundError(f"no such find: {find_id}")
    return hits[0]


def next_id(kind: str) -> str:
    prefix = "config" if kind == "config" else "find"
    ns = [int(m.group(1)) for p in FINDS_DIR.glob(f"{prefix}-*.md")
          if (m := re.match(rf"{prefix}-(\d+)", p.name))]
    return f"{prefix}-{max(ns, default=0) + 1:04d}"


def index_text(meta: dict) -> str:
    """What a find 'sounds like' in the similarity space: claim + mechanism + address."""
    parts = [meta.get("statement", ""), meta.get("mechanism", ""),
             "scope: " + json.dumps(meta.get("scope", {})),
             "directive: " + json.dumps(meta.get("directive") or meta.get("atoms") or {})]
    return "\n".join(str(p) for p in parts if p)


async def index_find(conn, meta: dict, body: str) -> None:
    """Upsert the index row; re-embed only when the content actually changed."""
    digest = hashlib.sha256(
        (json.dumps(meta, sort_keys=True, default=str) + body).encode()).hexdigest()
    row = conn.execute("SELECT body_hash FROM finds WHERE id = %s",
                       (meta["id"],)).fetchone()
    vec = None
    if not row or row[0] != digest:
        vec = json.dumps(await embed.embed(index_text(meta)))
    conn.execute("""
        INSERT INTO finds (id, kind, scope, statement, confidence, status,
                           provenance, body_hash, embedding, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::vector, now())
        ON CONFLICT (id) DO UPDATE SET
          kind = EXCLUDED.kind, scope = EXCLUDED.scope,
          statement = EXCLUDED.statement, confidence = EXCLUDED.confidence,
          status = EXCLUDED.status, provenance = EXCLUDED.provenance,
          body_hash = EXCLUDED.body_hash, updated_at = now(),
          embedding = COALESCE(EXCLUDED.embedding, finds.embedding)""",
        (meta["id"], meta.get("kind"), json.dumps(meta.get("scope", {})),
         meta.get("statement") or json.dumps(meta.get("atoms", {})),
         meta.get("confidence"), meta.get("status", "candidate"),
         meta.get("provenance"), digest, vec))


async def save_find(conn, slug: str, kind: str, scope: dict, statement: str,
                    mechanism: str = "", directive: dict | None = None,
                    evidence: list | None = None, confidence: float = 0.3,
                    body: str = "", links: list | None = None,
                    provenance: str = "brain") -> dict:
    """A find is born — always 'candidate' (§5: promotion must be earned)."""
    if kind not in ("conclusion", "config"):
        return {"error": f"kind must be 'conclusion' or 'config', not '{kind}'. "
                "Raw data about a coin is NOT a find — it lives in the senses; "
                "a find must move a knob (directive) or settle atom values."}
    FINDS_DIR.mkdir(exist_ok=True)
    fid = next_id(kind)
    slug = re.sub(r"[^a-z0-9-]", "", slug.lower().replace(" ", "-")).strip("-")[:60]
    meta = {"id": fid, "kind": kind, "scope": scope, "statement": statement}
    if mechanism:
        meta["mechanism"] = mechanism
    if directive:
        meta["directive"] = directive
    meta |= {"confidence": confidence, "status": "candidate",
             "provenance": provenance,
             "evidence": {"supporting": evidence or [], "contradicting": []},
             "history": [f"{date.today()}: born"], "links": links or []}
    (FINDS_DIR / f"{fid}-{slug}.md").write_text(render(meta, body), encoding="utf-8")
    await index_find(conn, meta, body)
    return {"saved": fid, "status": "candidate",
            "note": "promote with update_find once an oos+market-adjusted experiment supports it"}


def _earned_promotion(conn, supporting: list) -> bool:
    """§5: 'active' requires >=1 out-of-sample AND market-adjusted supporting experiment."""
    if not supporting:
        return False
    return conn.execute(
        "SELECT count(*) FROM experiments WHERE id = ANY(%s) "
        "AND sample = 'oos' AND market_adjusted", (supporting,)).fetchone()[0] > 0


async def update_find(conn, find_id: str, note: str, status: str | None = None,
                      add_supporting: list | None = None,
                      add_contradicting: list | None = None,
                      confidence: float | None = None,
                      scope: dict | None = None) -> dict:
    """Every change appends to history — the find's biography is part of the find."""
    path = find_path(find_id)
    meta, body = parse(path)
    ev = meta.setdefault("evidence", {"supporting": [], "contradicting": []})
    ev["supporting"] = list(dict.fromkeys(ev.get("supporting", []) + (add_supporting or [])))
    ev["contradicting"] = list(dict.fromkeys(ev.get("contradicting", []) + (add_contradicting or [])))
    # The immune system: user-seeded priors are trusted day one (§8); everything
    # else earns 'active' through the gate. Deaths are data — 'dead' is never blocked.
    if (status in ("active", "promoted") and meta.get("provenance") != "user"
            and not _earned_promotion(conn, ev["supporting"])):
        return {"error": "immune system: promotion needs >=1 supporting experiment "
                         "with sample='oos' AND market_adjusted=true — run it first"}
    if status:
        meta["status"] = status
    if confidence is not None:
        meta["confidence"] = confidence
    if scope:
        meta["scope"] = (meta.get("scope") or {}) | scope
    meta.setdefault("history", []).append(f"{date.today()}: {note}")
    path.write_text(render(meta, body), encoding="utf-8")
    await index_find(conn, meta, body)
    return {"updated": meta["id"], "status": meta.get("status"), "evidence": ev}
