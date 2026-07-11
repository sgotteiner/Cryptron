"""The TradingView hand: price data via the user's TradingView Desktop.

A CONDITIONAL hand (embodiment: it exists only while TV Desktop is open
with CDP enabled). Wraps the TradingViewMCP project's CLI — subprocess in,
JSON out. Useful where the CEX price hand is blind: TV lists many DEX
pairs, so gem coins may be visible here.
"""
import asyncio
import json
import os
import subprocess

CLI = os.environ.get("TV_CLI", r"C:\my_projects\TradingViewMCP\src\cli\index.js")
NOT_OPEN = ("TradingView Desktop is not open (or CDP is off). "
            "Ask the user to launch it, then retry.")


def _run(*args: str) -> dict:
    try:
        out = subprocess.run(["node", CLI, *args], capture_output=True,
                             text=True, timeout=60, encoding="utf-8")
        return json.loads(out.stdout)
    except json.JSONDecodeError:
        return {"success": False, "error": (out.stdout or out.stderr)[:200]}
    except Exception as e:
        return {"success": False, "error": f"{type(e).__name__}: {e}"}


def _cdp_down(res: dict) -> bool:
    return "CDP connection" in str(res.get("error", ""))


async def search(query: str) -> dict:
    """Find symbols on TV (incl. DEX pairs) — 'is this gem visible here?'"""
    res = await asyncio.to_thread(_run, "search", query)
    if _cdp_down(res):
        return {"error": NOT_OPEN}
    return res


async def fetch_ohlcv(symbol: str, timeframe: str = "60", bars: int = 200) -> dict:
    """Point the chart at symbol/timeframe, then read OHLCV bars."""
    res = await asyncio.to_thread(_run, "symbol", symbol)
    if _cdp_down(res):
        return {"error": NOT_OPEN}
    if not res.get("success", True):
        return {"error": f"couldn't set symbol {symbol}: {res.get('error')}"}
    await asyncio.to_thread(_run, "timeframe", timeframe)
    res = await asyncio.to_thread(_run, "ohlcv", "-n", str(min(bars, 500)))
    if not res.get("success", True):
        return {"error": res.get("error")}
    return res


if __name__ == "__main__":
    async def _demo():
        print(json.dumps(await search("BTCUSDT"), indent=1)[:400])
    asyncio.run(_demo())
