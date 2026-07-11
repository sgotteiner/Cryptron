"""LLM provider chain: Gemini -> Groq -> OpenRouter. First success wins.

One function: complete(system, messages) -> text. Messages are
[{"role": "user"|"assistant", "content": str}, ...].
"""
import os

import httpx

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")


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
    return "".join(p.get("text", "") for p in r.json()["candidates"][0]["content"]["parts"])


async def _openai_style(client, url: str, key: str, model: str,
                        system: str, messages: list) -> str:
    r = await client.post(
        url, headers={"Authorization": f"Bearer {key}"},
        json={"model": model,
              "messages": [{"role": "system", "content": system}] + messages},
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


async def complete(system: str, messages: list) -> str:
    errors = []
    async with httpx.AsyncClient(timeout=90) as client:
        try:
            return await _gemini(client, system, messages)
        except Exception as e:
            errors.append(f"gemini: {e}")
        try:
            return await _openai_style(
                client, "https://api.groq.com/openai/v1/chat/completions",
                os.environ["GROQ_API_KEY"].strip(), GROQ_MODEL, system, messages)
        except Exception as e:
            errors.append(f"groq: {e}")
        try:
            return await _openai_style(
                client, "https://openrouter.ai/api/v1/chat/completions",
                os.environ["OPENROUTER_API_KEY"].strip(),
                os.environ.get("OPENROUTER_MODEL", "openrouter/auto"), system, messages)
        except Exception as e:
            errors.append(f"openrouter: {e}")
    raise RuntimeError("all LLM providers failed: " + " | ".join(errors))
