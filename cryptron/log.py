"""One logbook for everything the creature does.

Every user turn, LLM call (which provider answered), tool call with its args,
tool RESULT, tool FAILURE, reflex save — one line each, console + logs/
cryptron.log. Nothing the system does is invisible; every claim in a reply
is auditable against what the tools actually returned.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
_file = None

try:  # Windows consoles default to legacy codepages that choke on emoji
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def _sink():
    global _file
    if _file is None:
        LOG_DIR.mkdir(exist_ok=True)
        _file = open(LOG_DIR / "cryptron.log", "a", encoding="utf-8")
    return _file


def log(event: str, detail: str = "", trunc: int = 2000) -> None:
    ts = datetime.now(timezone.utc).strftime("%m-%d %H:%M:%S")
    line = f"{ts} | {event:<10} | {detail[:trunc]}"
    print(line, flush=True)
    f = _sink()
    f.write(line + "\n")
    f.flush()
