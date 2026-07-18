"""Per-chat working state (in-process): the rolling investigation context.

Everything a turn needs to be an ASSISTANT: what's been checked lately (all
paths append here — fast path included), the pending next-step suggestion
awaiting 'go', and the pending guide awaiting 'bank'.
"""
_S: dict = {}


def of(chat_id: str) -> dict:
    return _S.setdefault(chat_id, {"steps": [], "next": None, "bank": None,
                                   "task": "", "mark": 0})


def add_step(chat_id: str, tool: str, text: str, raw: str) -> None:
    s = of(chat_id)
    s["steps"].append({"tool": tool, "text": text, "raw": raw[:1200]})
    if len(s["steps"]) > 10:
        drop = len(s["steps"]) - 10
        s["steps"] = s["steps"][drop:]
        s["mark"] = max(0, s["mark"] - drop)


def task_steps(chat_id: str) -> list:
    """Steps belonging to the CURRENT task only (since its mark)."""
    s = of(chat_id)
    return s["steps"][s["mark"]:]


def set_task(chat_id: str, task: str) -> None:
    s = of(chat_id)
    s["task"] = task
    s["mark"] = len(s["steps"])
