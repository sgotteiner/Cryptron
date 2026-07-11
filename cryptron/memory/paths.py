"""The path layer (memory_design.md §6): the retrieval unit is the PATH.

An investigation is a chain of beads on a thread. The beads are experiments —
and the guidance pivots that redirected them: "check the trend first" is what
turned one experiment into the next, so replay must show the pivot at the
exact transition it caused, or the path replays without its reasons.

The playbook lives here too: a lesson is either global (rides on every prompt)
or a pivot on a live thread (carries the address of the transition it caused).
"""
from . import finds


def open_thread(conn, thread_id: str, question: str, parent: str | None = None,
                status: str = "open") -> dict:
    """The unit of focus. Re-opening an existing thread updates its status."""
    conn.execute("""
        INSERT INTO threads (id, question, status, parent) VALUES (%s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
          question = EXCLUDED.question, status = EXCLUDED.status""",
        (thread_id, question, status, parent))
    return {"thread": thread_id, "status": status,
            "note": "pass thread_id to record_experiment so its beads land on this path"}


def save_guidance(conn, lesson: str, why: str = "", provenance: str = "user",
                  thread_id: str | None = None,
                  after_experiment: str | None = None) -> dict:
    """Ask once -> learned. Anchored (thread_id, after_experiment) = a pivot bead."""
    conn.execute("""
        INSERT INTO guidance (lesson, why, provenance, thread_id, after_experiment)
        VALUES (%s, %s, %s, %s, %s)""",
        (lesson, why, provenance, thread_id, after_experiment))
    return {"learned": lesson} | ({"pivot_on": thread_id} if thread_id else {})


def load_guidance(conn) -> list:
    return conn.execute("""
        SELECT lesson, why FROM guidance WHERE active ORDER BY id LIMIT 40""").fetchall()


def replay(conn, thread_id: str) -> dict:
    """The path, in order: experiments interleaved with the pivots that caused
    them, plus the finds the thread crystallized into."""
    thread = conn.execute("SELECT question, status, parent FROM threads WHERE id = %s",
                          (thread_id,)).fetchone()
    if not thread:
        known = [r[0] for r in conn.execute("SELECT id FROM threads").fetchall()]
        return {"error": f"no such thread: {thread_id}", "known_threads": known}
    exps = conn.execute("""
        SELECT id, hypothesis, config, sample, market_adjusted, result, reading,
               created_at
        FROM experiments WHERE thread_id = %s ORDER BY created_at, id""",
        (thread_id,)).fetchall()
    pivots = conn.execute("""
        SELECT lesson, why, after_experiment, created_at FROM guidance
        WHERE thread_id = %s AND active ORDER BY id""", (thread_id,)).fetchall()

    pos = {e[0]: i for i, e in enumerate(exps)}
    beads = [(i, 0, {"bead": "experiment", "id": e[0], "hypothesis": e[1],
                     "config": e[2], "sample": e[3], "market_adjusted": e[4],
                     "result": e[5], "reading": (e[6] or "")[:300]})
             for i, e in enumerate(exps)]
    for lesson, why, after, created in pivots:
        # Anchored pivots sit right after their experiment; unanchored ones
        # fall into place by time — before the first experiment they precede.
        at = pos.get(after)
        if at is None:
            at = sum(1 for e in exps if e[7] <= created) - 1
        beads.append((at, 1, {"bead": "user-pivot", "lesson": lesson, "why": why}))
    beads.sort(key=lambda b: (b[0], b[1]))
    return {"thread": thread_id, "question": thread[0], "status": thread[1],
            "parent": thread[2], "path": [b[2] for b in beads],
            "finds_born": _finds_touching([e[0] for e in exps])}


def _finds_touching(exp_ids: list) -> list:
    """Where the path crystallized: finds whose evidence cites these experiments."""
    out = []
    if not (exp_ids and finds.FINDS_DIR.exists()):
        return out
    for path in sorted(finds.FINDS_DIR.glob("*.md")):
        meta, _ = finds.parse(path)
        ev = meta.get("evidence") or {}
        cited = set(ev.get("supporting") or []) | set(ev.get("contradicting") or [])
        if cited & set(exp_ids):
            out.append({"id": meta["id"], "statement": meta.get("statement"),
                        "status": meta.get("status")})
    return out
