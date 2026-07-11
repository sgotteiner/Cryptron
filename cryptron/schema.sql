-- Cryptron memory, layer 1: raw evidence (memory_design.md §3).
-- Append-only. Ephemeral data is captured the moment it is sensed.

-- One table per sense; identical skeleton. coin is nullable and left NULL
-- at capture time — parsing/classification is enricher work, not the collector's.
CREATE TABLE IF NOT EXISTS sense_telegram (
  id          BIGSERIAL PRIMARY KEY,
  coin        TEXT,
  observed_at TIMESTAMPTZ NOT NULL,  -- when the world showed it
  captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),  -- when we saved it
  source_id   TEXT NOT NULL,         -- which group
  payload     JSONB NOT NULL         -- sense-specific content, schema-free
);
CREATE INDEX IF NOT EXISTS idx_sense_telegram_coin_time
  ON sense_telegram (coin, observed_at);
CREATE INDEX IF NOT EXISTS idx_sense_telegram_source_time
  ON sense_telegram (source_id, observed_at);
-- Idempotent capture: re-running the collector never duplicates a message.
CREATE UNIQUE INDEX IF NOT EXISTS uq_sense_telegram_msg
  ON sense_telegram (source_id, ((payload->>'message_id')::bigint));

-- CMC is a snapshot sense: no native item id — observed_at is fetch time and
-- every run appends a new snapshot (ephemeral data, gone if not captured now).
CREATE TABLE IF NOT EXISTS sense_cmc (
  id          BIGSERIAL PRIMARY KEY,
  coin        TEXT,                  -- the symbol; known natively here
  observed_at TIMESTAMPTZ NOT NULL,
  captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  source_id   TEXT NOT NULL,
  payload     JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sense_cmc_coin_time
  ON sense_cmc (coin, observed_at);
CREATE UNIQUE INDEX IF NOT EXISTS uq_sense_cmc_snapshot
  ON sense_cmc (source_id, coin, observed_at);

-- Twitter is a stream sense like Telegram: tweets have native ids.
CREATE TABLE IF NOT EXISTS sense_twitter (
  id          BIGSERIAL PRIMARY KEY,
  coin        TEXT,                  -- stamped from the target's coin, if any
  observed_at TIMESTAMPTZ NOT NULL,
  captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  source_id   TEXT NOT NULL,         -- which query/watch
  payload     JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sense_twitter_coin_time
  ON sense_twitter (coin, observed_at);
CREATE INDEX IF NOT EXISTS idx_sense_twitter_source_time
  ON sense_twitter (source_id, observed_at);
CREATE UNIQUE INDEX IF NOT EXISTS uq_sense_twitter_tweet
  ON sense_twitter (source_id, ((payload->>'tweet_id')::bigint));

-- The dialogue is a sense too (creature doc §11): every user/assistant turn
-- is captured — the user's guidance is evidence with provenance.
CREATE TABLE IF NOT EXISTS sense_chat (
  id          BIGSERIAL PRIMARY KEY,
  coin        TEXT,
  observed_at TIMESTAMPTZ NOT NULL,
  captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  source_id   TEXT NOT NULL,         -- telegram chat id
  payload     JSONB NOT NULL         -- {role, text, message_id}
);
CREATE INDEX IF NOT EXISTS idx_sense_chat_source_time
  ON sense_chat (source_id, observed_at);

-- Sense-layer plumbing: where each collector left off, so restarts resume
-- with no missed items and no duplicates.
CREATE TABLE IF NOT EXISTS sense_cursors (
  sense        TEXT NOT NULL,
  source_id    TEXT NOT NULL,
  last_item_id TEXT,
  last_run_at  TIMESTAMPTZ,
  PRIMARY KEY (sense, source_id)
);

-- The playbook: lessons the user taught (or the brain inferred) that must be
-- applied automatically to every future investigation. Ask once -> learned.
CREATE TABLE IF NOT EXISTS guidance (
  id         SERIAL PRIMARY KEY,
  lesson     TEXT NOT NULL,        -- the directive, stated generally
  why        TEXT,                 -- the mechanism/reason behind it
  provenance TEXT NOT NULL DEFAULT 'user',  -- user | brain
  active     BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- The unit of focus (creature doc §8).
CREATE TABLE IF NOT EXISTS threads (
  id       TEXT PRIMARY KEY,
  question TEXT,
  status   TEXT NOT NULL DEFAULT 'open',  -- open | stable-good | stable-bad | dormant
  parent   TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Experiments are first-class, not a junction (memory_design.md §3).
-- The immune system is enforced by schema: sample and market_adjusted are columns.
-- (embedding VECTOR is ALTERed onto this table below, with the layer-2 section.)
CREATE TABLE IF NOT EXISTS experiments (
  id              TEXT PRIMARY KEY,          -- 'exp-0001'
  thread_id       TEXT REFERENCES threads(id),
  hypothesis      TEXT,                      -- pre-registered, falsifiable
  config          JSONB,                     -- the atom-values tried
  testing_organ   JSONB,                     -- how "win" was defined
  window_from     TIMESTAMPTZ,
  window_to       TIMESTAMPTZ,
  sample          TEXT,                      -- 'in' | 'oos'
  market_adjusted BOOLEAN,
  result          JSONB,
  reading         TEXT,                      -- the brain's interpretation
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Provenance down to the raw rows.
CREATE TABLE IF NOT EXISTS experiment_inputs (
  experiment_id TEXT NOT NULL REFERENCES experiments(id),
  source_table  TEXT NOT NULL,
  row_id        BIGINT NOT NULL,
  PRIMARY KEY (experiment_id, source_table, row_id)
);

-- ── Memory, layer 2: finds (memory_design.md §4-6) ─────────────────────────
-- The vault (finds/*.md) is the source of truth; this table is its INDEX —
-- the query surface for scope-match and vector recall. Rebuildable any time
-- from the files:  python -m cryptron.memory
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS finds (
  id         TEXT PRIMARY KEY,       -- 'find-0042' | 'config-0017'
  kind       TEXT NOT NULL,          -- conclusion | config
  scope      JSONB NOT NULL,         -- THE ADDRESS: level/domain/class/condition
  statement  TEXT,
  confidence REAL,
  status     TEXT NOT NULL,          -- candidate|active|narrowed|dead (configs: promoted|retired)
  provenance TEXT,                   -- user | brain
  body_hash  TEXT,                   -- re-embed only when content changed
  embedding  VECTOR(1536),           -- gemini-embedding-001, L2-normalized
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Vector recall spans experiments too (§6: "seen this shape before?").
ALTER TABLE experiments ADD COLUMN IF NOT EXISTS embedding VECTOR(1536);
