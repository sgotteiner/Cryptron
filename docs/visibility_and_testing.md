# Cryptron — Visibility & Testing (the development method)

> How this creature is developed: from the chat, by using it. The user's four
> concepts, stated the day they crystallized (2026-07-19): *"I can see
> everything in Telegram when I ask for it; my messages serve as guidance and
> improvements; I can tell you to look at the logs and fix; you can test by
> mimicking my chat and seeing if the results are correct."*
> Companion docs: [`brain_design.md`](brain_design.md) (the flow these tools
> observe), [`memory_design.md`](memory_design.md) (what they inspect).

## 1. Everything visible from the chat (the console)

Telegram is the development console. Nothing requires opening files or a
terminal:

| ask | what you see |
|---|---|
| "what sources do you have" | every watched source with live row counts + tool catalog with WHAT-DATA descriptions (`capabilities`) |
| "what do you know about X" / "closest situation" | the canonical situation + nearest taught edges with exact sims + the action threshold (`graph`) |
| "show the trace" | the internal logbook tail verbatim: steps, sims, tool calls, failures, which LLM served (`trace`) |
| "what guidance did you save" | every lesson, verbatim (`playbook`) |
| "add this group: t.me/X" | the body grows and captures immediately (`add_source`) |

**The verbatim guarantee**: console outputs bypass the LLM composer entirely —
what you see is what ran, never a paraphrase. That's what makes the chat a
trustworthy debugger.

## 2. Messages are the development interface

Using the system IS developing it:
- A question that works = a test that passed.
- A question it can't handle = a roadmap item (the raising method: refusals
  and failures in the logs are the backlog).
- A teaching in a message is detected and offered back — 'bank' saves it.
- Every reply ends with a proposed next step — 'go' approves it AND teaches it
  as a permanent edge. Approval is teaching; the ceremony is one tap.

## 3. "Look at the logs and fix"

The logbook (`logs/cryptron.log`, mirrored to console) records every user
turn, route decision, step similarity, tool call with args, result, failure,
and serving model. The fix workflow (also in `CLAUDE.md`):
1. Diagnose from the log — the trace is complete enough that the failure is
   always in it.
2. Fix the bug.
3. **Decontaminate**: edit the hallucinated/broken bot messages in
   `sense_chat` to state what the fix did — the visible proof, in the
   conversation itself, that the fix landed. Fabricated turns stay marked
   (`fabricated: true`) and never re-enter the model's context (quarantine,
   not erasure — layer 1 stays append-only).

### Decontamination (his concept — why step 3 exists)

A stateful chat has a feedback loop: one bad reply gets saved, re-fed as
context, imitated, and built upon — a single bug amplifies into persistent
failure. Going stateless would break the loop but destroy the assistant.
His solution keeps both: after the code fix, the CONTENT is fixed too — the
poisoned message is rewritten to carry the truth (what was wrong, what the
fix did), so the same history that spread the disease now spreads the cure.
The fix isn't just deployed; it becomes part of the system's memory of
itself. This is the same epistemics the finds live by (history lines,
deaths-are-data) applied to the chat.

## 4. Testing by replaying the user's chat

The acceptance test is the user's own messages:
- Replay his EXACT phrasings (not developer phrasings — the gap between them
  is where every "it works" claim has died).
- Judge each reply against the logged tool results: every number must trace
  to a result; a reply with no tools behind it must say so itself.
- A/B replays root-cause behavior: same message over a clean vs a poisoned
  history copy isolates what the model responds to.
- Approval flows are tested by simulating the approvals ('go', 'bank') and
  checking what got taught.
- **Test hygiene (hard rule)**: cleanups delete only ids the test created —
  taught edges and lessons are HIS data and live in the same tables.

## Why this works (the unique part)

The same channel is simultaneously: the product (a trading assistant), the
teaching interface (approvals become edges), the debugger (verbatim console),
and the test corpus (real usage replayed). There is no separate "dev mode" —
development pressure and usage pressure are the same pressure, so what gets
fixed is exactly what gets used.

**And it all rests on the atomic design** (creature doc §3): the system was
designed from atoms up — named, small, single-purpose units (one sense = one
table, one hand = one tool with one signature, one step = one edge, one lesson
= one row). Visibility is only possible because there are precise things to
see: a trace line can name the exact tool and args, a similarity score can
point at one edge, a failure can name one hand. A system designed as a blob
can be logged but not TRACED; this one can be traced because every behavior
decomposes to atoms that were designed before they were built.
