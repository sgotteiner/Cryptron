# CryptoHub — System Design

---

## 1. Why This System Exists

### The Problem

You've built multiple crypto research tools as standalone POCs:

1. **Telegram Signal Verifier** — scraped groups like @BinanceKillers, parsed signals with regex, backtested against real price data via ccxt. The regex was brittle (missed non-standard formats, false positives on chat messages), and it had no scam detection. You want LLM-based parsing instead.

2. **TradingView Pine Strategy Tester** — used a TradingView MCP (78 tools via Chrome DevTools Protocol) to inject and test Pine scripts. Gemini Flash kept forgetting to change tickers, failed to navigate between Pine editor and chart, repeated the same mistakes. Also scraped Pine repos from GitHub via Firecrawl. Results were unreliable without your intervention.

3. **YouTube Influencer Analyzer** — used a YouTube transcript MCP to extract coin mentions from crypto influencers and check if they were good calls. Supposedly exposed one influencer but you don't trust the result because Gemini Flash quality was poor.

4. **eToro Copy Trading Mirror** — tracked a specific trader (@CPHequities) by scraping their public eToro profile, with plans to mirror trades on an accessible broker.

Each tool works in isolation. None of them talk to each other. None of them run automatically. And most importantly — **they can't be combined**. You can't say "get a Telegram signal, then check if 80% of people voted for it on CoinMarketCap, then test it with a Pine strategy, then tell me if I should buy."

### The Vision

You don't know the best trading strategy yet. **If you did, you wouldn't need such a flexible system.** This is not a tool that follows your strategy — it's a tool that **helps you discover your strategy** by:

- Monitoring many signal sources simultaneously
- Evaluating each source's reliability with configurable, transparent metrics
- Combining signals from different sources to find high-conviction opportunities
- Remembering everything so you can connect dots over time
- Running experiments (different evaluation parameters, different combinations) automatically
- Surfacing what works and what doesn't so you can iterate

It's a **personal crypto research assistant** that runs 24/7 on your PC, costs $0, and gets smarter as it accumulates data. Not a trading bot — it doesn't execute trades. It tells you what's worth looking at and why, backed by evidence.

### The Pattern You Identified

Across all your projects, you see a repeating pattern:

- **Agents** that know how to get information from somewhere (Telegram, YouTube, TradingView, eToro, web search, blockchain)
- **Targets** they monitor (specific groups, channels, traders, coins)
- **Configurations** that define how to evaluate what they find (10% gain in a week? 30% in a month? trailing stop-loss simulation?)
- **Pipelines** that chain agents together in ways that combine their insights
- **A database** that remembers what was found, what was analyzed, what worked
- **Notifications** that alert you when something passes your criteria

CryptoHub makes this pattern concrete, configurable, and automated.

---

## 2. Core Hierarchy

```
Pipeline    "Full Signal Check"
  │         Defines what to do when a signal arrives — which agents to run,
  │         in what order, with what conditions for action
  │
  └─ Agent  "Telegram Signal Checker"
       │    Knows how to read Telegram groups, parse messages, produce signals.
       │    One piece of code that can watch many groups.
       │
       └─ Target  "@BinanceKillers"
            │     One specific group, with its OWN evaluation config:
            │     - Check if signals made 10% in 7 days (this group does swing trades)
            │     - Score based on last 50 signals
            │     - Check for pre-pump scams in the 24h before signals
            │
            └─ Signal  "LONG SOL/USDT @ 180, TP 190/200, SL 170"
                       One parsed signal, stored in DB forever.
                       Linked to its target, its evaluation results, its pipeline runs.
```

### Why This Hierarchy

- **Pipelines** are the user-facing concept — "when X happens, do Y and Z"
- **Agents** are the building blocks — reusable pieces of capability
- **Targets** are what agents watch — each with independent configuration because different targets have different behavior (a swing-trading group needs different evaluation than a scalping group)
- **Signals** are the atomic unit of data — everything traces back to a signal

You control the hierarchy at every level: which pipelines are active, which agents they use, which targets each agent watches, how each target is evaluated.

---

## 3. Agents

### What an Agent Is

A Python class that does one thing well. It has:
- A `run(context, input)` method that does its work and returns output
- A config schema that defines what parameters it accepts
- A type: `source`, `enricher`, `strategy`, or `action`

```python
class BaseAgent:
    name: str
    agent_type: str  # source | enricher | strategy | action
    description: str
    config_schema: dict

    async def run(self, ctx: PipelineContext, input_data: Any) -> Any:
        raise NotImplementedError
```

Adding a new agent = write one Python file with a class that extends `BaseAgent`, put it in the `agents/` folder. It's automatically discovered and available in pipelines and the control panel.

### V1 Agents (Build Now)

| Agent | Type | What It Does |
|-------|------|-------------|
| `telegram_reader` | source | Connects to Telegram via Telethon, reads messages from configured groups. Knows where it left off (cursor). |
| `llm_parser` | enricher | Takes raw message text, asks an LLM to extract structured signal data. Returns `null` for non-signal messages (chat, memes, admin posts). |
| `exchange_checker` | enricher | Given a coin symbol, uses ccxt to check which exchanges list it and gets basic market data (volume, price). |
| `price_checker` | enricher | Fetches historical OHLCV data for a coin from the signal time onward. Used by evaluation strategies. |
| `scam_detector` | enricher | Checks for pre-pump patterns: did the coin already pump significantly before the signal was posted? Volume spikes before the signal? |
| `signal_evaluator` | strategy | Runs the target's configured evaluation strategies on a signal using price data. Reports win/loss per strategy. |
| `target_scorer` | strategy | Maintains running win rate and trust grade per target based on accumulated evaluation results. |
| `telegram_notifier` | action | Sends a formatted alert to you via a Telegram bot. |
| `db_saver` | action | Saves signal, analysis results, and pipeline run to Supabase. |

### Future Agents (Architecture Supports, Not Built in V1)

**More Sources:**

| Agent | What It Does | Example Use |
|-------|-------------|-------------|
| `youtube_reader` | Extracts transcripts from YouTube videos, uses LLM to find coin mentions, strategy descriptions, and sentiment. | "CryptoGuru posted a video mentioning SOL and AVAX. Let me check if they went up after the video." |
| `tradingview_pine_tester` | Uses the TradingView MCP to inject a Pine script, run it across multiple tickers and timeframes, and read strategy results. Only works when your PC has TradingView open. | "Test the CryptoSlaya script on BTC 4H and SOL 1H. Report win rate and drawdown." |
| `etoro_scraper` | Scrapes a public eToro trader's portfolio to detect new positions. | "CPHequities just opened a LONG on AAPL. Check if it aligns with any other signals I have." |
| `cmc_checker` | Scrapes CoinMarketCap for community votes, market cap, circulating supply, token info. | "80% of CMC voters are bullish on this coin and it has $50M daily volume — looks legitimate." |

**Discovery Agents (Find New Sources Automatically):**

| Agent | What It Does | Example Use |
|-------|-------------|-------------|
| `web_search_discoverer` | Searches the internet for "best crypto Telegram signal groups 2026", extracts group links, filters out ones you already know. | "Found 5 new Telegram groups. Let me evaluate them automatically by backtesting their last 50 signals." |
| `pine_repo_scraper` | Searches GitHub for high-starred Pine Script repositories, scrapes the scripts, queues them for testing via the Pine tester. | "Found a Pine strategy with 200 stars. It has good results on BTC 4H but fails on altcoins." |
| `reddit_scanner` | Monitors crypto subreddits for coin mentions with sentiment analysis. | "SOL was mentioned 47 times on r/altcoin today with mostly bullish sentiment. This aligns with a @BinanceKillers signal from this morning." |

**Analysis Agents (Cross-Source Intelligence):**

| Agent | What It Does | Example Use |
|-------|-------------|-------------|
| `convergence_detector` | Queries the DB for coins mentioned by 2+ independent sources recently. Multiple independent sources agreeing = stronger conviction. | "SOL was signaled by BinanceKillers, mentioned by CryptoGuru on YouTube, and CPHequities just opened a position. High convergence." |
| `collusion_detector` | Checks if groups always signal the same coins within minutes of each other — possibly the same person running multiple groups, which is suspicious. | "Groups A, B, and C posted the same SOL signal within 3 minutes. Flagging as possible coordinated pump." |
| `pipeline_backtester` | Replays historical signals through a pipeline to evaluate if the pipeline's conditions would have caught good signals and filtered bad ones. | "The 'full_signal_check' pipeline would have caught 15 of 20 winning signals and filtered 8 of 10 losing ones last month. Trying different thresholds..." |
| `strategy_optimizer` | Varys evaluation parameters and backtests each variant to find optimal settings. | "For @BinanceKillers, '12% in 10 days' performs better than '10% in 7 days'. Auto-updating recommended config." |
| `news_monitor` | Monitors crypto news sources and uses LLM to interpret market impact. | "US government announced Bitcoin reserve purchase → LLM says bullish for BTC, possibly for crypto market overall → searching for analyst opinions → found 3 articles predicting 20% BTC rally" |

---

## 4. Configurability — The Core Design Principle

### Why Deep Configuration Matters

You said: *"I don't know the best strategy. If I did, I wouldn't need such a flexible system."* This means:

- Configuration is not just "turn things on/off" — it's **how you experiment with different approaches to deciding what's a good trade**
- Different targets need different evaluation criteria (a scalping group vs. a swing-trading group)
- You'll constantly add new parameters as you think of new things to check
- Adding a new parameter should be trivial — add a field to the config, no code change unless it needs new logic

### Target Configuration Structure

Every target (e.g., one specific Telegram group) has three config sections:

```yaml
# CONNECTION — how to reach this target
connection:
  link: "https://t.me/BinanceKillers"
  fetch_limit: 50

# EVALUATION — how to judge if signals are good
# THIS is where you experiment. Different targets get different strategies.
evaluation:
  strategies:
    - type: peak_gain
      name: "10% in 7 days"
      timeframe_days: 7
      min_gain_pct: 10
      candle_interval: "1h"
    - type: peak_gain
      name: "30% in 30 days"
      timeframe_days: 30
      min_gain_pct: 30
      candle_interval: "4h"
    - type: trailing_sl_sim
      name: "Trailing 5/5/5"
      initial_sl_pct: 5
      trailing_activation_pct: 5
      trailing_distance_pct: 5
      timeframe_days: 7
      candle_interval: "5m"
    - type: tp_vs_sl
      name: "TP1 before SL"
      timeframe_days: 7
      candle_interval: "5m"

  # Which strategy determines the target's trust score
  primary_strategy: "10% in 7 days"
  
  # How many recent signals to use for scoring
  scoring_window: 50
  
  # How old signals can be before they count less
  decay_days: 90

# BEHAVIOR — what to do with results
behavior:
  enabled: true
  notify: true
  notify_conditions:
    min_win_rate: 0.50
    min_evaluated_signals: 10
    scam_check_passed: true
```

### Real Examples of How This Flexibility Helps

**Example 1: Two groups, different strategies**

@BinanceKillers posts swing trade signals (hold for days). You evaluate them on "10% gain in 7 days."
@ScalpKing posts quick scalp signals (hold for hours). You evaluate them on "3% gain in 6 hours."

Same agent (telegram_reader), same pipeline, completely different evaluation — because each target has its own config.

**Example 2: Discovering better parameters over time**

You start evaluating @BinanceKillers on "10% in 7 days" and get a 45% win rate — mediocre. You try "15% in 14 days" and get 62% — much better. The group's signals need more time to play out. You update the config, the system re-evaluates historical signals, the score changes immediately.

Eventually, the `strategy_optimizer` agent automates this: it backtests different parameter combinations and suggests the best one per target.

**Example 3: Adding a new evaluation dimension**

After running the system for a month, you realize: "I should also check if the coin has enough trading volume — low volume coins are risky even if the signal direction is right." You add:

```yaml
  - type: volume_check
    name: "Min 24h volume $1M"
    min_volume_usd: 1_000_000
```

This is a new strategy type, so it requires writing one Python function:

```python
@register_strategy("volume_check")
async def check_volume(signal, price_data, config):
    volume_24h = await get_24h_volume(signal.coin)
    return StrategyResult(
        win=volume_24h >= config["min_volume_usd"],
        details={"volume_24h": volume_24h}
    )
```

Immediately available for any target's config. No other code changes.

---

## 5. Evaluation Strategies

Evaluation strategies are **first-class configurable objects**, not hardcoded logic. Each strategy type is a Python function registered by name. Targets reference them by type in their config and pass parameters.

### Built-in Strategy Types

| Type | Question It Answers | Parameters |
|------|-------------------|------------|
| `peak_gain` | Did price ever reach +X% within Y days after the signal? | `min_gain_pct`, `timeframe_days`, `candle_interval` |
| `close_gain` | Was the close price +X% after exactly Y days? | `min_gain_pct`, `timeframe_days` |
| `trailing_sl_sim` | What P&L does a trailing stop-loss strategy produce? | `initial_sl_pct`, `trailing_activation_pct`, `trailing_distance_pct`, `timeframe_days` |
| `tp_vs_sl` | Did the signal's own TP1 get hit before its SL? | `timeframe_days`, `candle_interval` |
| `multi_tp` | Which TP levels (TP1, TP2, TP3) were reached? | `timeframe_days` |
| `worst_drawdown` | What was the maximum price drop after the signal? (for scam/dump detection) | `timeframe_days`, `max_loss_pct` |
| `risk_reward` | What was the actual R:R ratio achieved? | `timeframe_days` |
| `hold_and_sell` | Buy at signal time, sell after exactly N days. What's the P&L? | `hold_days` |

### Strategy Composition Per Target

A target can use multiple strategies and combine them for scoring:

```yaml
scoring:
  primary_strategy: "10% in 7 days"   # determines the headline win rate
  
  # Optional: require multiple strategies to pass for a signal to count as "WIN"
  must_pass_all: ["tp_vs_sl", "volume_check"]
  
  # Optional: weighted composite score
  composite:
    - strategy: "10% in 7 days"
      weight: 0.5
    - strategy: "trailing 5/5/5"
      weight: 0.3
    - strategy: "volume_check"
      weight: 0.2
```

### Custom Strategies

Register any Python function as a new strategy type:

```python
@register_strategy("consecutive_hold")
async def consecutive_hold(signal, price_data, config):
    """
    Custom: only count as win if the coin held ABOVE entry price
    for at least N consecutive days after reaching TP1.
    """
    consecutive_days = config.get("min_consecutive_days", 3)
    # ... your logic ...
    return StrategyResult(win=held_long_enough, pnl_pct=pnl, details={...})
```

Now you can reference `type: consecutive_hold` in any target's config YAML. The control panel auto-discovers it and shows its parameters in the config form.

---

## 6. Pipelines — Combining Agents

### What a Pipeline Is

A pipeline says: **"When THIS happens, do THESE things in order, and if the results match THESE conditions, take THESE actions."**

Pipelines are YAML files. Creating a new combination of agents = writing a YAML file. No code.

### Pipeline Structure

```yaml
name: "Human readable name"
description: "What this pipeline does and why"

# WHEN does this pipeline run?
trigger:
  type: event | schedule | manual
  event: "new_telegram_signal"           # for event-triggered
  source_filter: ["binance_killers"]     # optional: only for specific targets
  cron: "0 */6 * * *"                    # for scheduled runs

# WHAT does it do? (ordered steps)
steps:
  - agent: agent_name
    input: $trigger.field OR $previous_step.field
    output: step_name              # name this step's output
    config: {extra: params}        # step-specific config overrides
    stop_if_null: true             # if agent returns null, abort pipeline
    optional: true                 # if agent fails, continue anyway

# SHOULD we act on the results? (conditions)
notify:
  agent: telegram_notifier
  conditions:
    all:                           # ALL must be true
      - $exchange.listed == true
      - $scam.is_suspicious == false
    any:                           # at least ONE must be true
      - $target_score.win_rate > 0.5
      - $target_score.total_signals < 10  # too new to judge

  # What to send
  template: |
    {{signal.direction}} {{signal.coin}} @ {{signal.entry}}
    ...
```

### Example Pipelines

#### Pipeline 1: "Full Signal Check" (V1 default)

The bread and butter. A new Telegram signal arrives → parse it → check exchange → check scam → evaluate → score the group → save everything → notify if conditions pass.

```yaml
name: full_signal_check
description: >
  End-to-end validation of a Telegram signal. Parses the message,
  verifies the coin exists on exchanges, checks for pump-and-dump
  patterns, evaluates against the group's configured strategies,
  updates the group's trust score, and notifies if the signal
  passes all quality checks.

trigger:
  type: event
  event: new_telegram_message

steps:
  - agent: llm_parser
    input: $trigger.raw_message
    output: signal
    stop_if_null: true        # not a trading signal — stop

  - agent: exchange_checker
    input: $signal.coin
    output: exchange

  - agent: scam_detector
    input:
      coin: $signal.coin
      signal_time: $signal.timestamp
    output: scam

  - agent: price_checker
    input:
      coin: $signal.coin
      exchange: $exchange.name
      since: $signal.timestamp
    output: price_data
    optional: true            # may fail for very obscure coins

  - agent: signal_evaluator
    input:
      signal: $signal
      price_data: $price_data
      strategies: $trigger.target_config.evaluation.strategies
    output: evaluation
    optional: true

  - agent: target_scorer
    input:
      target_id: $trigger.target_id
      evaluation: $evaluation
    output: target_score

  - agent: db_saver
    input: $*               # save everything from this pipeline run

notify:
  agent: telegram_notifier
  conditions:
    all:
      - $exchange.listed == true
      - $scam.is_suspicious == false
    any:
      - $target_score.win_rate > $trigger.target_config.behavior.notify_conditions.min_win_rate
      - $target_score.total_signals < $trigger.target_config.behavior.notify_conditions.min_evaluated_signals
  template: |
    📊 {{signal.direction}} {{signal.coin}} @ {{signal.entry}}
    Group: {{trigger.target_name}} ({{target_score.grade}})
    Exchange: {{exchange.name}} | Volume: ${{exchange.volume_24h}}
    Scam check: {{scam.verdict}}
    Group win rate: {{target_score.win_rate}}% ({{target_score.total_signals}} signals)
```

#### Pipeline 2: "Signal + Pine Confirmation" (Future)

A Telegram signal is only actionable if a Pine strategy on TradingView also confirms the direction. This is the kind of **cross-source combination** that makes this system powerful.

```yaml
name: signal_with_pine_confirmation
description: >
  Runs the standard signal check, then additionally tests the coin/direction
  against a configured Pine strategy on TradingView. Only notifies if both
  the group's track record AND the Pine strategy agree.
  Only runs when TradingView is available (PC is on with TV open).

trigger:
  type: event
  event: new_telegram_signal

steps:
  - agent: llm_parser
    input: $trigger.raw_message
    output: signal
    stop_if_null: true

  - agent: exchange_checker
    input: $signal.coin
    output: exchange

  - agent: scam_detector
    input: {coin: $signal.coin, signal_time: $signal.timestamp}
    output: scam

  - agent: tradingview_pine_tester
    input:
      coin: $signal.coin
      direction: $signal.direction
    config:
      strategy: "crypto_slaya.pine"
      timeframes: ["4H"]
    output: pine
    optional: true             # skip if TradingView isn't running

  - agent: db_saver
    input: $*

notify:
  agent: telegram_notifier
  conditions:
    all:
      - $exchange.listed == true
      - $scam.is_suspicious == false
      - $pine.confirms_direction == true
      - $pine.win_rate > 0.55
  template: |
    🎯 Pine-Confirmed Signal
    {{signal.direction}} {{signal.coin}} @ {{signal.entry}}
    Pine strategy agrees ({{pine.win_rate}}% WR on {{pine.timeframe}})
    Group: {{trigger.target_name}}
```

#### Pipeline 3: "YouTube Influencer Audit" (Future)

Periodically checks a YouTube channel and evaluates if the coins they mentioned actually went up.

```yaml
name: youtube_influencer_audit
description: >
  Scans a YouTube channel for recent videos, extracts coin mentions,
  checks how those coins performed after the video was posted.
  Builds an influencer credibility score over time.
  Useful to detect exit-liquidity influencers who dump on their audience.

trigger:
  type: schedule
  cron: "0 9 * * *"   # daily at 9 AM

steps:
  - agent: youtube_reader
    input: $trigger.target_config.connection
    output: videos       # [{title, coins_mentioned, transcript_summary, published_at}]

  - agent: price_checker
    input:
      coins: $videos[].coins_mentioned
      since: $videos[].published_at
    output: coin_performance   # [{coin, price_at_video, price_1w_later, pct_change}]

  - agent: influencer_scorer
    input:
      channel: $trigger.target_id
      coin_performance: $coin_performance
    output: credibility    # {accuracy_pct, total_calls, exit_liquidity_pct, verdict}

  - agent: db_saver
    input: $*

notify:
  agent: telegram_notifier
  conditions:
    all:
      - $credibility.total_calls >= 5
      - $credibility.accuracy_pct < 0.30      # alert if influencer is BAD
  template: |
    ⚠️ Influencer Alert: {{trigger.target_name}}
    Accuracy: {{credibility.accuracy_pct}}% ({{credibility.total_calls}} calls)
    Exit liquidity suspected: {{credibility.exit_liquidity_pct}}% of coins dumped post-video
    Verdict: {{credibility.verdict}}
```

#### Pipeline 4: "Auto-Discover Telegram Groups" (Future)

The holy grail — the system finds new signal groups on the internet, evaluates them by backtesting their recent signals, and adds the good ones automatically.

```yaml
name: discover_telegram_groups
description: >
  Searches the internet for crypto Telegram signal groups, evaluates
  each by backtesting their recent signals, and adds promising groups
  to the monitoring list. Detects and rejects scam/pump-and-dump groups.

trigger:
  type: schedule
  cron: "0 9 * * 1"   # every Monday at 9 AM

steps:
  - agent: web_search_discoverer
    input:
      queries:
        - "best crypto Telegram signal groups 2026 free"
        - "reliable crypto signals Telegram"
        - "crypto futures signals Telegram group"
    output: candidate_links

  - agent: filter_known
    input: $candidate_links
    output: new_groups        # only groups not already in DB

  - agent: for_each
    input: $new_groups
    steps:
      - agent: telegram_reader
        input: {group: $item, limit: 50}
        output: messages

      - agent: llm_parser
        input: $messages
        output: signals       # parse all 50 messages, keep the ones that are signals

      - agent: batch_evaluator
        input: $signals
        config:
          strategy: {type: peak_gain, timeframe_days: 7, min_gain_pct: 10}
        output: results

      - agent: calculate_score
        input: $results
        output: score

  - agent: filter
    input: $new_groups
    condition: $item.score.win_rate > 0.40 AND $item.score.total_signals > 5
    output: promising

notify:
  agent: telegram_notifier
  conditions:
    all:
      - $promising.length > 0
  template: |
    🔍 Discovered {{promising.length}} new groups
    {% for g in promising %}
    • {{g.name}} — {{g.score.win_rate}}% WR ({{g.score.total_signals}} signals)
    {% endfor %}
    Added to monitoring with default config.
```

#### Pipeline 5: "Cross-Source Conviction" (Future)

Finds coins that multiple independent sources agree on. If BinanceKillers signals LONG SOL, AND CryptoGuru mentioned SOL in a video, AND CPHequities just opened a SOL position — that's convergence.

```yaml
name: cross_source_conviction
description: >
  Periodically checks if any coin was mentioned by 2+ independent sources
  recently. Multiple independent sources agreeing on the same coin is a
  stronger signal than any single source alone.
  Also detects collusion (same person running multiple groups).

trigger:
  type: schedule
  cron: "0 */4 * * *"   # every 4 hours

steps:
  - agent: convergence_detector
    input:
      lookback_hours: 48
      min_sources: 2
    output: convergent_coins    # [{coin, sources, signals, first_seen, last_seen}]

  - agent: collusion_detector
    input: $convergent_coins
    output: collusion_check     # flags if sources posted within minutes of each other

  - agent: cmc_checker
    input: $convergent_coins[].coin
    output: sentiment
    optional: true

  - agent: db_saver
    input: $*

notify:
  agent: telegram_notifier
  conditions:
    all:
      - $convergent_coins.length > 0
      - $collusion_check.is_suspicious == false
  template: |
    🔥 Multi-Source Convergence
    {% for c in convergent_coins %}
    {{c.coin}} — {{c.sources.length}} sources agree
      Sources: {{c.sources | join(", ")}}
      CMC sentiment: {{c.sentiment.bullish_pct}}% bullish
    {% endfor %}
```

---

## 7. Memory and Research State

### The Problem with Previous Projects

Your old Telegram script fetched the last 10 messages, processed them, and threw away the context. There was no memory. No way to say "I already analyzed BTC/USDT today" or "this coin was also mentioned by another group yesterday."

### The Design Principle: Remember Everything, Query Smartly

Every signal, every evaluation, every pipeline run, every piece of data fetched — stored in Supabase. Forever. Signals are tiny (a few KB each). 10,000 signals = a few MB. The free Supabase tier has 500MB — that's hundreds of thousands of signals.

But **remembering everything** only matters if you can **query it usefully**. The system should support:

### Use Case 1: Coin Research State

"What do I know about SOL right now?"

The system can answer: SOL was signaled by @BinanceKillers 2 hours ago (LONG at $178), also mentioned by CryptoGuru on YouTube yesterday (bullish), CPHequities has a position since last week. Last CMC check: 82% bullish, 15K votes. Exchange: Binance, 24h volume $1.2B. Last Pine test (CryptoSlaya on 4H): 65% WR over last 30 days.

This is a **query against the database** joining signals, evaluations, and coin data. Your coding assistant can run this query via the Supabase MCP and present it to you.

### Use Case 2: Cross-Reference Detection

"Did any other group also signal this coin recently?"

When a new SOL signal arrives from @BinanceKillers, the system checks the DB: "any other signals for SOL in the last 48 hours?" If @VIPSignals also said LONG SOL yesterday — that's convergence. Stronger conviction. But if they posted within 3 minutes of each other with identical text — that's collusion. Same person, multiple groups. Suspicious.

### Use Case 3: Temporal Patterns

"Group X's signals work on weekdays but fail on weekends."
"Low-cap coin signals from Group Y are always scams, but their BTC/ETH calls are solid."

These patterns emerge from stored evaluation data. Over time, you can slice and analyze: by group, by coin type, by time of day, by market conditions. The data is there — you just query it. The `strategy_optimizer` agent eventually automates this.

### Use Case 4: Ad-Hoc Investigation

You see an article about the US government buying Bitcoin. You tell your coding assistant: "Take all BTC signals from the DB in the last month and check their performance. Also search for analyst opinions about government crypto policy. Compare."

The assistant queries Supabase (via MCP) for BTC signals, runs a web search, and gives you a synthesis. The system doesn't need a "news agent" built in for this — you use it as a knowledge base that your AI assistant queries on demand.

### Use Case 5: Resumed State

You close your PC at night. When you restart, each agent checks its cursor in the DB: "Last message I processed from @BinanceKillers was ID 45782." It picks up from there. No missed signals, no duplicates.

### Coin Cache

If a signal about BTC/USDT arrives and you already fetched BTC exchange data 2 hours ago, don't fetch again. The `coins` table acts as a cache with a configurable TTL per data type (exchange data is fresh for 24h, CMC sentiment for 6h, price data for 1h).

---

## 8. Pipeline Backtesting and Self-Improvement

### The Idea

The system runs 24/7 for free. Why not use idle time to test if your pipeline configurations are actually optimal?

### How Pipeline Backtesting Works

1. Take all historical signals from the DB for a target
2. Replay each signal through a pipeline as if it just arrived
3. For each signal, record: "Would the pipeline have notified me?"
4. Compare against actual outcome: "Did the signal make money?"
5. Calculate metrics:
   - **Precision**: of the signals the pipeline WOULD have sent me, what % were actually profitable?
   - **Recall**: of the signals that WERE profitable, what % did the pipeline catch?
   - **False positive rate**: how many bad signals would it have sent?

### How Self-Improvement Works

The `strategy_optimizer` agent varies pipeline parameters:

```
Try: min_win_rate = 0.40 → Precision: 55%, Recall: 90%
Try: min_win_rate = 0.50 → Precision: 68%, Recall: 72%
Try: min_win_rate = 0.60 → Precision: 78%, Recall: 45%
```

It finds the sweet spot and suggests: "For @BinanceKillers, setting min_win_rate to 0.52 gives the best balance of precision (65%) and recall (75%). Current setting is 0.50. Recommend updating."

You can auto-apply these suggestions or review them first (configurable).

### What Can and Can't Be Backtested

**Pine strategies CAN be backtested retroactively** — and they should be. Pine strategies run on price history (OHLCV candles), which is always available from exchanges for any point in the past. If a Telegram signal from 3 months ago said "LONG SOL at $178" and you want to know "would the CryptoSlaya Pine strategy have confirmed that direction on the 4H chart at that time?" — you can absolutely test that now, because you have all the historical candles.

**Real-time snapshot data CANNOT be backtested** unless it was cached at the time. CMC sentiment votes, order book depth, social media buzz — these are ephemeral. If you didn't save them when the signal arrived, they're gone.

**Design implication**: the `db_saver` agent should save as much context as possible at pipeline run time (CMC data, exchange data, etc.) so that future backtesting has the full picture for the data that IS ephemeral.

### Backtesting Improves Both Agents AND Pipelines

The whole point of backtesting is not just "was the pipeline accurate?" — it's **"what should change?"**

- **Improving an agent**: if Pine rejected 5 signals that turned out to be highly profitable, maybe Pine's parameters (timeframe, indicator settings) need adjusting. The backtester surfaces this: "Pine's 4H CryptoSlaya rejected 5 winning signals from @BinanceKillers with avg +22% gain. Consider re-tuning or switching to 1D timeframe."

- **Improving a pipeline**: if signals from @BinanceKillers consistently win WITHOUT Pine confirmation, maybe this group's signals shouldn't go through Pine at all. The backtester can compare pipeline variants: "Pipeline A (with Pine step) caught 8 of 15 winners. Pipeline B (without Pine step) caught 13 of 15 winners but also let in 4 losers. Pipeline B has better net expected value for this group."

- **Improving per-target config**: maybe "10% in 7 days" is the wrong evaluation strategy for a group that signals slower plays. Backtest with "15% in 14 days" and compare.

The backtester doesn't just report metrics — it suggests **specific changes** to agents, pipelines, and target configs.

---

## 9. The Brain — LLM Roles

The LLM isn't just a parser. It plays three distinct roles in the system, each with different requirements:

### Role 1: Signal Parser (Structured Extraction)

The simplest role. Parse a raw message into structured data. No reasoning needed — just pattern matching with a schema.

**Input**: raw Telegram message text
```
⚡️⚡️ #BTC/USDT ⚡️⚡️
Signal Type: Regular (Long)
Leverage: Cross (50.0X)
Entry Targets: 64500.0
Take-Profit Targets:
1) 65000.0
2) 65500.0
3) 66000.0
Stop Targets: 62000.0
```

**Output**: structured JSON
```json
{
  "type": "signal",
  "coin": "BTC/USDT",
  "direction": "LONG",
  "entry": [64500.0],
  "take_profits": [65000.0, 65500.0, 66000.0],
  "stop_loss": 62000.0,
  "leverage": 50,
  "confidence": 0.95
}
```

For non-signal messages:
```json
{
  "type": "info",
  "summary": "User discussing BTC price action",
  "coins_mentioned": ["BTC"],
  "sentiment": "bullish"
}
```

Even small/free models handle this well. Provider chain: Gemini Flash free → Groq free (Llama 3.3 70B) → regex fallback for obvious formats.

### Role 2: Conversational Trading Assistant (Telegram Chat)

The Telegram bot isn't just a one-way notification channel — it's a **two-way chat interface** to the LLM brain. You talk to it like a colleague. It has access to all the system's tools and data.

**How it works**: you send a Telegram message → the LLM receives it with conversation history + available tools → it reasons about what to do → calls tools (query DB, run backtest, test Pine, check exchange) → responds with results and insights → you follow up → it digs deeper.

**Example conversation:**
```
You:   "How did BinanceKillers do last week?"
Bot:   Queries DB → "12 signals. 7 wins (58%). Best: SOL +18%.
       3 scam flags. Want me to dig into the scam flags?"

You:   "Yes, and test CryptoSlaya on the winners"
Bot:   Runs pine_tester on 7 coins →
       "Pine confirmed 5 of 7. The 2 it missed were low-cap alts
       where Pine doesn't have enough history. Should I try a
       different timeframe for those?"

You:   "Try 1D instead of 4H"
Bot:   Runs tests → "1D confirms 1 of 2. The other (PEPE/USDT)
       has too little data on any timeframe."

You:   "What coins are most mentioned across all sources this week?"
Bot:   Runs convergence query → "SOL (3 sources), BTC (2), AVAX (2).
       SOL has the strongest convergence — BinanceKillers, VIPSignals,
       and a new group I'm still evaluating."
```

The LLM decides which tools to call based on your question. Same tools as the pipeline agents — `query_signals`, `run_backtest`, `test_pine`, `check_exchange` — but invoked through natural conversation instead of a fixed YAML sequence.

**Conversation history is saved** in Supabase so the assistant remembers context across sessions. "Last time we discussed PEPE, you said you don't trust low-cap signals from group X."

### Role 3: Research Brain (Autonomous Experiment Design)

This is the most advanced role. When you give the system a research goal — "optimize the Pine strategy for BinanceKillers signals" — the LLM doesn't just grid-search parameters. It **reasons about results and designs smarter experiments**, like a junior developer learning to be senior.

**Example: Pine strategy optimization**
```
LLM runs: CryptoSlaya on BTC daily → 68% WR ✅
LLM runs: CryptoSlaya on BTC 1H   → 41% WR ❌

LLM reasons: "Works on daily but not hourly. The moving averages
(50/200) are designed for longer timeframes. Let me try 4H as a
middle ground, and also try adjusting MAs to 20/50 on hourly."

LLM runs: CryptoSlaya on BTC 4H        → 61% WR ✅
LLM runs: CryptoSlaya (MA 20/50) on 1H → 55% WR ⚠️

LLM reasons: "4H works well with default params. Hourly improved
with shorter MAs but still weaker. Let me check if this pattern
holds for altcoins or just BTC..."

LLM runs: CryptoSlaya on SOL 4H  → 58% WR ✅
LLM runs: CryptoSlaya on SOL 1D  → 44% WR ❌

LLM reasons: "SOL works on 4H but not daily — opposite of BTC.
This suggests the strategy needs different timeframes per coin
volatility class. Recommendation: BTC on 1D, altcoins on 4H."
```

A grid search can't do this. The LLM observes patterns, forms hypotheses, and designs targeted experiments. There's a budget cap (max N iterations) so it doesn't run forever.

**Implementation**: a reasoning loop, not a framework.

```python
for i in range(budget):
    # Show the LLM all previous results
    # Ask: "What should we test next and why? Or DONE?"
    response = llm.reason(context=all_results_so_far, tools=available_tools)
    if response.action == "DONE":
        break
    result = execute(response.action)
    results.append(result)
    reasoning_log.append(response.reasoning)
```

~80 lines of Python. No framework needed. The LLM IS the brain.

### Progressive Autonomy — The Developer Analogy

The system learns like onboarding a junior developer. You don't dump everything on day 1. You give them tasks, they get stuck, you teach them, they apply what they learned.

**Month 1 — Junior dev, asks a lot:**
```
Bot:  "BinanceKillers had 3 scam signals this week. Should I
       lower their trust score or remove them?"
You:  "Lower the score, never auto-remove. I want to see if
       they recover."
```
→ System saves: *preference: never auto-remove targets. On scam spike: lower score, keep monitoring.*

**Month 3 — Mid-level, asks less:**
```
Bot:  "BinanceKillers had 3 scam signals again. Lowered trust to C.
       Also noticed their weekend signals are 80% scams vs 15% on
       weekdays. Want me to only evaluate weekday signals?"
You:  "Smart. Yes."
```
→ System learned the pattern AND proposed a solution. Only asked for confirmation.

**Month 6 — Senior dev, just reports:**
```
Bot:  "Weekly report: Disabled weekend signals for BinanceKillers
       (scam rate 85%). Optimized CryptoSlaya params for altcoins —
       4H with MA 20/50 gives +8% expected value. Applied.
       Discovery found 2 new groups, evaluating for 2 weeks before
       enabling notifications."
```
→ System made decisions itself because it's seen you make them before.

**How this works technically:**

1. **Preference memory**: Every correction, every "yes/no/do it differently" is stored in a `preferences` table indexed by situation type. Before making a decision, the system checks: "Have I seen this situation? What did the user say?"

2. **Confidence threshold**: Each decision has a confidence score. High confidence (seen this exact pattern before, user always said the same thing) → act autonomously. Low confidence (new situation, ambiguous) → ask. Over time, more decisions cross the threshold.

3. **Decision log**: Everything it does autonomously is logged with reasoning. You can audit: "Why did you do this?" → "Because on March 15th you told me to handle it this way."

4. **Research playbook**: The system learns not just preferences but **methodology**. You teach it "always check other timeframes" → it internalizes this as a research step. You teach it "segment by market cap" → it starts doing it automatically. Each lesson becomes part of its evaluation workflow.

5. **Alignment through chat, not config editing**: Instead of you editing YAML, you tell it "BinanceKillers signals need more time to play out" and it translates that into the right config changes.

### The Three Operating Modes

| Mode | How It Works | LLM Role |
|------|-------------|----------|
| **Automated** (pipelines) | Runs 24/7. Fixed YAML sequences. Sends alerts. | Signal parser only |
| **Conversational** (Telegram chat) | You ask questions or give goals. Think together. | Conversational assistant with tools |
| **Autonomous research** (optimizer) | You say "optimize X." System runs experiments, updates you, asks when uncertain. | Research brain with reasoning loop |

All three modes share the same tools and the same database.

### LLM Provider Chain

```
Signal parsing:    Gemini Flash free → Groq free → regex fallback
Conversation:      Gemini Pro free → Groq Llama 3.3 70B → Gemini Flash
Research brain:    Gemini Pro free → Groq Llama 3.3 70B
```

All free. Different roles benefit from different model quality — parsing is easy (Flash), reasoning benefits from better models (Pro).

---

## 10. Database Design (Supabase)

### Why Supabase Over SQLite

- Accessible from anywhere (your PC, GitHub Actions, phone, your coding assistant via Supabase MCP)
- Free tier: 500MB database, more than enough
- No file to manage or backup
- SQL + REST API + real-time subscriptions (useful later for live dashboards)
- Your coding assistant can query it directly via the Supabase MCP — "show me all SOL signals from the last week"

### Core Tables

**`signals`** — every signal ever detected
```sql
id               SERIAL PRIMARY KEY
agent_type       TEXT         -- "telegram_reader"
target_id        TEXT         -- "binance_killers"
target_name      TEXT         -- "Binance Killers"
coin             TEXT         -- "SOL/USDT"
direction        TEXT         -- "LONG" | "SHORT" | null
entry_price      NUMERIC
take_profits     JSONB        -- [185, 190, 200]
stop_loss        NUMERIC
leverage         NUMERIC
raw_message      TEXT         -- original message for debugging
message_type     TEXT         -- "signal" | "info" | "sentiment" | "other"
signal_time      TIMESTAMPTZ  -- when the signal was posted
created_at       TIMESTAMPTZ  -- when we stored it
```

**`evaluations`** — evaluation results per signal per strategy
```sql
id               SERIAL PRIMARY KEY
signal_id        INT REFERENCES signals(id)
strategy_type    TEXT         -- "peak_gain"
strategy_name    TEXT         -- "10% in 7 days"
strategy_config  JSONB        -- {timeframe_days: 7, min_gain_pct: 10}
result           TEXT         -- "win" | "loss" | "open" | "skipped"
pnl_pct          NUMERIC      -- +12.5 or -4.2
details          JSONB        -- {peak_price: 201.3, peak_time: "...", ...}
evaluated_at     TIMESTAMPTZ
```

**`target_scores`** — running trust scores per target
```sql
id               SERIAL PRIMARY KEY
agent_type       TEXT
target_id        TEXT
target_name      TEXT
total_signals    INT
wins             INT
losses           INT
win_rate         NUMERIC
avg_return_pct   NUMERIC
grade            TEXT         -- "A+", "B-", "D", etc.
last_updated     TIMESTAMPTZ
```

**`pipeline_runs`** — log of every pipeline execution
```sql
id               SERIAL PRIMARY KEY
pipeline_name    TEXT
trigger_type     TEXT         -- "event" | "schedule" | "manual"
trigger_data     JSONB        -- what started this run
steps_results    JSONB        -- output of each step
notified         BOOLEAN
duration_ms      INT
status           TEXT         -- "success" | "failed" | "skipped"
created_at       TIMESTAMPTZ
```

**`coins`** — coin cache / knowledge base
```sql
symbol           TEXT PRIMARY KEY   -- "SOL/USDT"
name             TEXT               -- "Solana"
exchanges        JSONB              -- ["binance", "kucoin", "mexc"]
cmc_data         JSONB              -- {bullish_pct: 82, total_votes: 15000, ...}
last_exchange_check  TIMESTAMPTZ
last_cmc_check       TIMESTAMPTZ
notes            TEXT               -- your manual notes
```

**`agent_cursors`** — resume state per agent/target
```sql
agent_type       TEXT
target_id        TEXT
last_item_id     TEXT         -- last Telegram message ID, last YouTube video ID, etc.
last_check_time  TIMESTAMPTZ
metadata         JSONB        -- agent-specific state
PRIMARY KEY (agent_type, target_id)
```

**`agent_configs`** — target configurations (also editable via control panel)
```sql
id               SERIAL PRIMARY KEY
agent_type       TEXT
target_id        TEXT UNIQUE
target_name      TEXT
config           JSONB        -- the full target config YAML, stored as JSON
enabled          BOOLEAN
created_at       TIMESTAMPTZ
updated_at       TIMESTAMPTZ
```

**`preferences`** — learned decision patterns from user feedback
```sql
id               SERIAL PRIMARY KEY
situation_type   TEXT         -- "scam_spike", "low_win_rate", "new_group_found"
situation_hash   TEXT         -- hash of the situation context for dedup
user_instruction TEXT         -- what the user said to do
example_context  JSONB        -- the specific situation that triggered this preference
confidence       NUMERIC      -- how confident the system is in applying this autonomously
times_applied    INT DEFAULT 0
created_at       TIMESTAMPTZ
last_applied     TIMESTAMPTZ
```

**`chat_history`** — conversation memory for the Telegram chat interface
```sql
id               SERIAL PRIMARY KEY
chat_id          TEXT         -- Telegram chat ID
role             TEXT         -- "user" | "assistant"
content          TEXT         -- message text
tools_called     JSONB        -- which tools the assistant invoked
created_at       TIMESTAMPTZ
```

**`research_sessions`** — autonomous research/optimization runs
```sql
id               SERIAL PRIMARY KEY
goal             TEXT         -- "optimize Pine for BinanceKillers"
iterations       JSONB        -- [{action, result, reasoning}, ...]
final_summary    TEXT
suggestions      JSONB
status           TEXT         -- "running" | "completed" | "paused"
created_at       TIMESTAMPTZ
completed_at     TIMESTAMPTZ
```

JSON/JSONB columns are used liberally for flexibility — adding a new config field or a new strategy detail means adding a JSON key, not a schema migration.

---

## 11. Control Panel

### Architecture

**Python FastAPI** serves a REST API. **HTML/CSS/JS** frontend (no framework — just files) talks to the API via fetch. Styled with a dark-mode design. AI writes the JS, you read the Python.

The API is the source of truth. Everything you can do in the web UI, you can also do via:
- API calls (for your coding assistant)
- Supabase MCP (for direct DB queries)

### Pages

**Dashboard**
- System status: is the scheduler running? is Telegram connected? last heartbeat
- Quick stats: signals today, alerts sent, active targets
- Recent activity feed: "12:45 — Parsed LONG SOL from BinanceKillers → passed scam check → notified"

**Agents & Targets**
- List agents grouped by type
- Under each agent, list its targets — each target shows: name, status, trust grade, win rate, last checked
- Click a target → expand to see/edit its full config:
  - Connection settings
  - Evaluation strategies (add/remove strategies, change parameters)
  - Behavior settings (notifications, thresholds)
  - Signal history for this target
  - Score breakdown (per-strategy results)
- "Add Target" button per agent — type-specific form
- Each agent type shows different config fields because their configs are different

**Pipelines**
- List all pipeline YAML files with name, trigger type, status (enabled/disabled)
- Click → view the YAML (editable with a code editor widget)
- "Run Now" button — manually trigger any pipeline with test input
- Run history: list of recent runs with status, duration, whether it notified
- Click a run → see step-by-step: each agent's input → output → timing

**Signals / Research**
- Searchable table of all signals
- Filters: coin, source, agent, date range, direction, evaluation result
- Click a signal → see everything: raw message, parsed data, evaluation results per strategy, pipeline run that processed it, whether you were notified
- Coin view: click a coin → see all signals for that coin across ALL sources, all evaluations, cached data

**Settings**
- LLM provider config: priority order, API keys, test connection
- Telegram config: bot token, chat ID, test notification
- Scheduler: timezone, global pause, view active jobs
- Data: export DB, check Supabase storage usage

---

## 12. Tech Stack

| Component | Choice | Why |
|-----------|--------|-----|
| **Backend language** | Python 3.11+ | You know it. Best ecosystem for crypto (ccxt, telethon). All trading logic in a language you can read and debug. |
| **API framework** | FastAPI | Async, fast, auto-docs, serves static files. |
| **Frontend** | HTML/CSS/JS (no framework) | AI writes it. Looks good, no build step. Easy to improve iteratively. |
| **Database** | Supabase (PostgreSQL) | Free, hosted, accessible from anywhere, queryable by coding assistant via MCP. 500MB free tier. |
| **Scheduler** | APScheduler | In-process, cron syntax, persistent job store. No external service. |
| **LLM** | Gemini Flash free → Groq free → regex fallback | All free. Structured output. |
| **Telegram reading** | Telethon | User account access to group messages. Free. Resumes from cursor. |
| **Telegram sending** | python-telegram-bot | Bot API for notifications. Free. |
| **Exchange data** | ccxt | All major exchanges. Free public API. Already used in your POCs. |
| **Web scraping** | httpx + Firecrawl MCP | httpx for simple requests. Firecrawl for JS-heavy sites (CMC, eToro). |
| **YouTube** | yt-dlp + youtube-transcript-api | Free transcript extraction. |
| **TradingView** | TradingView MCP (existing) | 78 tools via CDP. Only works when TV Desktop is open. System detects availability and skips if offline. |
| **Deployment** | Your PC, 24/7 | `python run.py` starts everything. Resumes from cursors on restart. ~20GB disk is fine — data lives in Supabase. |

---

## 13. What Gets Built When

### V1 — The Foundation That Works (Build Now)

**Core engine**: pipeline runner, agent base class, agent registry, config loader, scheduler, Supabase connection.

**Two working flows end-to-end**:
- Telegram signal → LLM parse → exchange check → scam check → evaluate → score → save → notify
- Telegram signal → LLM parse → Pine confirmation → save → notify (when TradingView is available)

**Pipeline backtesting**: replay historical signals through pipelines, measure precision/recall, LLM-driven experiment design for strategy optimization.

**Control panel**: basic web UI with all 5 pages — functional, not beautiful yet.

**Result**: you can add Telegram groups, configure their evaluation strategies, get Pine-confirmed signals when TV is available, and get notifications for signals that pass your criteria. The system backtests itself and suggests improvements. Everything is stored in Supabase.

### V2 — The Brain (Build Next)

**Conversational Telegram interface**: chat with your system via Telegram. Ask questions, give goals, think together. The LLM has access to all tools and data.

**Progressive autonomy**: preference memory, confidence-based escalation, decision logging. The system learns your methodology and starts handling routine decisions alone.

**Research brain**: LLM-driven experiment design loop. Observes results, reasons about patterns, designs smarter tests. You teach it your research methodology and it internalizes it.

### V3 — More Sources (Build Later)

YouTube reader + influencer scorer. CMC sentiment enricher. eToro copy trader source.

### V4 — Intelligence & Autonomy (Build Eventually)

Cross-source convergence detection. Collusion detection. Discovery agents that find new groups/channels. News monitoring. Web search integration. Wallet tracking. Self-improving pipelines.

**The key**: V1's architecture is designed so V2/V3/V4 are achieved by adding new agent files and pipeline YAMLs — not rewriting the core. The conversational brain (V2) uses the exact same tools as the automated pipelines (V1), just invoked through natural language instead of YAML.
