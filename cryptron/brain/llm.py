"""LLM provider chain: Claude (the real brain) -> Gemini -> Groq -> OpenRouter.

Claude runs via the Claude Code CLI in headless print mode on the user's paid
plan (CLAUDE_CODE_OAUTH_TOKEN in .env, from `claude setup-token`). The free
chain survives only as a loudly-logged emergency fallback.

One function: complete(system, messages) -> text. Messages are
[{"role": "user"|"assistant", "content": str}, ...].
"""
import asyncio
import os

import httpx

from ..log import log

CLAUDE_MODEL = os.environ.get("CRYPTRON_CLAUDE_MODEL", "claude-sonnet-5")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")


async def _claude(system: str, messages: list) -> str:
    convo = "\n\n".join(f"[{m['role']}]\n{m['content']}" for m in messages)
    prompt = (f"{system}\n\n=== CONVERSATION SO FAR ===\n{convo}\n\n"
              "=== YOUR NEXT OUTPUT (one JSON object, per protocol) ===")
    # Clean env so inherited session vars can't hijack auth: the CLI then
    # authenticates from the machine's stored login (~/.claude/.credentials.json);
    # CLAUDE_CODE_OAUTH_TOKEN in .env is an optional override.
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("ANTHROPIC_", "CLAUDE_", "CLAUDECODE"))}
    token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN", "").strip()
    if token:
        env["CLAUDE_CODE_OAUTH_TOKEN"] = token
    proc = await asyncio.create_subprocess_exec(
        "claude", "-p", "--output-format", "text", "--model", CLAUDE_MODEL,
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE, env=env)
    out, err = await asyncio.wait_for(
        proc.communicate(prompt.encode("utf-8")), timeout=180)
    if proc.returncode != 0:
        raise RuntimeError(f"claude cli exit {proc.returncode}: "
                           f"{err.decode('utf-8', 'replace')[:200]}")
    return _nonempty(out.decode("utf-8", "replace").strip())


def _nonempty(text) -> str:
    """An empty/None completion is a provider FAILURE — fall to the next."""
    if not text or not str(text).strip():
        raise ValueError("empty completion")
    return text


async def _gemini(client, system: str, messages: list) -> str:
    key = os.environ["GEMINI_API_KEY"].strip()
    contents = [{"role": "model" if m["role"] == "assistant" else "user",
                 "parts": [{"text": m["content"]}]} for m in messages]
    r = await client.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent",
        params={"key": key},
        json={"systemInstruction": {"parts": [{"text": system}]}, "contents": contents},
    )
    r.raise_for_status()
    return _nonempty("".join(
        p.get("text", "") for p in r.json()["candidates"][0]["content"]["parts"]))


async def _openai_style(client, url: str, key: str, model: str,
                        system: str, messages: list) -> str:
    r = await client.post(
        url, headers={"Authorization": f"Bearer {key}"},
        json={"model": model,
              "messages": [{"role": "system", "content": system}] + messages},
    )
    r.raise_for_status()
    return _nonempty(r.json()["choices"][0]["message"]["content"])


async def complete(system: str, messages: list) -> str:
    """First success wins — and the winner is LOGGED: which model answered a
    turn is diagnosis-critical (a silent fallback is a different brain)."""
    errors = []
    try:
        text = await _claude(system, messages)
        log("llm", f"claude/{CLAUDE_MODEL}")
        return text
    except Exception as e:
        errors.append(f"claude: {e}")
    async with httpx.AsyncClient(timeout=90) as client:
        try:
            text = await _gemini(client, system, messages)
            log("llm", f"FALLBACK gemini/{GEMINI_MODEL} (claude: {str(errors[0])[:100]})")
            return text
        except Exception as e:
            errors.append(f"gemini: {e}")
        try:
            text = await _openai_style(
                client, "https://api.groq.com/openai/v1/chat/completions",
                os.environ["GROQ_API_KEY"].strip(), GROQ_MODEL, system, messages)
            log("llm", f"FALLBACK groq/{GROQ_MODEL} ({str(errors[-1])[:100]})")
            return text
        except Exception as e:
            errors.append(f"groq: {e}")
        try:
            model = os.environ.get("OPENROUTER_MODEL", "openrouter/auto")
            text = await _openai_style(
                client, "https://openrouter.ai/api/v1/chat/completions",
                os.environ["OPENROUTER_API_KEY"].strip(), model, system, messages)
            log("llm", f"FALLBACK openrouter/{model}")
            return text
        except Exception as e:
            errors.append(f"openrouter: {e}")
    raise RuntimeError("all LLM providers failed: " + " | ".join(errors))
