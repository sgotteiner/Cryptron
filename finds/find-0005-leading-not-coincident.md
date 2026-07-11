---
id: find-0005
kind: conclusion
scope: {level: molecule, domain: telegram-signals, class: '*'}
statement: >
  Check the price trend BEFORE a signal was posted, not just after. A coin that already
  pumped pre-signal may mean the caller front-ran it — the follower becomes exit liquidity.
mechanism: >
  A signal is information only if it LEADS the move. Coincident or lagging "calls" are
  advertising a position, not sharing an edge; entering on them buys someone's exit.
directive:
  prefer:
    - signal_check: {trend_before: true, must_lead_price: true}
  avoid:
    - entry_on: pre-pumped-calls
confidence: 0.7
status: active
provenance: user
evidence: {supporting: [], contradicting: []}
history:
  - "2026-07-11: born — seeded from the user's playbook (guidance #3)"
links: ["[[find-0004-attention-is-the-memes-fundamental]]", "[[find-0008-sangitagem-moves-real-exits-missing]]"]
---
Operationally: price_summary's days_before window exists for exactly this — read
trend_before on every signal evaluation, unprompted.

What would kill it: evidence in a group that pre-pumped calls still outperform the
market after the signal (a genuine momentum group rather than an exit-liquidity one).
