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

-- The outcomes knowledge base: coins we KNOW won or lost, and how. One row =
-- one call judged under one way of trading it (no universal score, §4 — the
-- same call can be a win under hold_and_let_run and a loss under tight TP/SL).
-- Comparison experiments JOIN this against the background senses captured.
CREATE TABLE IF NOT EXISTS call_outcomes (
  id          BIGSERIAL PRIMARY KEY,
  coin        TEXT NOT NULL,
  source_id   TEXT NOT NULL,        -- which group called it
  called_at   TIMESTAMPTZ NOT NULL, -- first mention
  organ       TEXT NOT NULL,        -- how "win" was defined
  config      JSONB NOT NULL,       -- the organ's parameters
  entry       DOUBLE PRECISION,
  peak_pct    DOUBLE PRECISION,
  low_pct     DOUBLE PRECISION,
  close_pct   DOUBLE PRECISION,
  win         BOOLEAN,              -- NULL = not priceable / window still open
  pnl_pct     DOUBLE PRECISION,
  note        TEXT,                 -- e.g. 'not on CEX'
  computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (coin, source_id, called_at, organ, config)
);
CREATE INDEX IF NOT EXISTS idx_call_outcomes_win
  ON call_outcomes (source_id, organ, win);

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

-- A lesson that redirected a LIVE thread is a bead on that path (memory_design.md
-- §6): it carries the address of the exact transition it caused, so replay shows
-- the pivot where it happened. Global lessons keep NULLs and ride the playbook.
ALTER TABLE guidance ADD COLUMN IF NOT EXISTS thread_id TEXT REFERENCES threads(id);
ALTER TABLE guidance ADD COLUMN IF NOT EXISTS after_experiment TEXT REFERENCES experiments(id);
-- Selective injection (memory_design §6: never SELECT-everything): lessons are
-- retrieved by relevance to the message, not dumped wholesale into every call.
ALTER TABLE guidance ADD COLUMN IF NOT EXISTS embedding VECTOR(1536);

-- The situation graph (his design, 2026-07-18): one taught edge = "in this
-- situation, the next step is X". Situations are CANONICAL (names become
-- placeholders, values become log forms + class words) so similarity differs
-- only where differences MEAN something. Edges come from teachings ONLY.
CREATE TABLE IF NOT EXISTS taught_steps (
  id          SERIAL PRIMARY KEY,
  guidance_id INT REFERENCES guidance(id),  -- every edge traces to a teaching
  situation   TEXT NOT NULL,                -- canonical rendering
  action      JSONB NOT NULL,               -- {"tool","args_hint"} | {"kind":"verdict"}
  features    JSONB,                        -- raw numeric features (log cap, age…)
  embedding   VECTOR(1536),
  active      BOOLEAN NOT NULL DEFAULT true,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
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

-- ── The sentiment/attention senses (all free) ──────────────────────────────

-- Reddit is a stream sense: posts have native ids (fullnames like 't3_abc').
CREATE TABLE IF NOT EXISTS sense_reddit (
  id          BIGSERIAL PRIMARY KEY,
  coin        TEXT,                  -- NULL at capture; enricher work
  observed_at TIMESTAMPTZ NOT NULL,  -- post creation time
  captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  source_id   TEXT NOT NULL,         -- which subreddit watch
  payload     JSONB NOT NULL         -- post_id, title, selftext, score, num_comments…
);
CREATE INDEX IF NOT EXISTS idx_sense_reddit_source_time
  ON sense_reddit (source_id, observed_at);
CREATE UNIQUE INDEX IF NOT EXISTS uq_sense_reddit_post
  ON sense_reddit (source_id, (payload->>'post_id'));

-- News is a stream sense over RSS feeds: items have native guids/links.
CREATE TABLE IF NOT EXISTS sense_news (
  id          BIGSERIAL PRIMARY KEY,
  coin        TEXT,
  observed_at TIMESTAMPTZ NOT NULL,  -- published time
  captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  source_id   TEXT NOT NULL,         -- which feed
  payload     JSONB NOT NULL         -- item_id, title, summary, link
);
CREATE INDEX IF NOT EXISTS idx_sense_news_source_time
  ON sense_news (source_id, observed_at);
CREATE UNIQUE INDEX IF NOT EXISTS uq_sense_news_item
  ON sense_news (source_id, (payload->>'item_id'));

-- Fear & Greed (alternative.me) publishes one index value per day and serves
-- FULL history — backfillable, deduped on the value's own timestamp.
CREATE TABLE IF NOT EXISTS sense_feargreed (
  id          BIGSERIAL PRIMARY KEY,
  coin        TEXT,                  -- always NULL: market-wide regime
  observed_at TIMESTAMPTZ NOT NULL,  -- the index day
  captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  source_id   TEXT NOT NULL,
  payload     JSONB NOT NULL         -- value, classification
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_sense_feargreed_day
  ON sense_feargreed (source_id, observed_at);

-- CoinGecko is a snapshot sense: per-coin crowd sentiment (bullish/bearish
-- votes, watchlist users, community size). Votes are ephemeral — captured on
-- every lookup; history exists only from the day capture started.
CREATE TABLE IF NOT EXISTS sense_coingecko (
  id          BIGSERIAL PRIMARY KEY,
  coin        TEXT,                  -- the symbol; known natively here
  observed_at TIMESTAMPTZ NOT NULL,
  captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  source_id   TEXT NOT NULL,         -- 'lookup' | watchlist name
  payload     JSONB NOT NULL         -- sentiment votes, watchlist, community
);
CREATE INDEX IF NOT EXISTS idx_sense_coingecko_coin_time
  ON sense_coingecko (coin, observed_at);
CREATE UNIQUE INDEX IF NOT EXISTS uq_sense_coingecko_snapshot
  ON sense_coingecko (source_id, coin, observed_at);

-- DEX snapshots: every GeckoTerminal lookup AND trending-pools poll is
-- captured (price/liquidity/fdv of gem pools, and WHICH pools the crowd is
-- piling into right now, is exactly the ephemeral data §6.4 exists for).
CREATE TABLE IF NOT EXISTS sense_dex (
  id          BIGSERIAL PRIMARY KEY,
  coin        TEXT,                  -- the searched symbol
  observed_at TIMESTAMPTZ NOT NULL,
  captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  source_id   TEXT NOT NULL,         -- 'lookup'
  payload     JSONB NOT NULL         -- pool: network, address, price, liquidity, fdv…
);
CREATE INDEX IF NOT EXISTS idx_sense_dex_coin_time
  ON sense_dex (coin, observed_at);
CREATE UNIQUE INDEX IF NOT EXISTS uq_sense_dex_snapshot
  ON sense_dex (source_id, coin, observed_at, (payload->>'pool_id'));
