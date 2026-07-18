"""The learning reflex as its OWN cognitive act — guide once, banked always.

Banking lessons was a side-duty buried in the main prompt, and side-duties
get dropped under load. A single-purpose call with one tiny prompt is
reliable where a mega-prompt is not: the main loop answers the user; this
reflex ONLY asks "did he just teach me something durable?" Every user turn
runs it; dedupe in save_guidance keeps the playbook one-truth-per-lesson.
"""
import json

from ..log import log
from . import llm

PROMPT = """You extract durable investigation lessons from a user's message to \
his crypto research bot.
A LESSON is a general rule about HOW to investigate or evaluate: a check to \
always run, a comparison method, a workflow principle — something that must \
apply to every future investigation, stated generally.
NOT a lesson: a question asking for data/numbers, a one-off request, praise or \
frustration with no rule in it, anything true of only one specific coin.
Reply with ONE JSON object and nothing else:
{"lesson": "<the general rule>", "why": "<the reason behind it>"}
or, if the message contains no durable lesson:
{"lesson": null}"""


async def detect(user_text: str) -> dict | None:
    """Detect a durable lesson — NEVER banks (his rule: he approves with
    'bank'). Returns {"lesson", "why"} or None."""
    try:
        raw = (await llm.complete(
            PROMPT, [{"role": "user", "content": user_text}])).strip()
        obj = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
    except Exception as e:
        log("reflex-err", f"{type(e).__name__}: {e}")
        return None
    if not obj.get("lesson"):
        return None
    log("reflex", f"detected: {obj['lesson'][:100]}")
    return {"lesson": obj["lesson"], "why": obj.get("why", "")}
