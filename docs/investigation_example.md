# Cryptron — A Worked Investigation

> This file exists so the investigation doesn't have to be re-explained every time.
>
> **Cryptron is an investigator.** It runs experiments, never accepts the surface number,
> always asks *why*, chases the driver behind every result, and writes down what survives —
> so the next question is cheaper than the last. This is one concrete trace of that loop, the
> thing [`cryptron_creature.md`](cryptron_creature.md) describes abstractly (§7 the brain, §8
> threads, §9 patterns). Read it as the *shape of thinking*, not a result to trust.
>
> The point it proves: the **reasoning is the easy part** — a handful of general questions any
> good investigator asks. The hard part is the **memory** — writing the finds down in a shape
> the investigator can reason over easily. That store is still to be designed; this trace is a
> sample of the questions it will have to answer.

---

## The investigation, told straight

Start with a group. Score its last 50 signals the obvious way — did TP1 hit before the SL?
**10% win. −90%.**

Terrible. But 10% is *worse than random*, and worse-than-random isn't noise — it's
information. So **why?** Either they're a scam, or I'm scoring them wrong (their stop is so
tight that normal wiggle knocks me out). Ask another sense — the pump-and-dump molecule — and
it says *not a scam*. So it's not a lie. It's their direction, or it's my exit.

If they're reliably wrong, fade them — flip every call. **30% win, −50%.** Still losing, and
*that's* the tell: you can't lose going both long *and* short from direction alone. So it was
never direction.

Then what's eating me? Maybe the coins just don't move. Check it — ignore direction, ignore
exits: do these coins go anywhere, ±15% in two weeks? **Yes.** The money is there. So I'm
entering at the wrong *moment* — they post at the spike and I buy the top. New knob: wait for
the pullback.

Enter on a −10% dip instead. **50% win, +30%.** First green — but I *built* that rule on these
same 50 signals, so of course it fits. Doesn't count until it holds where I didn't look. Fresh
batch, same rule, no tuning: **40% win, +20%.** It held. Real, if small. And notice — it makes
money at 40% win, which means the 80%-winrate bar is the wrong ruler for this kind of strategy.
It's expectancy, not winrate.

Does the trick travel? Run the same pullback on another group. **20% win, −10%.** Nope — but
look closer: 20% wins yet only −10% down means the winners were *big*. That's not a dead group,
it's a *mix* — a few good ones buried in noise. So what's different about the good ones? Market
cap. This group trades **memes**. And a meme isn't the same animal — thin, reflexive,
lottery-shaped. My pullback-and-peak-gain exit was capping the one thing that makes a meme
worth holding: the moonshot. Memes get their own playbook.

So what drives a meme? **Attention.** Go look. One winner had **1300 comments** before it ran;
a loser had **50**. Another winner had **1000 comments and a YouTuber sitting on 2M views.**
Same driver — attention — through different eyes: Twitter, YouTube. When several light up at
once, that's the real tell.

Then the coin that breaks it: **lots of comments, still failed. Why?** Because the whole market
fell that day. It wasn't the coin — it was the tide. Which means I've been measuring wrong the
*entire time*: every move is the market plus the coin's own move, and I never separated them.
Now my *winners* are suspect too — did attention pump them, or were they just riding a green
day? Re-score everything against the market. **Beat the tide, or you've got nothing.**

That's the loop. It never stops at the number — it asks why, and the why keeps pointing at a
deeper variable, until what's left is the real one.

---

## The trace (quick reference)

One Telegram signal group. Cold start, empty memory. Each step is a **result** and the **move**
it triggered — and the move is always a *general question*, never a one-off hack.

| # | Experiment | Result | The move (and the general question behind it) |
|---|-----------|--------|-----------|
| 1 | Score the group's last 50 signals under *TP1-before-SL*, vs a random-entry baseline | **10% win, −90%** | Worse than random is *information*. **Why?** Either a scam, or the exit organ is wrong (SL too tight, noise knocks you out). |
| 2 | Ask another sense — the pump-and-dump molecule | **"not a scam"** | **Triangulate.** Scam ruled out → it's direction or the exit. |
| 3 | Fade them — flip every call, clean symmetric exit | **30% win, −50%** | 10% doesn't flip to 90%; inversion only pays if they're *genuinely wrong on direction*. Still loses → **both directions lose → it isn't direction.** |
| 4 | Ignore direction *and* exits: does the coin move **±15% in 14 days** at all? | **yes** | Money's there → the poison is **entry timing** (they post the spike). Research discovers a new **atom**: *entry offset*. |
| 5 | Enter on a **−10% pullback in 48h**, then peak-gain exit | **50% win, +30%** | First green — but *invented on these 50 signals*, so in-sample. **Doesn't count until it holds where I didn't look.** |
| 6 | Same rule, **fresh batch**, no tuning | **40% win, +20%** | Held out-of-sample → **real edge**, modest. Makes money at 40% win → the 80%-winrate bar is the wrong ruler here: **expectancy, not winrate.** |
| 7 | Does it **transfer**? Same rule on **another group** | **20% win, −10%** | **Did it happen elsewhere?** No. Generalizing now would be the n=1 trap. |
| 8 | Read the loss, don't bin it | *(20% win, only −10%)* | Winners big, losers small → a **mix, not a failure.** **Contrast winners vs losers.** |
| 9 | What *differs* between the groups? | market cap → **memes** | **What kind of coin is this?** Mechanism-backed class: memes are thin, reflexive, lottery-shaped. The pullback+peak-gain exit is a *large-cap* rule caging the moonshot. Memes → their own **tissue**, own exit (hold-and-let-run). |
| 10 | What drives the meme winners? | **attention** | 1300 comments before a winner vs 50 on a loser; another winner had 1000 comments **+ a 2M-view YouTube video.** The driver widens from "comments" to **attention** — one latent thing seen through *different senses*. Several lighting up at once = **convergence**. |
| 11 | A meme with **many comments** still failed | *(failed despite attention)* | **Always ask why.** Not the coin — **the whole market fell.** Every move = market (**beta**) + the coin's own (**alpha**), and I never split them → my *winners* are suspect too. **Re-score everything market-adjusted.** The market is the **null model**: beat the tide or you have nothing. |

It never "finished." It descended from *"this group is 10% — garbage"* to *"attention —
real, leading, multi-channel, measured against the market — is what separates meme winners
from losers."* That descent, **surface number → real driver**, is the whole job.

---

## The operators (the general questions)

Every move above is one of a small, reusable set. This is the investigator's verb list — what
turns *one result* into *the next thread* — and it's what dissolves the docs' hand-wavy
"invent / creativity" (§7 move 4, §10): inventing is just asking one of these the thread hasn't
been asked yet, or importing one that paid off elsewhere.

- **Why?** — never take the number at face value; every result is a cause to find.
- **Generalize** — did it happen elsewhere? (other groups, coins, timeframes, periods)
- **Perturb** — what if I change one atom? (follow the gradient)
- **Classify** — what *kind* of coin is this, per outside sources? (inherit the class's behavior)
- **Enrich** — what related info on this coin/source would help? (pull from other senses)
- **Contrast** — how do winners differ from losers?
- **Decompose** — is the aggregate hiding sub-populations?
- **Isolate** — what *else* was acting on this? (the market, the sector — separate it out)
- **Mechanism** — *why would* this be true? (a reason, not a coincidence)
- **Timing / causality** — did the cause come *before* the effect?

The catalog is meant to **grow**, and memory should **rank** which question tends to pay off —
that ranking is the §10 "for-you feed," grounded in what has actually worked.

---

## The disciplines (the immune system)

The operators find candidate patterns; these keep the false ones from being believed. In a
space where false patterns are infinite, cheap, and self-reinforcing, this is the hard,
load-bearing half.

- **Never accept the surface number** — every result is a *why*, not a verdict.
- **Triangulate** — confirm or kill with an independent sense.
- **Demand a mechanism** — "small-caps move more" has a reason; "Tuesdays win" is probably luck.
- **Refuse to overgeneralize** — a rule that works once must be *tested for transfer*; when it
  fails, that failure is the next clue (step 7 → the meme discovery).
- **Chase the driver, not the proxy** — comments → attention; group → market-cap class;
  pullback → entry timing. State finds over the driver so they transfer.
- **Isolate the market** — every move is **beta + alpha**; score *excess return vs the market*,
  or you credit a signal for what was just the tide. The market is the **null model**.
- **Relative, not absolute** — 1300 comments is huge for a microcap, nothing for DOGE. Measure
  the spike vs the coin's own baseline.
- **Leading, not coincident** — buzz (or a video) *after* the move is exit liquidity, not a
  signal. Confirm the cause preceded the effect.
- **Out-of-sample before belief** — a rule invented on a batch can't be proven on the same batch
  (steps 5 → 6).
- **Base rate / survivorship** — a winner with 1300 comments means nothing until the losers'
  counts are checked.
- **Small-n caution** — two points earn a *thread*, not a *rule*.

---

## What gets written down — atoms and conclusions

At the end of the day the deliverable is concrete: **the atom-values.** A signal strategy just
*is* a configuration of atoms — timeframe, entry offset, exit rule, attention threshold — per
molecule, per tissue, per organ. That's what you'd actually trade. So memory documents two
linked things at every level of the anatomy:

- **the settled config** — the best atom-values for this molecule / tissue / organ, with its
  score (out-of-sample, market-adjusted). *This is procedural memory (§6) — "how it moves now."*
- **the conclusions** — the patterns that got you there and generalize past this one case,
  each **scoped** to a level or class. *This is the patterns store (§6/§9).*

The two are welded by one rule: **a conclusion is only "good data" if it cashes out as a
directive over atoms.** "Attention drives memes" is trivia until it becomes *"add an
attention-filter atom to the meme tissue, threshold ~here, drop the tight-TP exit atoms."* A
find that doesn't move a knob is a fact, not a find. And the conclusions are what make finding
atoms **cheap instead of brute-force** — "memes want hold-and-let-run" deletes every tight-TP
config from the meme search *before it runs* (§9, the coverage of an endless space).

This trace also shows what the memory must *hold onto*: much of the decisive evidence —
comment counts, the YouTube view spike, the market state on the day — is **ephemeral**. Not
captured the moment it's sensed, it's gone, and the experiment becomes impossible later.

So the unit to design — the **shape of a "find"** — has two faces sharing one spine, the
**atom**: everything in memory is either *an atom-config* or *a conclusion about atom-configs*,
carrying its mechanism, scope, evidence, and a confidence that updates when the next
counterexample lands. Get that shape right and the memory falls out of it. Get it wrong and the
investigator reasons over mush. That design is the §15 #1 gate — and the first thing on the
path that's actually buildable.
