"""Tool dispatch: name + args -> the one hand/memory function, fully logged.

The single registry of what the body can DO. call_tool is the only entry:
args in, result or FAILURE out — always visible in the logbook.
"""
import json

from ..hands import admin, background, dex, dex_price
from ..log import log
from ..memory import finds, paths, recall
from ..senses import coingecko
from . import inspect, outcomes, social, tools


async def run_tool(conn, name: str, args: dict) -> dict:
    try:
        if name == "sources":
            return tools.sources(conn)
        if name == "capabilities":
            return admin.capabilities(conn)
        if name == "graph":
            return await inspect.graph(conn, **args)
        if name == "trace":
            return inspect.trace(**args)
        if name == "add_source":
            return await admin.add_source(conn, **args)
        if name == "calls":
            return tools.calls(conn, **args)
        if name == "price_summary":
            return await tools.price_summary(**args)
        if name == "score":
            return await tools.score(conn, **args)
        if name == "sql":
            return tools.sql(conn, **args)
        if name == "cmc_lookup":
            return await tools.cmc_lookup(conn, **args)
        if name == "exchanges":
            return await tools.exchanges(**args)
        if name == "dex_search":
            return await dex.search(conn, **args)
        if name == "dex_price_summary":
            return await dex_price.price_summary(conn, **args)
        if name == "dex_trending":
            return await dex.trending(conn, **args)
        if name == "mentions":
            return social.mentions(conn, **args)
        if name == "sentiment":
            return await coingecko.lookup(conn, **args)
        if name == "fear_greed":
            return social.fear_greed(conn)
        if name == "tv_search":
            return await tools.tv_search(**args)
        if name == "tv_ohlcv":
            return await tools.tv_ohlcv(**args)
        if name == "save_guidance":
            return await paths.save_guidance(conn, **args)
        if name == "open_thread":
            return paths.open_thread(conn, **args)
        if name == "replay_thread":
            return paths.replay(conn, **args)
        if name == "capture_background":
            return await background.capture(conn, **args)
        if name == "label_calls":
            return await outcomes.label_calls(conn, **args)
        if name == "record_experiment":
            return await tools.record_experiment(conn, **args)
        if name == "save_find":
            return await finds.save_find(conn, **args)
        if name == "update_find":
            return await finds.update_find(conn, **args)
        if name == "recall":
            return await recall.recall(conn, **args)
        if name == "finds_in_scope":
            return recall.in_scope(conn, **args)
        if name == "read_find":
            return recall.read(conn, **args)
        return {"error": f"no such tool: {name}"}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


async def call_tool(conn, name: str, args: dict) -> dict:
    log("tool", f"{name} {json.dumps(args, default=str)}")
    result = await run_tool(conn, name, args)
    if isinstance(result, dict) and result.get("error"):
        log("TOOL-FAIL", f"{name}: {result['error']}")
    else:
        log("result", json.dumps(result, default=str)[:800])
    return result
