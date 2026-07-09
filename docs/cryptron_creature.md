# Cryptron — The Creature

> This document is the *why* and the mental model. It is an **ideas file**, not a spec —
> loose on purpose, so we don't lose concepts while we keep tuning. It describes what Cryptron
> **is** as a living thing, so every later decision — what to build, what to skip, what "done"
> means — can be checked against it.
>
> An earlier attempt designed a monitoring system that validates signals and notifies you —
> then got thrown away for being designed without this model underneath it. A pipeline that
> notifies you is real, but it is a *byproduct*. This document describes the actual organism.

---

## 1. The one-sentence vision

A crypto research assistant that works 24/7, improves itself, and does what I do — but
better and faster — until what it has learned **is** a profitable general strategy.

It either hands me signals, or one day trades on them itself.

---

## 2. The problem it exists to solve

I already know the loop. I do it by hand:

```
copy a Pine strategy (Discord / GitHub)  →  run it  →  see if it worked
        →  if not, adjust its settings  →  see if it's better
        →  try it on other timeframes and coins  →  see if it worked
        →  try another strategy  →  note what I learned
        →  ... and it never ends.
```

The same loop drives everything else — Telegram groups, investors to copy (eToro), YouTube,
Twitter, Discord, news. And the *combinations* of sources (e.g. test a strategy only on
small-caps that trade on a known exchange and have many CMC upvotes — Pine **and** CMC
together) are more endless still.

Each source is effectively endless. The work is not hard — it's **too much**. That is the
whole reason the creature exists: to run this loop across a combinatorial space, while I
sleep, and to **find the patterns** I'd never have time to see.

The base of all self-improvement is simple: **run something, see how it went, adjust, and
keep the knowledge.** An AI can do that far better than I can, forever.

---

## 3. The anatomy

Cryptron is built like a body. Each level is a *composition* of the level below.

| Level | What it is | Examples |
|-------|-----------|----------|
| **Atom** | the smallest tunable setting — a single knob | Pine: timeframe, moving-average period. Telegram: stop-loss %, take-profit % |
| **Molecule** | one source, configured — a bundle of atoms for a single domain | Pine, Telegram, CMC, YouTube, Discord, Twitter, news, web scraping |
| **Tissue** | combines molecules **of one source/domain** and runs experiments to structure their settings — *this is where self-improvement lives* | "tune Pine's atoms"; a single Pine **strategy built from several Pine sub-strategies**, tuned together |
| **Organ** | combines already-tuned tissues **across different sources** into a pipeline; its own wiring (incl. the joint settings between sources) is tunable too | Pine + CMC; Telegram → CMC → Pine |
| **Creature (Cryptron)** | the whole setup that runs the organs; holds the brain and the memory | the 24/7 assistant |
| **Words** | what the creature emits | signals |

**The tissue/organ line is *intra-source vs cross-source*.** Combining molecules *within one
source* — several Pine sub-strategies into one strategy — is a **tissue**. Combining *across
sources* — Pine + CMC — is an **organ**. So tuning the joint settings of a cross-source
combination is an **organ experiment** (per the rule below: any configured level can be the
subject of an experiment).

### The atom is the unit of configuration — not the unit of knowledge

A common mistake (and the one to avoid) is to treat an "experiment" as the atom. It isn't.
The atom is just a knob. **The experiment is an *activity* — it runs over a configured level
to settle that level's atom-values.** Most often it runs at the **tissue** level: a tissue is
*alive*, it keeps experimenting to settle the atom-values of its molecules. But experiments
are **not exclusive to tissues — an organ can be experimented on too.** An organ's *wiring* is
itself configurable (the order of its tissues, the thresholds at the joints between them are
atoms), so tuning that wiring is an experiment on the organ. The levels stay distinct — a
tissue combines molecules, an organ combines tuned tissues; what generalizes is only that
**any configured level can be the subject of an experiment.**

### Two kinds of combination — do not confuse them

- **Tissue-combination happens at *learning time*.** A tissue brings molecules **of one
  domain** together to *discover* good settings. Its product is **tuned settings**.
- **Organ-combination happens at *run time*.** An organ wires tuned tissues — **typically from
  different sources** — into a sequence that *produces signals*. Its product is **words**.

Same parts, two different purposes, two different times. (This is about *combination*; it
doesn't confine experiments — an organ's wiring can still be tuned at learning time before the
organ is used at run time to produce words.)

---

## 4. Testing — the testing organ

The single biggest mechanism the silhouette was missing: **there is no universal score.**

A signal isn't "good" or "bad." It's good-or-bad *relative to how you'd trade it*. The score
is the **output of a trade-management organ**, not a constant. Concrete example: a signal
surged 300% after a couple of weeks. Under a fixed 10% take-profit / 5% stop-loss it's a
loss — you get knocked out long before the surge. Under hold-and-let-run it's a 300% win.
*Same signal.* Only the way of trading it changed.

So testing is not a second body — it's a **testing organ** in the one body, built from the
same levels:

- **atoms:** tp%, sl%, the "sell half" level, trailing distance…
- **tissues:** a *fixed TP/SL* tissue, a *hold-until-TP* tissue…
- **the organ itself:** *sell-half-then-keep-managing* — a multi-step trade-management strategy
  composed of those tissues.

And which testing organ is *correct* is itself discovered **per source**: a scalping group
wants tight TP/SL; a slow-burn group wants hold-and-let-run.

This means the real search space is **(source config) × (testing config), searched jointly.**
You cannot know if a source is good until you've also discovered *how you'd trade it*. The
two questions are entangled and must be co-discovered.

> **"Is there a way to make money off this signal?"** is therefore an *existence question over
> the space of testing organs* — does there exist a trade-management organ under which this source is
> profitable? That is the deep version of the question, and it is the heart of evaluation.

---

## 5. Embodiment — senses and hands

The creature is **embodied**. Senses and hands aren't an appendix; they're the body where it
meets the world, threaded through the whole anatomy:

- **Every molecule *is* a sense fused with a config.** The Telegram molecule is an ear
  (reads groups); the CMC molecule is an eye on sentiment; the YouTube molecule is an ear on
  influencers. Perception is the bottom of each source's anatomy — a molecule without its
  sense is just a name.
- **The ambient discovery drive is peripheral vision** — a sense pointed at the *whole world*
  instead of one source (web search, scraping, trending feeds). This is the alertness organ
  (see §10).
- **Hands are how tissues actually run experiments** — the backtest hand, the price-data
  hand, and the **trade-simulator hand** that applies a testing organ to price history and
  answers the money question of §4.
- **The voice that speaks signals is a hand too** — the creature's mouth (notifications).
- **A coding assistant is itself an idea-tool** — if it proposes an improvement, that's a new
  hypothesis worth testing.

Illustrative senses/hands (examples to make the idea clear, not a final list): **Pine,
Telegram, CMC, YouTube, Discord, Twitter, news, web scraping** — plus market data and a
trade-simulator for running tests.

> **The embodiment principle:** Cryptron's intelligence is bounded by its sensorimotor reach.
> It can only reason about what it can sense, and only test what it has a hand to run. Never
> design analysis that needs data the creature can't perceive, or experiments it has no hand
> to execute. The body we can build is exactly as smart as its real tools.

---

## 6. Memory

Like a human, the creature has more than one kind of memory. I don't *recall* how to run —
yet I can improve my leg movement by training. Three stores:

- **Procedural memory — "how to run" (the muscle).** The current *best known atom-values* of
  every molecule and tissue. Never read as facts; it's simply *how the creature moves now*.
  Experiments are the training that sharpens it. Overwritten only when beaten.
- **Episodic memory — the raw history.** Append-only log of every experiment: variant,
  hypothesis, result. Never deleted; it's the evidence.
- **Patterns — the compression.** Generalized findings, made *machine-usable*:
  `{statement, scope, directive, evidence, confidence}` — e.g. "MA-crossover needs timeframe
  ≥ 4H on alts" with a scope, a prefer/avoid directive, supporting/contradicting experiment
  ids, and a confidence that **updates** rather than overwrites.

Hard rules:

1. **Memory spans the full stack, atom → organ**, and stores every config — source, testing,
   combination — in **one uniform shape**, so anything is addressable and comparable the same
   way.
2. **It lives at the creature level, not inside one tissue.** A lesson the Pine tissue learns
   is available when the brain reasons about anything else. One shared genetic memory.
3. **It must retrieve only the relevant slice** — scope-indexed, comparable, never-forgetting,
   efficient.
4. **Ephemeral data must be captured the moment it's sensed.** Price/OHLCV is always
   re-fetchable, so Pine and signal backtests are the workhorse — runnable thousands of times
   while I sleep. But snapshot data (CMC votes, sentiment, order-book state) can't be
   re-derived for a past moment; if it wasn't saved when first seen, it's gone. So experiments
   that depend on ephemeral data are only possible if memory cached it at capture time.

> **Implementation is deliberately deferred — and the order is not optional.** What the brain
> asks of memory is what *defines* memory, so we design the brain's data flow first, then the
> store. The flow that must be designed before any implementation:
>
> ```
> experiment results
>    → retrieve from memory the data related to the results
>    → analyze
>    → save the analysis into memory
>    → retrieve from memory the data related to the analysis
>    → design the new experiment
>    → (run) → repeat
> ```
>
> Only **after** that flow is concrete do we choose *how* memory is implemented — **a DB, a
> RAG index, both, or something else.** Design the consumer, then the store. For now we only
> fix *what it must do.*
>
> ⚠️ **Note for the next session:** do **not** start implementing memory (or anything) before
> the brain's flow above is designed. Implementing first means building the wrong store and
> doing the work twice.

---

## 7. The brain and the analyze → design cycle

The brain is at the creature level and runs one continuous cycle (analyze and design are not
two systems — they're one loop):

```
the brain holds a FRONTIER — what's been tried, current best configs,
                             live patterns, and the open threads it's pulling
        │
   ANALYZE new results → revise beliefs: a pattern strengthens or breaks,
                          a hypothesis is born or dies, the frontier updates
        │
   DESIGN next move → advance a thread or open a new one (§8)
        │
   if a config crosses the bar → promote it → speak signals (§11)
        │
   run → repeat
```

**Designing the next experiment is general reasoning, not a private heuristic — it belongs in
the brain.** The moves are the moves any good researcher makes:

1. **Extend along the axis** — 1H ok, 4H better → try daily. (follow the gradient)
2. **Generalize a surprising result** — a small coin beat BTC → try *another* small coin → is
   it a pattern?
3. **Transfer a hypothesis by analogy** — CMC upvotes mattered → does Twitter sentiment matter
   too? (move the pattern to an analogous dimension)
4. **Invent** — propose a genuinely new hypothesis (creativity, §10).

The intelligence that matters most is *which experiment to run next*. Running thousands of
backtests is just compute; choosing the next move wisely is the skill — and it's the brain's,
fed by memory, not something hardcoded from me.

This is the junior-to-senior arc: early on the brain asks a lot and runs crude experiments;
over time it internalizes my judgment, reasons sharper, and promotes things on its own
because it has seen me agree before.

---

## 8. Threads — the unit of focus

The brain doesn't reason one experiment at a time. It pulls a **thread** (a line of inquiry):
"find the right timeframe for CryptoSlaya on alts" is a thread; the 1H→4H→daily experiments
are beads on it. Analysis happens at the thread level.

**The stopping rule (and it's the 300%-surge insight pointed at research itself):** don't stop
at the first diminishing result — that's the early-TP mistake, you'd quit right before the
payoff. Instead:

- Run *several* experiments along a thread.
- Stop when the thread is **stable** — whether stable-**good** (→ promote, it speaks) or
  stable-**bad** (→ abandon).
- Keep pulling through the **volatile / inconclusive** zone — that's research chop, not a
  reason to flinch.

**Threads run in parallel**, and the **relations *between* threads are first-class
discoveries** — often the most valuable ones, because they're the broadest generalizations.
"Alts wanted 4H, BTC wanted 1D" isn't two facts; it's one pattern: *timeframe scales with
volatility class.* Cross-thread relations spawn new threads. The frontier holds many threads
at once and watches the gaps between them.

---

## 9. Patterns — how the creature covers an endless space

The settings, experiments, and especially their combinations are **endless**. You cannot cover
that space by running everything — not even with all the compute in the world. Brute force
loses.

The only way through is to find **what is common between experiments** — the **patterns**. A
pattern is a generalization that explains many results at once, so finding one is worth
thousands of runs: it lets a finite amount of work *cover* an infinite region.

So patterns are the creature's **method of coverage**:

- They are the **compression of declarative memory** — what the pile of results *means*.
- They make the loop **smarter than grid search** — each confirmed pattern prunes huge regions,
  so the brain spends experiments only where they're informative (confirming or breaking a
  pattern).
- The profitable general strategy at the end (§12) is itself the **top-level pattern.**

The brain's real job, restated: **not to run every experiment, but to find the patterns that
let it skip almost all of them.**

---

## 10. Creativity and alertness

The problem is open-ended: **find a profitable general crypto strategy.** No fixed menu of
sources, no fixed menu of ideas. Pine-from-Discord-or-GitHub was only an *example*. An idea
worth testing can come from anywhere — a YouTuber, a coding assistant, the brain's own
variation on something half-working, a pattern transplanted across domains, a thought I drop
in chat.

So **ideas are first-class inputs from any origin.** A new idea can grow into a new molecule,
tissue, or experiment — the body grows new parts, it doesn't get rebuilt.

**My creativity is largely alertness.** I scroll YouTube, an influencer about crypto pops up,
and I have a new source — the algorithm feeds me suggestions that fit my taste. The creature's
analog is an **ambient discovery drive** (peripheral vision, §5): a background sense that scans
the world and builds its *own* "for you" feed by ranking what it finds against the patterns
that have been **paying** — memory becomes the recommender. And it can do what my algorithm
won't: deliberately hunt **adjacent** ideas and even **contrarian** ones.

So explore splits in two:

- **directed explore** — generalize/transfer from patterns already trusted (cheap, safe),
- **ambient explore** — scan the world for genuinely new sources/strategies (the alertness
  analog).

Both just **queue candidate threads** for the brain to vet. Discovery stays **read-only** —
scraping to *find* ideas, never auto-acting on what a page says.

---

## 11. The "reasonably good" bar and autonomy

A thread that goes **stable-good** crosses the bar and gets **promoted**: the brain starts
watching live, emits signals, and tells me — automatically. Research and production aren't two
systems; they're two phases of the same organ, and the brain owns the promotion.

The bar starts as something I set crudely, per tissue/organ ("don't talk to me about a group
until it beats 55% over 30+ signals"). But **teaching the brain my real bar is itself a loop**:
it watches which promotions I actually agreed with and tunes the threshold toward my true
taste.

What it may do: **today** — research, accumulate knowledge, promote, and emit signals to me
(it does not trade). **Later, maybe** — trade on its own signals, once it's earned that trust.

---

## 12. What "finished" looks like

The end state is not finished software — it's a **profitable general strategy.** And that
strategy is not something I write at the end; it **is the distillation of everything the
creature has learned** — the accumulated patterns, compressed into something I can read as my
own method. The system isn't a tool that follows my strategy; it's the place where my strategy
is *discovered.*

---

## 13. How it's built

The one inversion that earlier attempts got backwards:

> **The experiment engine is the heart. Signals are a byproduct. Memory is the bloodstream.
> Senses and hands are the body that touches the world.**

- The **research loop** (design → run → analyze → save → design next) is the organism's
  metabolism. It deserves the most care and the most code.
- **Pattern-finding** is the loop's purpose, not a report it prints. A loop that runs
  experiments but never generalizes is a grid search in a costume — it will never cover the
  space.
- **Testing is its own organ** (§4): co-search source × trade-management, never assume a fixed
  score.
- **Memory** makes the loop *compound* instead of repeat; its tech is designed after the brain
  that consumes it.
- **Creativity must have a path in** — a new idea (from a YouTuber, from you, from the brain,
  from me in chat) must be able to become a testable part without a rebuild. If ideas can only
  enter as hand-coded molecules, the creature can't explore, and exploration is half its mind.
- **Embodiment bounds everything** (§5): design only for senses it has and hands it can swing.
- The **signal pipeline** (Telegram → CMC → Pine → notify) is real, but it's what the creature
  *says* once a tissue is healthy — not the reason it exists.

A build that produces twenty source-agents and a pretty dashboard but a shallow research loop
has built the wrong creature well. A build that makes the loop, the testing organ, and the
memory genuinely excellent — even with only Pine and one Telegram molecule to start — has
built the right one.

---

## 14. Architecture direction — the brain as a multi-agent system (MAS)

*(A direction to evaluate, not yet locked — captured so we don't lose it.)*

The brain need not be a single LLM loop. It can be a **society of specialized agents** — a
multi-agent system, effectively microservices coordinated around the shared memory, each an
LLM-driven role:

- **Experiment-runner** — executes experiments via the hands (backtest, replay, simulate).
- **Analyzer** — turns results into revised beliefs (patterns ↑/↓, hypotheses born/died).
- **Designer** — chooses the next move per thread (extend / generalize / transfer / invent).
- **Scout** — the ambient discovery drive (§10): scans the world for creative new strategies
  and hypotheses, queues candidate threads.
- **Steward** — monitors the health of memory and tools (senses/hands), keeps the substrate
  clean and efficient.
- (possibly) **Critic / Promoter** — guards the "reasonably good" bar (§11) before anything
  speaks.

In the biology: the brain isn't one cell but a **colony** — organs staffed by many specialized
cells working at once. This fits the creature naturally because **so much is parallel**:
threads run in parallel (§8), so runners and analyzers can be **multiple instances**; scouts
run continuously in the background; designers work per-thread. The shared memory (§6) is the
**bloodstream** they coordinate through.

This stays subordinate to everything above: the MAS is *how* the brain might be built, not a
replacement for the brain's data flow (§6) or the embodiment principle (§5). We still design
the flow first, then decide whether one loop or a colony runs it.

---

## 15. Open questions — still to design

We have the body plan. These are the mechanisms still *not* designed, roughly in dependency
order. **Design them as concepts before any implementation** (see the §6 warning).

1. **The brain's data flow, in detail** (§6/§7) — the analyze → save → retrieve → design
   sequence made concrete. Everything downstream waits on this.
2. **What an "analysis" actually is** — the concrete shape of a revised belief / updated
   pattern that gets written back to memory after a result.
3. **How the designer chooses among the four moves** (extend / generalize / transfer / invent)
   and balances **exploit vs explore** under a limited budget.
4. **Thread lifecycle** — how a thread is born, how "stable" (good or bad) is actually
   declared, and how cross-thread relations get noticed.
5. **The candidate → thread pipeline** — how a raw idea from a scout (or from chat) becomes a
   testable thread.
6. **The trust gene** — how much evidence, across how much variety, before a pattern is
   trusted enough to *skip* whole regions of the space; and what happens when two patterns
   conflict.
7. **Then, and only then:** memory implementation (DB / RAG / both / more), MAS decomposition,
   and tools wiring.

> The natural next target is **#1**, the brain's data flow — it's the thing the most other
> pieces depend on.
