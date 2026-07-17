"""The learning reflex as its OWN cognitive act — guide once, banked always.

Banking lessons was a side-duty buried in the main prompt, and side-duties
get dropped under load. A single-purpose call with one tiny prompt is
reliable where a mega-prompt is not: the main loop answers the user; this
reflex ONLY asks "did he just teach me something durable?" Every user turn
runs it; dedupe in save_guidance keeps the playbook one-truth-per-lesson.
"""
import json

from ..log import log
from ..memory import paths
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


async def learn(conn, user_text: str) -> str | None:
    """Returns the lesson text if this message taught one (and it was new)."""
    try:
        raw = (await llm.complete(
            PROMPT, [{"role": "user", "content": user_text}])).strip()
        obj = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
    except Exception as e:
        log("reflex-err", f"{type(e).__name__}: {e}")
        return None
    lesson = obj.get("lesson")
    if not lesson:
        return None
    saved = paths.save_guidance(conn, lesson=lesson, why=obj.get("why", ""))
    if "learned" in saved:
        log("reflex", f"BANKED: {lesson}")
        return lesson
    log("reflex", f"already known: {lesson[:100]}")
    return None
