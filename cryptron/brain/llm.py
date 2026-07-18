"""LLM provider chain: Claude (the real brain) -> Gemini -> Groq -> OpenRouter.

Claude runs via the Claude Code CLI in headless print mode on the user's paid
plan (CLAUDE_CODE_OAUTH_TOKEN in .env, from `claude setup-token`). The free
chain survives only as a loudly-logged emergency fallback.

One function: complete(system, messages) -> text. Messages are
[{"role": "user"|"assistant", "content": str}, ...].
"""
import asyncio
import os
import tempfile
import time

import httpx

from ..log import log

CLAUDE_MODEL = os.environ.get("CRYPTRON_CLAUDE_MODEL", "claude-sonnet-5")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

_claude_cooldown_until = 0.0  # session-limit memory: don't re-knock a shut door


async def _claude(system: str, messages: list) -> str:
    """Cryptron's identity goes in as the REAL system prompt (--system-prompt-
    file) and the CLI's own tools are stripped (--tools "") — delivered as user
    text, the model rightly treats a persona as prompt injection and refuses."""
    global _claude_cooldown_until
    if time.time() < _claude_cooldown_until:
        raise RuntimeError("session limit cooldown "
                           f"({int(_claude_cooldown_until - time.time())}s left)")
    convo = "\n\n".join(f"[{m['role']}]\n{m['content']}" for m in messages)
    prompt = (f"=== CONVERSATION SO FAR ===\n{convo}\n\n"
              "=== YOUR NEXT OUTPUT (one JSON object, per protocol) ===")
    # Clean env so inherited session vars can't hijack auth: the CLI then
    # authenticates from the machine's stored login (~/.claude/.credentials.json);
    # CLAUDE_CODE_OAUTH_TOKEN in .env is an optional override.
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("ANTHROPIC_", "CLAUDE_", "CLAUDECODE"))}
    token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN", "").strip()
    if token:
        env["CLAUDE_CODE_OAUTH_TOKEN"] = token
    fd, sys_path = tempfile.mkstemp(suffix=".txt", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(system)
        # Neutral cwd + no MCP + no tools: the brain must see ZERO native
        # tools, or it checks its own tool list and refuses the harness ones.
        for attempt, wait in ((1, 15), (2, 45), (3, 0)):  # ride out throttle blips
            proc = await asyncio.create_subprocess_exec(
                "claude", "-p", "--output-format", "text", "--model", CLAUDE_MODEL,
                "--tools", "", "--strict-mcp-config", "--setting-sources", "",
                "--system-prompt-file", sys_path,
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE, env=env,
                cwd=tempfile.gettempdir())
            out, err = await asyncio.wait_for(
                proc.communicate(prompt.encode("utf-8")), timeout=180)
            if proc.returncode == 0:
                return _nonempty(out.decode("utf-8", "replace").strip())
            detail = (out or err).decode("utf-8", "replace").strip()[:150]
            log("llm", f"claude attempt {attempt} exit {proc.returncode}: {detail}")
            if "limit" in detail.lower():  # hard window: back off 10 min, no retry
                _claude_cooldown_until = time.time() + 600
                break
            if wait:
                await asyncio.sleep(wait)
    finally:
        os.unlink(sys_path)
    raise RuntimeError(f"claude cli failed after 3 attempts: {detail}")


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
