---
id: find-0001
kind: conclusion
scope: {level: creature, domain: '*', class: '*'}
statement: >
  Every price move = market beta + coin alpha. A signal is only credited with what it
  earned OVER the market — absolute returns on a green day are self-deception.
mechanism: >
  The tide lifts all boats. Without subtracting the tide, every bull-market strategy
  looks brilliant and every bear-market strategy looks broken.
directive:
  prefer:
    - market_adjusted: true
  avoid:
    - scoring: absolute-returns
confidence: 0.8
status: active
provenance: user
evidence: {supporting: [], contradicting: []}
history:
  - "2026-07-11: born — seeded from the user's playbook (guidance #6)"
links: ["[[find-0006-no-universal-score]]"]
---
The null model of the whole system: before believing any pattern, ask what the market
(BTC / total cap) did over the same window. This is the condition that killed the naive
form of the attention hypothesis in the worked trace (memory_design.md §4).

What would kill it: nothing directly — it is methodology, not a market claim. It would
*narrow* only if a class is found whose beta to the market is ~0.
