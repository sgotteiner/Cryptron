"""Testing organs: ways of trading a signal, applied to price history.

A signal has no universal score (creature doc §4) — "win" is only defined
relative to how you'd trade it. Each organ is one way of trading, registered
by name; experiments pick organs and parameters (atoms) per run.

All organs share one signature:
    organ(candles, entry_price, config) -> OrganResult
where candles are [ms_ts, open, high, low, close, volume] from the price hand,
starting at the signal moment.
"""
from dataclasses import dataclass, field

ORGANS: dict = {}

MS_PER_DAY = 86_400_000


@dataclass
class OrganResult:
    win: bool | None          # None = window not over yet (open)
    pnl_pct: float | None
    details: dict = field(default_factory=dict)


def organ(name: str):
    def register(fn):
        ORGANS[name] = fn
        return fn
    return register


def _window(candles: list, entry_ms: int, days: float) -> list:
    end = entry_ms + days * MS_PER_DAY
    return [c for c in candles if entry_ms <= c[0] < end]


@organ("peak_gain")
def peak_gain(candles: list, entry_price: float, config: dict) -> OrganResult:
    """Did price ever reach +min_gain_pct within timeframe_days?"""
    gain = config["min_gain_pct"]
    win_candles = _window(candles, candles[0][0], config["timeframe_days"])
    if not win_candles:
        return OrganResult(None, None, {"reason": "no candles in window"})
    peak = max(c[2] for c in win_candles)  # high
    peak_pct = (peak / entry_price - 1) * 100
    return OrganResult(peak_pct >= gain, round(peak_pct, 2),
                       {"peak_price": peak, "needed_pct": gain})


@organ("tp_vs_sl")
def tp_vs_sl(candles: list, entry_price: float, config: dict) -> OrganResult:
    """Walking the candles: did take-profit get hit before stop-loss?

    tp/sl come as prices (the signal's own levels) or as pcts of entry.
    Conservative on same-candle hits: counts as loss (assume SL swept first).
    """
    tp = config.get("tp_price") or entry_price * (1 + config["tp_pct"] / 100)
    sl = config.get("sl_price") or entry_price * (1 - config["sl_pct"] / 100)
    win_candles = _window(candles, candles[0][0], config.get("timeframe_days", 14))
    for c in win_candles:
        hit_tp, hit_sl = c[2] >= tp, c[3] <= sl
        if hit_sl:  # includes both-in-one-candle: conservative loss
            return OrganResult(False, round((sl / entry_price - 1) * 100, 2),
                               {"hit": "sl", "both_same_candle": hit_tp, "at": c[0]})
        if hit_tp:
            return OrganResult(True, round((tp / entry_price - 1) * 100, 2),
                               {"hit": "tp", "at": c[0]})
    if not win_candles:
        return OrganResult(None, None, {"reason": "no candles in window"})
    last_close = win_candles[-1][4]
    return OrganResult(False, round((last_close / entry_price - 1) * 100, 2),
                       {"hit": "neither", "close": last_close})


@organ("hold_and_sell")
def hold_and_sell(candles: list, entry_price: float, config: dict) -> OrganResult:
    """Buy at signal, sell at close after hold_days. The moonshot-friendly exit."""
    win_candles = _window(candles, candles[0][0], config["hold_days"])
    if not win_candles:
        return OrganResult(None, None, {"reason": "no candles in window"})
    exit_price = win_candles[-1][4]
    pnl = (exit_price / entry_price - 1) * 100
    return OrganResult(pnl > 0, round(pnl, 2), {"exit_price": exit_price})
