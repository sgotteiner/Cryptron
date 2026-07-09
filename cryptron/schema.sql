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

-- Sense-layer plumbing: where each collector left off, so restarts resume
-- with no missed items and no duplicates.
CREATE TABLE IF NOT EXISTS sense_cursors (
  sense        TEXT NOT NULL,
  source_id    TEXT NOT NULL,
  last_item_id TEXT,
  last_run_at  TIMESTAMPTZ,
  PRIMARY KEY (sense, source_id)
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
-- (embedding VECTOR column arrives with the recall milestone — pgvector.)
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
