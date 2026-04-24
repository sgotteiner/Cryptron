# Cryptron — Implementation Plan

Based on [system_design.md](file:///c:/my_projects/TradingSetup/docs/system_design.md).

---

## Design Principle

**The brain is the product. The agents are its hands.**

V1 delivers the complete backbone so that everything after is improvement work — adding agents, creating pipelines, teaching the brain via chat. No infrastructure rewrites, just plug things in.

---

## Prerequisites

> [!IMPORTANT]
> **1. Supabase project**: Create a free project at [supabase.com](https://supabase.com). I need the **URL** and **Service Role Key** for `.env`.

> [!IMPORTANT]
> **2. Telegram credentials** (two things):
> - **Telethon** (reading groups): `api_id` + `api_hash` from [my.telegram.org](https://my.telegram.org)
> - **Bot API** (chat + notifications): bot token from [@BotFather](https://t.me/BotFather). Start a chat with your bot so I can get your `chat_id`.

> [!IMPORTANT]
> **3. LLM API keys** (free):
> - **Gemini**: [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
> - **Groq**: [console.groq.com](https://console.groq.com)

> [!IMPORTANT]
> **4. First test target**: Which Telegram group to use for the first pipeline test?

---

## Project Structure

```
c:\my_projects\TradingSetup\
├── docs/
│   ├── system_design.md
│   └── implementation_plan.md
│
├── core/                          # The backbone
│   ├── __init__.py
│   ├── base_agent.py              # BaseAgent + auto-discovery registry
│   ├── pipeline.py                # PipelineRunner (YAML → execute agents)
│   ├── context.py                 # PipelineContext (carries data between steps)
│   ├── db.py                      # Supabase client wrapper
│   ├── llm.py                     # LLM router (Gemini → Groq → fallback)
│   ├── brain.py                   # The conversational brain (tool-calling loop)
│   ├── preferences.py             # Preference memory (learn from user feedback)
│   ├── research.py                # Research loop (autonomous experiment design)
│   ├── strategies.py              # Strategy registry + built-in eval strategies
│   ├── config.py                  # Loads .env and settings
│   └── scheduler.py               # APScheduler integration
│
├── agents/                        # Tools the brain can use (auto-discovered)
│   ├── __init__.py
│   ├── telegram_reader.py         # Source: read Telegram groups
│   ├── llm_parser.py              # Enricher: raw text → structured signal
│   ├── pine_tester.py             # Strategy: test Pine scripts via TradingView MCP
│   ├── signal_evaluator.py        # Strategy: run configured eval strategies
│   ├── target_scorer.py           # Strategy: maintain win rate per target
│   ├── db_saver.py                # Action: save to Supabase
│   └── telegram_notifier.py       # Action: send alert via Telegram bot
│
├── pipelines/                     # YAML pipeline definitions
│   └── full_signal_check.yaml
│
├── targets/                       # Per-target YAML configs
│   └── example_group.yaml
│
├── static/                        # Dashboard frontend
│   ├── index.html
│   ├── app.js
│   └── style.css
│
├── main.py                        # Entry point: FastAPI + scheduler + Telegram
├── requirements.txt
├── .env.example
├── .env                           # (gitignored)
└── .gitignore
```

---

## Phase 1: Core Engine

The pipeline runner, agent registry, DB, LLM router, and config. The skeleton that everything plugs into.

### [NEW] `core/config.py`
Loads `.env` via `python-dotenv`. Exposes settings: Supabase URL/key, Telegram creds, LLM keys, scheduler timezone. Simple `os.getenv()` with defaults.

### [NEW] `core/db.py`
Supabase client wrapper with typed helpers for all tables: `save_signal()`, `save_evaluation()`, `get_cursor()`, `set_cursor()`, `get_target_config()`, `save_preference()`, `get_preferences()`, `save_chat_message()`, `get_chat_history()`, `save_research_session()`, etc.

### [NEW] `core/base_agent.py`
```python
class BaseAgent:
    name: str
    agent_type: str  # "source" | "enricher" | "strategy" | "action"
    description: str
    
    async def run(self, ctx: PipelineContext, input_data: Any) -> Any:
        raise NotImplementedError
```
Plus auto-discovery registry: scans `agents/` for BaseAgent subclasses, maps by name. `get_agent("pine_tester")` returns the instance.

### [NEW] `core/context.py`
`PipelineContext` — carried through pipeline runs:
- `outputs: dict` — named outputs from previous steps
- `trigger_data`, `target_config` — run metadata
- `db`, `llm` — shared clients
- `get(path)` — resolves `$signal.coin` references from YAML

### [NEW] `core/pipeline.py`
`PipelineRunner`:
1. Load YAML → list of steps
2. For each step/block:
   - If single agent: resolve inputs → call `agent.run()` → store output
   - If `parallel` block: resolve inputs → `asyncio.gather()` all agents → store outputs
3. Handle `stop_if_null`, `optional` flags
4. Evaluate notify conditions → call notify agent if passed
5. **`dry_run` mode**: same logic, skips action agents. For backtesting.

~150 lines. No framework.

### [NEW] `core/llm.py`
LLM router with two modes:
- **`extract_structured(text, schema)`** — for signal parsing (Flash is fine)
- **`chat_with_tools(messages, tools)`** — for the brain (Pro preferred)
- **`reason(context, tools)`** — for research loops (Pro preferred)

Provider chain: Gemini → Groq → regex fallback (parsing only).
Uses native function/tool calling APIs (both Gemini and Groq support it).

### [NEW] `core/strategies.py`
Strategy registry with `@register_strategy` decorator. Built-in: `peak_gain`, `trailing_sl_sim`, `tp_vs_sl`, `hold_and_sell`. Adding a new strategy = one decorated function.

### [NEW] `core/scheduler.py`
APScheduler wrapper. Registers pipeline runs as cron jobs. Provides pause/resume/list.

### Supabase Tables (migration SQL)
All tables from the system design: `signals`, `evaluations`, `target_scores`, `pipeline_runs`, `coins`, `agent_cursors`, `agent_configs`, `preferences`, `chat_history`, `research_sessions`, `backtest_runs`.

### Verification
- Agent registry discovers a test agent
- Pipeline runs a 3-step mock YAML
- LLM router falls back correctly
- DB reads/writes to Supabase
- Strategy function runs on sample data

---

## Phase 2: The Brain

The conversational Telegram interface, preference memory, and reasoning loop. **This is the core product.**

### [NEW] `core/brain.py`
The conversational engine. Receives a user message, thinks, uses tools, responds.

```python
class Brain:
    async def handle_message(self, chat_id: str, message: str) -> str:
        # Load conversation history
        history = await self.db.get_chat_history(chat_id, limit=20)
        
        # Load relevant preferences
        preferences = await self.preferences.get_relevant(message)
        
        # Build system prompt with available tools + preferences
        system = self.build_system_prompt(preferences)
        
        # LLM tool-calling loop
        response = await self.llm.chat_with_tools(
            system=system,
            messages=history + [{"role": "user", "content": message}],
            tools=self.get_available_tools()
        )
        
        # Save conversation
        await self.db.save_chat_message(chat_id, message, response)
        
        return response.text
    
    def get_available_tools(self):
        """All registered agents, exposed as callable tools."""
        return [agent.as_tool() for agent in agent_registry.values()]
```

The brain can call any registered agent as a tool. Same agents as the pipeline — but invoked through conversation instead of YAML.

### [NEW] `core/preferences.py`
Preference memory system:
- `save_preference(situation_type, user_instruction, context)` — stores a learned pattern
- `get_relevant(situation_description)` — finds applicable preferences for the current situation
- Preferences are injected into the brain's system prompt so it remembers past guidance
- Confidence tracking: how many times was this preference applied? Did the user ever correct it?

### [NEW] `core/research.py`
The autonomous experiment loop:
```python
class ResearchSession:
    async def run(self, goal: str, budget: int = 15):
        results = []
        reasoning = []
        
        for i in range(budget):
            response = await self.llm.reason(
                context=f"Goal: {goal}\nResults so far:\n{format(results)}",
                tools=[run_backtest, test_pine, query_signals, compare_variants]
            )
            if response.action == "DONE":
                break
            result = await self.execute(response.action)
            results.append(result)
            reasoning.append(response.reasoning)
            
            # Optional: update user on progress via Telegram
            if i % 5 == 4:
                await self.notify_progress(results, reasoning)
        
        summary = await self.summarize(results, reasoning)
        await self.db.save_research_session(goal, results, summary)
        return summary
```

Can be triggered via:
- Telegram chat: "Optimize Pine for BinanceKillers signals"
- Scheduled pipeline: weekly backtest + optimize
- Dashboard UI: "Run Research" button

### [MODIFY] Telegram bot setup in `main.py`
The bot handles BOTH:
- **Incoming messages** → routed to `Brain.handle_message()`
- **Outgoing notifications** → called by `telegram_notifier` agent

### Verification
- Send a message to the bot → get a response that used a tool (e.g., "How many signals today?" → queries DB → answers)
- Tell the bot a preference → verify it's stored and applied next time
- Start a research session via chat → verify it runs experiments and reports back
- Verify conversation history persists across sessions

---

## Phase 3: Starter Agents

Two agents to give the brain actual hands. One source (Telegram), one strategy (Pine). Enough to test multi-step pipelines.

### [NEW] `agents/telegram_reader.py` (source)
- Telethon-based group reader
- Fetches messages since last cursor from `agent_cursors`
- Returns `[{raw_text, message_id, timestamp, sender}]`
- Updates cursor after processing

### [NEW] `agents/llm_parser.py` (enricher)
- Takes raw text → calls `LLMRouter.extract_structured()` → returns signal dict or `None`

### [NEW] `agents/pine_tester.py` (strategy)
- Checks if TradingView MCP is reachable
- If yes: sets ticker, applies Pine script, reads strategy results
- If no: returns `None` (pipeline skips gracefully)
- Returns `{confirms_direction, win_rate, total_trades, profit_factor, timeframe}`

### [NEW] `agents/signal_evaluator.py` (strategy)
- Runs configured evaluation strategies from `core/strategies.py` on a signal using price data
- Returns per-strategy results

### [NEW] `agents/target_scorer.py` (strategy)
- Maintains running win rate per target in `target_scores` table
- Returns `{win_rate, total_signals, grade}`

### [NEW] `agents/db_saver.py` (action)
- Saves everything from the pipeline run to Supabase

### [NEW] `agents/telegram_notifier.py` (action)
- Renders template → sends via Telegram bot

### [NEW] `pipelines/full_signal_check.yaml`
The default pipeline: telegram → parse → evaluate → score → save → notify.

### [NEW] `pipelines/signal_with_pine.yaml`
Multi-step pipeline: telegram → parse → Pine confirm → save → notify only if Pine agrees.

### Verification
- Feed a test message → verify it's parsed, evaluated, saved, and notification sent
- Run the Pine pipeline when TV is open → verify Pine step executes
- Run the Pine pipeline when TV is closed → verify it skips cleanly
- Check cursor resume: stop, restart, verify no missed messages

---

## Phase 4: Dashboard

FastAPI API + vanilla HTML/CSS/JS control panel.

### API (`main.py`)

| Method | Endpoint | What |
|--------|----------|------|
| `GET` | `/api/status` | System health |
| `GET/POST` | `/api/targets` | List / add targets |
| `GET/PUT/DELETE` | `/api/targets/{id}` | Target CRUD + config |
| `GET` | `/api/signals` | Filterable signal list |
| `GET` | `/api/signals/{id}` | Signal + evaluations detail |
| `GET` | `/api/pipelines` | List pipelines |
| `GET/PUT` | `/api/pipelines/{name}` | Pipeline YAML CRUD |
| `POST` | `/api/pipelines/{name}/run` | Manual trigger |
| `GET` | `/api/runs` | Pipeline run history |
| `GET` | `/api/coins` | Known coins + scores |
| `POST` | `/api/research` | Start a research session |
| `GET` | `/api/research/{id}` | Research session status |

### Frontend (`static/`)

**5 pages** — dark mode, glassmorphism, Inter font:
- **Dashboard**: status indicators, stats cards, activity feed
- **Agents & Targets**: target cards with grades, config editor, signal history
- **Pipelines**: YAML editor, run history, "Run Now" button, backtest results
- **Signals**: filterable table, click-to-expand detail
- **Settings**: LLM config, Telegram config, scheduler, research sessions

### Verification
- Dashboard loads at `localhost:8000` with live data
- CRUD targets through the UI
- Trigger pipeline from UI → see results in run history
- Start research session from UI → see progress

---

## Phase 5: 24/7 Operation

### [MODIFY] `main.py` — startup flow
```
1. Load .env
2. Init Supabase, LLM router
3. Init Telethon client
4. Init Brain (with preferences loaded)
5. Auto-discover agents
6. Load pipelines + target configs
7. Start scheduler (telegram polling, re-evaluation, heartbeat)
8. Start Telegram bot listener (for chat)
9. Start FastAPI server
```

### Scheduled Jobs
- **Telegram poll**: every 60s, fetch new messages → run pipeline
- **Re-evaluate**: every 6h, re-evaluate "open" signals that now have enough price data
- **Heartbeat**: every 5min, log system status

### Verification
- Runs for 30 minutes without crashes
- Stop + restart → catches up via cursors
- Scheduled jobs fire on time

---

## Build Order

| Phase | What | Priority | Est. Size |
|-------|------|----------|-----------|
| **1** | Core engine (pipeline, agents, DB, LLM, strategies) | Backbone | ~600 lines |
| **2** | The brain (chat, preferences, research loop) | **Core product** | ~400 lines |
| **3** | Starter agents (telegram + pine + evaluator + 4 more) | Hands for the brain | ~700 lines |
| **4** | Dashboard (API + frontend) | Eyes for you | ~1000 lines |
| **5** | Scheduler + 24/7 | Autonomy | ~150 lines |
| | **Total** | | **~2,850 lines** |

After V1: adding a new agent = one file in `agents/`. Creating a new pipeline = one YAML. Teaching the brain = chat with it on Telegram. No infrastructure changes.

---

## What Comes Next (Improvement Work, Not Infrastructure)

These are all just "drop in a new agent" or "create a YAML" or "teach the brain":

- `agents/exchange_checker.py` — check coin on exchanges
- `agents/price_checker.py` — fetch OHLCV data
- `agents/scam_detector.py` — pre-pump detection
- `agents/pipeline_backtester.py` — replay historical signals
- `agents/youtube_reader.py` — scan YouTube channels
- `agents/cmc_checker.py` — CMC sentiment
- `agents/etoro_scraper.py` — copy trading
- `agents/convergence_detector.py` — cross-source analysis
- `agents/web_search_discoverer.py` — find new groups
- `pipelines/backtest_weekly.yaml` — automated optimization
- `pipelines/youtube_audit.yaml` — influencer scoring
- `pipelines/cross_source_conviction.yaml` — multi-source signals
- Teaching the brain new research methods via Telegram conversation

Each one is independent. Each one takes 30-60 minutes to add. The backbone supports them all from day 1.

---

## Open Questions

> [!IMPORTANT]
> **1. Supabase**: Do you have a project ready, or should I help create one?

> [!IMPORTANT]
> **2. Telegram auth**: Telethon needs a one-time phone login. Want me to write a standalone `auth_telegram.py` script for this?

> [!IMPORTANT]
> **3. Port**: `localhost:8000` or different?

> [!IMPORTANT]
> **4. First target group**: Which Telegram group for the first test?
