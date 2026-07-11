---
id: find-0007
kind: conclusion
scope: {level: creature, domain: '*', class: '*'}
statement: >
  Before believing any entry, check which exchanges actually list the coin. An unlisted
  coin can't be entered at quoted prices, and CEX listing is itself a liquidity/quality signal.
mechanism: >
  Analysis of an untradable coin is fiction: DEX-only gems have slippage, honeypots and
  phantom quotes. Listing breadth also proxies for scrutiny and real books.
directive:
  prefer:
    - pre_trade_check: {exchanges: true}
  avoid:
    - trusting: quoted-price-without-listing-check
confidence: 0.8
status: active
provenance: user
evidence: {supporting: [], contradicting: []}
history:
  - "2026-07-11: born — seeded from the user's playbook (guidance #2)"
links: ["[[find-0002-class-decides-the-playbook]]"]
---
Operationally: exchanges(coin) across binance/bybit/kucoin/gate/mexc/okx on every
evaluated signal. crypto_gemsignals coins are typically NOT CEX-priceable yet — the
gap itself is data (a listing later is an event worth studying).

What would kill it: a working DEX price/execution hand making DEX-only coins genuinely
tradable — the gate would then widen rather than die.
