---
id: find-0006
kind: conclusion
scope: {level: creature, domain: '*', class: '*'}
statement: >
  A signal has no universal score: the same call wins under one exit and loses under
  another. "Is it tradable?" must be answered under MULTIPLE testing organs, never one number.
mechanism: >
  A score is a function of (signal, exit, window) — dropping the exit from the question
  smuggles in an arbitrary one. exp-0001 proved it on real data: identical calls scored
  0.69 / 0.38 / 0.44 under peak_gain / tp_vs_sl / hold_and_sell.
directive:
  prefer:
    - scoring: {organs: [peak_gain, tp_vs_sl, hold_and_sell], report: all}
  avoid:
    - scoring: single-number-verdict
confidence: 0.8
status: active
provenance: user
evidence:
  supporting: [exp-0001]
  contradicting: []
history:
  - "2026-07-11: born — seeded from the user's playbook (guidance #4) + exp-0001"
links: ["[[find-0001-market-is-the-null-model]]", "[[find-0008-sangitagem-moves-real-exits-missing]]"]
---
Corollary: peak_gain is hindsight-only (nobody sells the exact top) — it measures whether
moves EXIST, not whether they are harvestable. Always label it as such.

What would kill it: nothing directly — methodology. It would relax only if one exit
family provably dominates across classes and regimes (see find-0002's kill condition).
