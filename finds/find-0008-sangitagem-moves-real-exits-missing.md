---
id: find-0008
kind: conclusion
scope: {level: tissue, domain: telegram-signals, target: sangitagem, class: meme}
statement: >
  sangitagem's pushed calls (>=3 mentions) move for real — 69% touched +20% within 14d,
  avg peak +45.6% — but no tested exit captures it: the alpha exists, the harvest is unsolved.
mechanism: >
  Consistent with memes-are-their-own-tissue: the moves are violent and transient, so
  fixed exits either get stopped by noise (tight TP/SL: 38% winrate) or give the move
  back (7d hold: -0.9% avg). The missing piece is an exit that trails or scales out.
directive:
  prefer:
    - next_experiment: {exit: trailing_or_scale_out, untested: true}
  avoid:
    - exit: tight_tp_sl
    - exit: fixed_day_hold
confidence: 0.4
status: candidate
provenance: brain
evidence:
  supporting: [exp-0001, exp-0002]
  contradicting: []
history:
  - "2026-07-11: born — from exp-0001 (n=16, in-sample, not market-adjusted) + exp-0002 (HMSTR single case)"
links: ["[[find-0003-memes-are-their-own-tissue]]", "[[find-0005-leading-not-coincident]]", "[[find-0006-no-universal-score]]"]
---
The first earned find — and deliberately still a candidate: evidence is in-sample, small
(n=16), not market-adjusted, and peak_gain is hindsight-only. Promotion requires an
out-of-sample, market-adjusted experiment (the immune system enforces this).

What would kill it: an OOS window where the peaks vanish; or market adjustment showing
the "moves" were just beta on green days. What would promote it: a trailing/scale-out
organ beating the market OOS on this group's calls.

Open questions: does trend_before separate winners from losers here (find-0005)?
Is >=3 mentions the right push threshold, or an untuned atom?
