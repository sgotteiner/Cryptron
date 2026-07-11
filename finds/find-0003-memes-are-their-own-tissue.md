---
id: find-0003
kind: conclusion
scope: {level: tissue, domain: '*', class: meme}
statement: >
  Memes are their own tissue: tight TP/SL exits die to their volatility, and the rare
  moonshot must be left room to pay for the many losers.
mechanism: >
  No fundamentals, thin books, reflexive crowds — meme price paths are violent both
  ways. A tight stop converts normal noise into a realized loss; a tight take-profit
  cages the one winner that funds the strategy.
directive:
  prefer:
    - exit: hold_and_let_run_or_trailing
  avoid:
    - exit: tight_tp_sl
confidence: 0.7
status: active
provenance: user
evidence:
  supporting: [exp-0001]
  contradicting: []
history:
  - "2026-07-11: born — seeded from the user's playbook (guidance #1) + exp-0001"
links: ["[[find-0002-class-decides-the-playbook]]", "[[find-0004-attention-is-the-memes-fundamental]]", "[[find-0008-sangitagem-moves-real-exits-missing]]"]
---
exp-0001 (sangitagem, n=16, in-sample): 69% of calls touched +20% within 14d (avg peak
+45.6%) yet tp_vs_sl won only 38% — the moves are there, tight exits lose them.

What would kill it: a meme sample where tight TP/SL beats letting winners run after
market adjustment; or evidence that "meme" is not a coherent class at all.
