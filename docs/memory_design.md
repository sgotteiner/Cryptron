# Cryptron — Memory Design

> The last design doc. Memory is the shared infrastructure (§6: one bloodstream, creature-level);
> hands plug in one at a time afterward and scale. This doc fixes the three contracts that make
> that possible: **the shape of a find**, **the id spine**, and **the retrieval contract**.
> Everything else (which hand next, thresholds, MAS vs single loop) is discovered by running.
>
> Grounding: [`cryptron_creature.md`](cryptron_creature.md) §6 (memory), §7 (brain), §9 (patterns),
> §15 #1 (the gate this doc closes). Worked example throughout:
> [`investigation_example.md`](investigation_example.md) — the Telegram → memes → attention trace.

---

## 1. What memory is for

Cryptron is an investigator. The human limits it removes are **coverage, memory, processing** —
the reasoning already works but starves. So memory's job, stated as the user stated it:

> *document the finds in an efficient way so the brain can reason easily over good data.*

Two consequences drive the whole design:

1. **Different things, different physics.** A comment-count snapshot and a conclusion like
   *"attention drives memes"* are nothing alike. Don't force uniformity on the content —
   standardize the **envelope** and split the layers.
2. **Retrieval is the intelligence.** The LLM reasoning over a slice is a commodity; *choosing
   the slice* — "what comes to mind" — is where the investigation's skill lived. Memory must
   make that mechanical.

---

## 2. Two systems, three roles

| Role | Question it answers | System |
|---|---|---|
| **Compute** | aggregate, market-adjust, backtest, contrast winners/losers | SQL (Supabase/Postgres) |
| **Recall** | "what's like this?" — fuzzy, emergent similarity | `pgvector` (a column in the same DB, not a separate product) |
| **Reason & trust** | validated finds, human-readable, auditable | markdown vault (Obsidian-compatible) |

Two moving parts only: **Supabase (raw + experiments + embeddings)** and **a folder of markdown
(the finds)**, welded by one id spine. The vault is the human/authoring face — the surface where
the user reads what Cryptron concluded and corrects it (§11, progressive autonomy) — and its
content is also embedded into `pgvector` for recall.

---

## 3. Layer 1 — Raw evidence (SQL)

Append-only. Never deleted. Its one non-negotiable job: **capture ephemeral data the instant it
is sensed** (comment counts, CMC votes, market state) — not saved at sense-time means gone
forever and the experiment becomes impossible later (§6.4).

### The spine of the layer: `(coin, time)`

Every observation, from every sense, is a fact about *a coin at a moment*. That shared key is
what lets an experiment ask "what did we know about this coin *then*."

### Sense tables — one per sense, flexible payload

New hands must plug in without migrations (§13: the body grows parts). So each sense table is a
few indexed columns + JSONB:

```sql
-- one table per sense; identical skeleton
CREATE TABLE sense_telegram (        -- likewise: sense_ohlcv, sense_cmc, sense_social, sense_youtube…
  id          BIGSERIAL PRIMARY KEY,
  coin        TEXT,                  -- nullable: some observations are market-wide
  observed_at TIMESTAMPTZ NOT NULL,  -- when the world showed it
  captured_at TIMESTAMPTZ NOT NULL,  -- when we saved it (ephemeral-capture audit)
  source_id   TEXT,                  -- group / channel / endpoint
  payload     JSONB                  -- sense-specific content, schema-free
);
CREATE INDEX ON sense_telegram (coin, observed_at);
```

Adding a hand = adding one table with this skeleton + the collector that fills it. Nothing else
changes. (Plus one piece of shared plumbing: a `sense_cursors` table records where each
collector left off per source, so restarts resume with no missed items and no duplicates —
sense tables also carry a uniqueness key on the source's native item id, making capture
idempotent.)

### Experiments — first-class, not a junction

An experiment is an entity with its own attributes; it *references* the sense-rows it consumed:

```sql
CREATE TABLE experiments (
  id             TEXT PRIMARY KEY,          -- 'exp-0011'
  thread_id      TEXT REFERENCES threads(id),
  hypothesis     TEXT,                      -- pre-registered, falsifiable
  config         JSONB,                     -- the atom-values tried
  testing_organ  JSONB,                     -- how "win" was defined (§4: no universal score)
  window_from    TIMESTAMPTZ, window_to TIMESTAMPTZ,
  sample         TEXT,                      -- 'in' | 'oos'  (out-of-sample flag — the validity gate)
  market_adjusted BOOLEAN,                  -- beta removed? (the null-model discipline)
  result         JSONB,                     -- winrate, expectancy, n, drawdown, baselines
  reading        TEXT,                      -- the brain's interpretation, written at analyze-time
  embedding      VECTOR(1536),              -- pgvector: hypothesis+scope+result summary
  created_at     TIMESTAMPTZ
);

CREATE TABLE experiment_inputs (             -- provenance down to the raw rows
  experiment_id TEXT REFERENCES experiments(id),
  source_table  TEXT,                       -- 'sense_telegram'
  row_id        BIGINT
);

CREATE TABLE threads (                       -- the unit of focus (§8)
  id       TEXT PRIMARY KEY,                -- 'thread-meme-attention'
  question TEXT,                            -- the line of inquiry
  status   TEXT,                            -- open | stable-good | stable-bad | dormant
  parent   TEXT                             -- the thread/find that spawned it
);
```

`sample` and `market_adjusted` are columns, not conventions — the immune system is enforced by
the schema: a find whose evidence has no `oos=true`, `market_adjusted=true` experiment **cannot
reach `active` status** (see §5).

---

## 4. Layer 2 — Finds (the vault)

The distilled layer the brain reasons over. Small, curated, human-readable. Everything here is
one of exactly two kinds sharing one spine — the **atom**:

- a **config** — settled atom-values for a molecule/tissue/organ (procedural memory: "how it moves now")
- a **conclusion** — a pattern that generalizes, stated as a **directive over atoms**

Welded by the rule: **a conclusion is only good data if it moves a knob.** A find that doesn't
cash out as prefer/avoid over atoms is a fact, not a find.

### The find shape — uniform envelope, two payloads

One markdown file per find. Frontmatter is the envelope (identical for both kinds); the body is
free text (full reasoning, what would kill this find, open questions).

**A conclusion** (from the worked trace, after the market-fell counterexample):

```markdown
---
id: find-0042
kind: conclusion
scope:                        # THE ADDRESS — retrieval matches on this
  level: tissue               # atom | molecule | tissue | organ | creature
  domain: telegram-signals
  class: meme                 # coin-class; '*' = universal
  condition: market-adjusted  # qualifiers EARNED by counterexamples
statement: >
  Leading, multi-channel attention (vs the coin's own baseline) separates
  meme winners from losers — measured as excess return vs the market.
mechanism: >
  Memes have no fundamentals; attention IS the fundamental. Thin books,
  reflexive crowds — attention converts directly into price.
directive:
  prefer:
    - attention_filter: {spike_vs_baseline: high, must_lead_price: true, channels: ">=2"}
    - exit: hold_and_let_run
  avoid:
    - exit: tight_tp_sl        # cages the moonshot that pays for the losers
confidence: 0.55
status: active                 # candidate | active | narrowed | dead
evidence:
  supporting: [exp-0009, exp-0010, exp-0012]
  contradicting: [exp-0011]    # many-comments coin that fell WITH the market
history:
  - 2026-07-08: born — winners/losers contrast (1300 vs 50 comments)
  - 2026-07-09: narrowed — 'market-adjusted' condition added after exp-0011
links: ["[[find-0038-memes-are-their-own-tissue]]", "[[find-0007-market-is-the-null-model]]"]
---
Body: full reasoning; what would kill it (attention spike that leads price,
multi-channel, market-adjusted — and the coin still doesn't outperform);
open questions (bot-detection? sentiment tone? threshold value?).
```

**A config:**

```markdown
---
id: config-0017
kind: config
scope: {level: tissue, domain: telegram-signals, target: group-2, class: meme}
atoms:
  entry_offset: none
  exit: hold_and_let_run
  attention_filter: {min_spike_vs_baseline: 5.0, must_lead_price: true}
score: {expectancy_pct: +0.4, n: 50, oos: true, market_adjusted: true}
status: candidate              # candidate | promoted | retired
evidence: [exp-0012]
derived_from: ["[[find-0042]]", "[[find-0038]]"]
---
```

### Why this earns "efficient"

One conclusion stands in for its whole evidence pile — the brain reasons over hundreds of dense
finds, not millions of raw rows, and drills down the spine only to verify or when a find breaks.
Compression is the efficiency *and* the "good data": a find has already passed the disciplines,
so reasoning can trust it without re-deriving.

---

## 5. The id spine — one chain, fully auditable

```
find-0042  (vault)
  └─ evidence: exp-0009, exp-0011, …        (experiments table)
        └─ experiment_inputs → sense_social row 88231, sense_telegram row 4410, …
              └─ (coin, observed_at) → everything else known at that moment
```

Every belief is walkable down to the raw observations that support it — "why do you believe
this?" is a query, not an argument. The spine is also the **decay detector**: all supporting
evidence old + recent evidence contradicting = the world changed, re-open the thread.

**Status lifecycle (the immune system, enforced):**

```
candidate ──(≥1 oos AND market-adjusted supporting experiment)──▶ active
active ──(counterexample explained by a condition)──▶ narrowed (scope tightens, stays active)
active ──(counterexample NOT explained; confidence below floor)──▶ dead (kept, marked — deaths are data)
```

Confidence **updates, never overwrites** (§6). Contradicting evidence is stored on the find
forever — a find with no contradicting slot ever filled is a find nobody tried to kill.

---

## 6. The retrieval contract — how memory feeds the next investigation

**The core claim: every operator in the question catalog compiles to a memory query.** "What
comes to mind" stops being a mystery and becomes three access paths:

| Path | Mechanism | What it answers |
|---|---|---|
| **Scope-match** | exact match on the find envelope's `scope` coordinates | "what applies to this situation?" |
| **Vector recall** | `pgvector` nearest-neighbor over experiments + finds | "what's *like* this?" (similarity never declared) |
| **Spine/link-walk** | ids down to raw; `[[links]]` across finds | "why do we believe X?" / "what relates to X?" |

### Operator → query table

| Investigation moment | Operator | The memory query | Path |
|---|---|---|---|
| New signal arrives | **Classify** + recall | classify coin (cap, age, sector from sense tables) → fetch all finds `WHERE scope matches (domain, class, condition)` | scope-match |
| Designing the next experiment | **Perturb** / prune | fetch `directive`s in scope → delete pruned regions of the atom space *before* running (§9 coverage) | scope-match |
| Surprising result | **Why?** | nearest-neighbor on the result's embedding: "seen this shape before?" (e.g. low-winrate-but-small-loss → past 'mix, not failure' cases) | vector |
| Result splits oddly | **Contrast / Decompose** | SQL over experiments+raw: winners vs losers in scope, grouped by every attribute on the spine | compute |
| "Did it happen elsewhere?" | **Generalize** | neighboring scopes: same `directive`/driver, different `class`/`domain` | link-walk + scope |
| Analogy ("CMC upvotes → Twitter sentiment?") | **Transfer** | vector recall across *domains* on the mechanism text | vector |
| "What else about this coin?" | **Enrich** | all sense rows at `(coin, observed_at ± window)` — incl. ephemeral snapshots captured then | spine |
| Result contradicts a find | **Belief revision** | the find + its full evidence chain; re-read contradicting vs supporting | spine |
| Idle / scout returns a candidate | **Rank** | score the candidate against finds that have been *paying* (§10 for-you feed) | vector + confidence |

### The compounding effect — the point of it all

Replay the worked trace *with* memory in place:

- **Cold (as it actually ran):** ~11 experiments to get from "10% — garbage" to the attention find.
- **Next meme group arrives:** classify → scope-match serves `[[find-0038]]` (memes = own tissue,
  hold-and-let-run), `[[find-0042]]` (attention filter), `[[find-0007]]` (market-adjust
  everything) *before the first experiment*. The config space is pre-pruned; the ephemeral
  attention snapshot is captured on arrival because the find's directive demands it. Cost: **~2
  experiments** — validate the playbook on this group, tune the threshold.
- **A group of unknown class arrives:** scope-match returns thin → *that absence is itself the
  signal* to open a classification thread first.

Memory converts investigations from **repeated to compounding**. That is the starvation cure:
not more reasoning — the right slice, served before the question is finished being asked.

### Learned retrieval — the similarity space improves

Embeddings cluster on surface features (coin, strategy, timeframe) — the *proxies*. The
investigation's whole skill was digging past proxies to *drivers* (regime, attention, class).
So retrieval must learn: **every confirmed driver becomes a scope dimension.** Before the
market-fell insight, "regime" wasn't retrievable-by; after, `condition:` carries it and
experiments are re-indexed. Recall drifts from surface-space toward driver-space exactly as
fast as the creature learns what actually matters. (Vector recall proposes; the envelope's
confidence/status decides what's *trusted* — similarity is an access path, never the truth.)

---

## 7. Write paths — when memory is written

1. **Sense-time (automatic, unconditional):** every observation → its sense table the moment it
   is seen. Ephemeral data has no second chance. Collectors are dumb and reliable.
2. **Run-time:** experiment row written at design-time (hypothesis pre-registered — no
   goalpost-moving), `result` + `reading` at analyze-time.
3. **Analyze-time:** finds born (`candidate`), promoted, narrowed, or killed. History line
   appended — the find's biography is part of the find.
4. **Chat-time:** the user's corrections and priors become finds like any other, marked
   `provenance: user` with high starting confidence. (Seeding, §8 below.)

---

## 8. Cold start — seed, don't brute-force

An empty vault forces the brain to rediscover the user's judgment. Instead, the first finds are
**hand-written priors**: *memes want hold-and-let-run; market-adjust everything; leading not
coincident; tight SLs poison volatile alts; …* — each in the standard shape, `provenance: user`,
so the investigator inherits taste on day one and experiments *against* the priors (they have
confidence and can be narrowed or killed like anything else).

---

## 9. Deliberately not decided (discovered by running)

- Threshold values (confidence floor, promotion bar, attention spike multiple) — atoms, to be tuned.
- Embedding model / dimension; chunking of find bodies.
- Whether finds need their own table mirroring the vault for fast scope queries (likely yes —
  vault stays the source of truth, DB row is the index).
- MAS decomposition (§14) — irrelevant to memory's contracts; any number of agents can share this bloodstream.
- Exact classification taxonomy for `class:` — grows as classes are *discovered* (memes was discovered, not pre-listed).

---

## 10. The build gate, restated

This doc closes §15 #1. The design is *done enough* when the find shape survives one real
thread on paper — the meme-attention trace instantiated end-to-end: capture → experiment →
find → retrieval serving the next experiment cheaper. The first slice to build is exactly
that thread, with **one hand** (Telegram or price), the two systems above, and nothing else.
Every additional hand scales the same skeleton.
