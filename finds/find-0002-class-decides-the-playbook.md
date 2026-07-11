---
id: find-0002
kind: conclusion
scope: {level: creature, domain: '*', class: '*'}
statement: >
  Before judging any coin or signal, classify the coin (large-cap / small-cap / meme):
  the class decides which playbook applies. No analysis before classification.
mechanism: >
  A $15M meme behaves nothing like a major: different volatility, different holders,
  different exits. One playbook across classes guarantees wrong exits somewhere.
directive:
  prefer:
    - classify_first: {by: [market_cap, age, sector], then: finds_in_scope}
  avoid:
    - one_playbook_for_all_classes: true
confidence: 0.8
status: active
provenance: user
evidence: {supporting: [], contradicting: []}
history:
  - "2026-07-11: born — seeded from the user's playbook (guidance #1)"
links: ["[[find-0003-memes-are-their-own-tissue]]", "[[find-0007-tradability-gate]]"]
---
Operationally: cmc_lookup for cap/rank → classify → finds_in_scope({class: ...}) before
the first experiment. Classes are DISCOVERED, not pre-listed — when a coin fits no known
class, that is a classification thread, not a forced fit.

What would kill it: evidence that one exit/entry policy dominates across all classes
(would collapse the class dimension of every scope).
