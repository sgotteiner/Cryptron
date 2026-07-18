# Cryptron — Brain Design

> How the brain works and is guided: the mission, the division of labor with the user,
> the evaluation workflow (checks → verdict → correction), and the learning rules that
> keep memory clean. Written so future sessions make **small edits here** instead of
> re-deriving the workflow from chat logs.
>
> Grounding: [`cryptron_creature.md`](cryptron_creature.md) §7 (analyze→design cycle),
> §10 (creativity/alertness), §11 (the dialogue, progressive autonomy), §14 (MAS
> direction); [`memory_design.md`](memory_design.md) §6 (the retrieval contract the
> brain runs on). The live, enforced form of this doc is `cryptron/brain/prompt.py` —
> when the two drift, reconcile them in the same edit.

---

## 1. The mission (the user's full-vision statement, 2026-07-17)

Cryptron's end goal: **find good opportunities on its own, using the user's evaluation
methodology** — sparing his time, effort, and extending his limited memory and
capability. There are many signals (Telegram groups, trending pools, and later more
sources); the job is deciding **which are worth following**.

The working loop that gets there:

1. **An outcomes knowledge base** — coins we KNOW won or lost and *how* (under which
   way of trading: `call_outcomes`, one row per call per organ+config), JOINed with
   the background the senses captured about them (sentiment, attention, liquidity,
   regime — at matching times).
2. **Comparison experiments** over that base draw the conclusions (finds).
3. **New signals are evaluated against that knowledge** — scope-match + recall serve
   precedent before the first new check runs.

The mindset for anything it sees, in the user's words: *is there an opportunity in
this signal? do I know the quality of this opportunity? did I have everything needed
to assess it, or do I need more tools?* The self-check both evaluates the signal and
grows the body — a missing tool, named honestly, is a roadmap item (§13 of the
creature doc: raising).

A second, legitimate mode: **quick answers.** Sometimes the user just wants a number
(a market cap, a listing) without visiting websites. Answer directly; not every
message opens an investigation.

---

## 2. Division of labor — he teaches checks, not conclusions

The single most important boundary, stated after two corrections in one day:

- **The user tells Cryptron WHAT to check — never what to conclude, never which
  thresholds matter.** Cutting lines ("100–500M cap coins with >70k watchlists took
  off") are Cryptron's to *discover* by contrasting winners vs losers in the knowledge
  base. He cannot run these checks himself — *too much to check is why Cryptron
  exists.*
- **Every experiment is a comparison.** Vs the market, vs the losing calls in the same
  cohort, vs the coin's own baseline. A number without a comparison group is not
  evidence; a single coin is an example, never a finding. No data collection for its
  own sake — capture serves comparisons (hence cohort capture: the *called* coins,
  winners and losers alike, get the same metrics at matching times).
- The same boundary binds the build sessions (Claude): hands get numbers, memory saves
  and retrieves them, the brain analyzes them. The research belongs to Cryptron in the
  Telegram dialogue, never to the assistant in the build session.

---

## 3. The evaluation workflow (checks → verdict → correction)

How a signal/coin/opportunity is handled in the dialogue:

1. **Retrieve first** — recall() + finds_in_scope() before any new check: what does
   memory already know about this class/situation? (memory_design §6; never re-derive.)
2. **Run the checks** — playbook lessons applied unprompted, plus whatever this case
   needs (attention, sentiment, listings, price behavior, regime).
3. **Commit to a VERDICT** — every evaluation ends with: **GOOD / BAD / NOT ENOUGH TO
   TELL**, resting on the **few most decisive checks**, plus what has NOT been checked
   yet. Never information-bomb: summarize what the user can work with; keep the rest
   ready for drill-in ("what about X?"). Never hide behind neutral data-reporting —
   *commit, be corrected, learn.*
4. **His correction closes the loop** — "you did enough" / "wait, you still need to
   check X" / "good or bad because…". That correction is the methodology transferring;
   it is banked (rule §4 below) and the next evaluation runs it unprompted. This also
   trains HIS guiding precision — the verdict gives him something exact to correct.

Progressive autonomy (creature doc §11) rides on this loop: as verdicts start
surviving his corrections, evaluation shifts from him to the creature.

---

## 4. The learning rule — with the gap-check

On **every** user message the brain asks: *is this a check, angle, or comparison I did
NOT already run and that is NOT already in my playbook?*

- **Already covered** → answer from what it has and say it was already factored in.
  **That is the system working, not a gap.** Over time most questions should land
  here — that is what learning correctly looks like. Do NOT re-save.
- **Not covered** → it is a gap: close it now, and `save_guidance` FIRST (before
  answering) **only if the lesson generalizes** — stated generally, never about one
  coin, with the why.
- A question that merely wants a number (mode 2 in §1) is neither — just answer.

**Enforced in code, not just prompted (2026-07-17):** banking is ALSO a dedicated
reflex (`brain/reflex.py`) — a single-purpose LLM call on every user message that only
asks "did he just teach a durable lesson?" and saves it (deduped). A side-duty in a
mega-prompt gets dropped under load; a separate act does not. When it banks, the reply
carries a visible "📘 Learned:" line so the user sees the contract honored.

Ask-once contract: he should only ever have to ask once; from then on the check runs
unprompted on every relevant investigation. When his question redirects a LIVE
investigation, the lesson carries `(thread_id, after_experiment)` — a pivot bead on
the path, so `replay_thread` shows the coaching at the exact turn it caused
(memory_design §6).

---

## 5. Memory economy — save the right things, never trash

The user: *"you don't want to overkill too. you don't want to save trash."* Enforced
two ways:

- **In the rules:** `record_experiment` what informs a decision; `save_find` only
  conclusions that move a knob (a conclusion that doesn't is a fact, not a find);
  `save_guidance` only lessons that are **general AND new**. Memory full of trash is
  memory that cannot be trusted.
- **In the code:** `save_guidance` dedupes (the playbook holds one truth per lesson);
  stale lessons are retired when the body outgrows them (e.g. the "no sentiment
  sense — BLOCKED" lesson died the day the sense was born).

---

## 6. Mechanics (current implementation, small and replaceable)

- **Two-tier flow (his design, 2026-07-18: "get the top gain in a simple query —
  that's it"):** every message first hits the FAST PATH (`brain/router.py`): a tiny
  routing call picks ONE retrieval — a single SELECT over the tables or one live
  lookup — and a tiny composer words the numbers (~2K tokens total). Judgment
  (evaluations, comparisons, verdicts, teaching, multi-step work) ESCALATES to the
  investigator loop (`brain/agent.py`): history (16 turns) + full system prompt →
  ONE JSON action per step, max 12 steps (~40K tokens/message — reserve it for what
  needs it). Dispatch registry: `brain/dispatch.py`. Every turn captured to
  `sense_chat` (chat is a sense).
- **LLM chain:** Claude (headless CLI on the paid plan; identity as true system
  prompt, zero native tools, retry + session-limit cooldown) → Gemini → Groq →
  OpenRouter as loudly-logged fallback (`brain/llm.py`).
- **Context is RETRIEVED, never dumped (his correction, 2026-07-18: "the point of
  the memory is to retrieve precisely — fix the system"):** lessons carry pgvector
  embeddings and each call injects only the top-6 relevant to the message
  (`paths.load_guidance` + `turns.system_prompt`); the identity prompt is compact
  by design (~1.8K tokens with playbook slice, was 4.4K); history is 8 clipped
  turns (~0.4K, was 2.1K); tool results cap at 2.5K chars. Measured: data question
  ~1.2K tokens (was ~40K), deep 5-step investigation ~18.5K (was ~40K). Remaining
  lever if deep turns must go lower: session reuse (send only deltas per step).
- **Tool surface:** the prompt's HANDS/MEMORY sections are the single authoritative
  tool list; `agent.run_tool` dispatches. Adding a hand = tool line in the prompt +
  dispatch line + the module. The embodiment rule stands: the prompt describes ALL
  the body there is, and the brain refuses honestly beyond it.
- **The logbook (`cryptron/log.py` → console + `logs/cryptron.log`):** every user
  turn, every LLM call (WHICH provider/model answered — silent fallback was a
  different brain wearing the same face), every tool call with args, every result,
  every failure, every reflex save. Nothing the system does is invisible.
- **Mechanical honesty:** if any tool call failed during a turn, the reply gets a
  code-appended "⚠️ System note — these checks FAILED" footer. Failure reporting
  does not depend on the model choosing to mention it.

---

## 7. Deliberately not decided (discovered by running)

- When verdict quality justifies autonomy steps (creature doc §11 bar) — watched, not
  scheduled.
- The autonomous loop (scheduled capture + self-driven threads + a "for-you feed" of
  scouted opportunities) — plugs into this workflow unchanged; not started until the
  user says the raising phase is ready.
- MAS decomposition (§14) — irrelevant to these contracts.
- Playbook→finds migration threshold — when full-injection visibly dilutes attention.

---

## 8. Status

**2026-07-17:** all of the above is live in `prompt.py` and enforced where code can
enforce it (dedupe, immune system, outcomes persistence). The raising phase continues:
probes in the Telegram chat, verdicts corrected, lessons banked once. This doc is the
place to record workflow refinements as they happen — small edits, not rework.
