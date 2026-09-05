"""Provider-agnostic LLM insight layer.

The LLM receives only pre-computed statistics and optional user context. It is
not allowed to calculate metrics or inspect raw rows.
"""

from __future__ import annotations

import json
import os
from typing import Any, Callable

Primitive = str | int | float | bool | None
StatsValue = Primitive | list["StatsValue"] | dict[str, "StatsValue"]

DEFAULT_MODELS = {
    "claude": "claude-sonnet-4-6",
    "gemini": "gemini-3.7-flash",
    "openai": "gpt-5.6-terra",
    # Verify the current model slug on Together AI's model catalog before relying on it.
    "llama": "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8",
}

MAX_OUTPUT_TOKENS = 900


def generate_insight(
    stats: dict[str, Any],
    context: str | None = None,
    provider: str = "claude",
    model: str | None = None,
) -> str:
    """Generate a plain-English narrative insight with a selected LLM provider.

    Returns a clear error string instead of raising provider/API failures, so a
    future web request can fail gracefully.
    """
    normalized_provider = provider.strip().lower()
    call_provider = _PROVIDER_CALLS.get(normalized_provider)
    if call_provider is None:
        available = ", ".join(sorted(_PROVIDER_CALLS))
        return f"Insight generation failed: unsupported provider '{provider}'. Available: {available}."

    try:
        safe_stats = _sanitize_stats(stats)
        safe_context = _sanitize_context(context)
        return call_provider(safe_stats, safe_context, model)
    except Exception as exc:  # Provider SDKs raise their own exception classes.
        return f"Insight generation failed for provider '{normalized_provider}': {exc}"


def build_insight_prompt(stats: dict[str, StatsValue], context: str | None = None) -> str:
    """Build the user-facing prompt shared by all model providers."""
    stats_json = json.dumps(stats, indent=2, sort_keys=True)
    context_block = context.strip() if context else "No additional user context was provided."

    return (
        "You are explaining a deterministic business analytics result.\n\n"
        "Rules:\n"
        "- Use only the statistics JSON below and the optional user context.\n"
        "- Do not recalculate, derive, or invent any number.\n"
        "- If a metric is null, say it is unavailable or undefined.\n"
        "- Treat cause/effect explanations as possible explanations, not certainties.\n"
        "- Do not claim investment advice or guaranteed market prediction.\n"
        "- Write for a business user who wants clear, decision-useful insight.\n\n"
        "Return this structure:\n"
        "1. A short summary paragraph.\n"
        "2. 3-5 key findings as bullets.\n"
        "3. Any data-quality warnings or limitations.\n"
        "4. Suggested next analytical steps.\n\n"
        f"Statistics JSON:\n{stats_json}\n\n"
        f"Optional user context:\n{context_block}"
    )


def _call_claude(stats: dict[str, StatsValue], context: str | None, model: str | None) -> str:
    api_key = _required_env("ANTHROPIC_API_KEY")
    selected_model = model or os.getenv("ANTHROPIC_MODEL") or DEFAULT_MODELS["claude"]
    prompt = build_insight_prompt(stats, context)

    try:
        from anthropic import Anthropic
    except ImportError as exc:
        raise RuntimeError("Install the 'anthropic' package to use Claude.") from exc

    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model=selected_model,
        max_tokens=MAX_OUTPUT_TOKENS,
        system=_system_prompt(),
        messages=[{"role": "user", "content": prompt}],
    )
    return _extract_claude_text(response)


def _call_gemini(stats: dict[str, StatsValue], context: str | None, model: str | None) -> str:
    api_key = _required_env("GOOGLE_API_KEY")
    selected_model = model or os.getenv("GEMINI_MODEL") or DEFAULT_MODELS["gemini"]
    prompt = f"{_system_prompt()}\n\n{build_insight_prompt(stats, context)}"

    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError("Install the 'google-genai' package to use Gemini.") from exc

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=selected_model,
        contents=prompt,
    )
    if not getattr(response, "text", None):
        raise RuntimeError("Gemini returned an empty response.")
    return response.text


def _call_openai(stats: dict[str, StatsValue], context: str | None, model: str | None) -> str:
    api_key = _required_env("OPENAI_API_KEY")
    selected_model = model or os.getenv("OPENAI_MODEL") or DEFAULT_MODELS["openai"]

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("Install the 'openai' package to use OpenAI models.") from exc

    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model=selected_model,
        max_output_tokens=MAX_OUTPUT_TOKENS,
        input=[
            {"role": "system", "content": _system_prompt()},
            {"role": "user", "content": build_insight_prompt(stats, context)},
        ],
    )
    if not getattr(response, "output_text", None):
        raise RuntimeError("OpenAI returned an empty response.")
    return response.output_text


def _call_llama(stats: dict[str, StatsValue], context: str | None, model: str | None) -> str:
    """Calls Llama via a hosted inference API (Together AI) — no self-hosted weights.

    Uses Together AI's OpenAI-compatible chat completions endpoint, so the
    'openai' Python package's client can point at Together's base_url instead
    of needing a separate SDK dependency.
    """
    api_key = _required_env("TOGETHER_API_KEY")
    selected_model = model or os.getenv("LLAMA_MODEL") or DEFAULT_MODELS["llama"]

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "Install the 'openai' package to use Llama via Together AI's "
            "OpenAI-compatible endpoint."
        ) from exc

    client = OpenAI(api_key=api_key, base_url="https://api.together.xyz/v1")
    response = client.chat.completions.create(
        model=selected_model,
        max_tokens=MAX_OUTPUT_TOKENS,
        messages=[
            {"role": "system", "content": _system_prompt()},
            {"role": "user", "content": build_insight_prompt(stats, context)},
        ],
    )
    choices = getattr(response, "choices", None)
    if not choices or not getattr(choices[0].message, "content", None):
        raise RuntimeError("Llama (via Together AI) returned an empty response.")
    return choices[0].message.content


def _system_prompt() -> str:
    return (
        "You are the narrative layer for an analytics AI platform. "
        "The Python analytics engine is the only source of numerical truth. "
        "Your job is to explain computed statistics clearly, never to calculate them."
    )


def _sanitize_stats(stats: dict[str, Any]) -> dict[str, StatsValue]:
    if not isinstance(stats, dict):
        raise ValueError("stats must be a dictionary of pre-computed values.")
    return {str(key): _sanitize_value(value, path=str(key)) for key, value in stats.items()}


def _sanitize_value(value: Any, path: str) -> StatsValue:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [_sanitize_value(item, path=f"{path}[]") for item in value]
    if isinstance(value, tuple):
        return [_sanitize_value(item, path=f"{path}[]") for item in value]
    if isinstance(value, dict):
        return {str(key): _sanitize_value(item, path=f"{path}.{key}") for key, item in value.items()}

    raise ValueError(
        f"stats contains unsupported raw-data value at '{path}' "
        f"({type(value).__name__}). Pass summarize_as_dict() output instead."
    )


def _sanitize_context(context: str | None) -> str | None:
    if context is None:
        return None
    if not isinstance(context, str):
        raise ValueError("context must be a string when provided.")
    return context.strip()[:2000]


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _extract_claude_text(response: Any) -> str:
    text_parts: list[str] = []
    for block in getattr(response, "content", []):
        text = getattr(block, "text", None)
        if text:
            text_parts.append(text)
    if not text_parts:
        raise RuntimeError("Claude returned an empty response.")
    return "\n".join(text_parts)


ProviderCall = Callable[[dict[str, StatsValue], str | None, str | None], str]

_PROVIDER_CALLS: dict[str, ProviderCall] = {
    "claude": _call_claude,
    "gemini": _call_gemini,
    "openai": _call_openai,
    "llama": _call_llama,
}


if __name__ == "__main__":
    sample_stats = {
        "value_column": "Revenue",
        "row_count": 10,
        "mean": 1736.0,
        "median": 1375.0,
        "std_dev": 1220.68,
        "growth_rate_pct": 25.0,
        "volatility": 99.58,
        "anomaly_count": 1,
        "recommended_chart_type": "line",
    }

    configured_provider = "claude"
    if os.getenv("ANTHROPIC_API_KEY"):
        configured_provider = "claude"
    elif os.getenv("GOOGLE_API_KEY"):
        configured_provider = "gemini"
    elif os.getenv("OPENAI_API_KEY"):
        configured_provider = "openai"
    elif os.getenv("TOGETHER_API_KEY"):
        configured_provider = "llama"

    print(generate_insight(sample_stats, provider=configured_provider))