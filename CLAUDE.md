# Cryptron — working rules for Claude

## THE GOVERNING RULE: he designs, Claude implements (absolute, 2026-07-18)

Only the user designs this system. Never invent features, mechanisms, or "solutions"
to problems he raises. When he describes a problem or asks a question, the deliverable
is the diagnosis/answer — then STOP and let him decide what to build. Code only what
he designed or explicitly asked for. If he asks to consult, present options — and
still write NO code until he approves a specific one. (Rule triggered by: uninvited
history-wrapping/quarantine features built while he was only asking questions.)

## First: stand in the user's shoes

Before any work, understand WHY this system exists. His problem: **his reasoning
works but starves.** He can evaluate a crypto opportunity as well as anyone — but he
cannot watch every source 24/7 (coverage), cannot retain everything he sees (memory),
cannot hold it all in his head to compare (processing). There are many signals; he
must somehow decide **which are worth following** — gems for low-risk swing trades
(~a month, a few x). Every check he'd want to run exists; there are just far too many.

So Cryptron: an investigator that runs HIS evaluation methodology over everything,
builds a knowledge base of outcomes + background, compares, commits to verdicts he
can correct, and eventually finds good opportunities on its own — saving his time and
extending his limited memory and capability. Full vision: `docs/brain_design.md` §1–3;
concept: `docs/cryptron_creature.md`; memory: `docs/memory_design.md`. **Docs are
authoritative — reconcile them (and `brain/prompt.py`) in the same edit when concepts
move.**

Follow the vision, not just the instruction: when he asks for something, ask what
problem of HIS it solves before deciding how to build it.

## Division of labor (he corrected this — keep it exact)

- **Claude builds the body**: hands that return comparable numbers, memory that saves
  and retrieves them, a brain wired to analyze them. Verify a hand returns numbers,
  then stop.
- **Cryptron does the research** — comparisons, conclusions, verdicts — guided by the
  user in the Telegram chat. Never do the analysis for him in the build session.
- He teaches through corrections; bank them (auto-memory / this file / the docs) so he
  only has to say things once. We are learning each other — his feedback here is the
  same ask-once contract Cryptron lives by.

## Cleaning methodology (his rule, stated 2026-07-17)

- **Patch or design?** Before building a feature, ask if it's a patch or something
  deeper. If deeper — develop it properly (own module, right table, right contract),
  don't bolt it on.
- **After several patches, cleanup is needed.** Bloat accumulates in prompts, docs,
  playbooks, and code alike; refactoring the prompt while adding rules was the model
  case. When touching a file that has absorbed patches, leave it reorganized, not
  longer.
- Keep the codebase **clean, flexible, easy to extend, maintainable**: separation of
  concerns, files ≤150 lines (split when bigger), one module = one role (sense /
  hand / brain tool / memory layer). Adding a hand must stay: one module + one table +
  one prompt line + one dispatch line.
- Same economy in memory: don't save trash — one truth per lesson, retire stale notes,
  no two truths anywhere (code, docs, vault, playbook).

## The log-fix workflow (his design, 2026-07-18)

When he says "look at the logs and fix": (1) diagnose from `logs/cryptron.log`,
(2) fix the bug, (3) then CLEAN THE CHAT — edit the hallucinated/broken messages in
`sense_chat` to state what the fix did (or delete them if he says so). The edited
message is his visible proof the fix landed. Fabricated turns stay marked
`fabricated: true` so they never re-enter the model's history window.

## Practical

- Free/keyless data sources preferred; no paid dependencies (Firecrawl dropped,
  CryptoPanic dead — see vault note for the source decisions).
- The bot runs via `python -m cryptron.brain.chat`; senses capture via
  `python -m cryptron`. Restart the bot after changing brain/prompt code.
- After meaningful work: update the vault project note's State section
  (`C:\my_projects\Vault\Projects\Cryptron\Project.md`) and commit (style: one poetic
  line, like the log).
