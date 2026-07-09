"""Environment and targets configuration."""
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(
            f"Missing {name} in .env — copy .env.example to .env and fill it in."
        )
    return value


def database_url() -> str:
    return require("DATABASE_URL")


def telegram_credentials() -> tuple[int, str, str]:
    return (
        int(require("TELEGRAM_API_ID")),
        require("TELEGRAM_API_HASH"),
        require("TELEGRAM_PHONE_NUMBER"),
    )


def load_targets() -> dict:
    path = ROOT / "targets.yaml"
    if not path.exists():
        raise SystemExit("targets.yaml not found — copy targets.example.yaml and edit it.")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
