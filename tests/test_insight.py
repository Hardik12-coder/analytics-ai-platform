import pandas as pd

from core.insight import _PROVIDER_CALLS, build_insight_prompt, generate_insight


def test_build_insight_prompt_uses_stats_and_context_only():
    prompt = build_insight_prompt(
        {
            "mean": 100.0,
            "growth_rate_pct": 12.5,
            "anomaly_count": 1,
        },
        context="Promotion ran during week 2.",
    )

    assert "mean" in prompt
    assert "100.0" in prompt
    assert "Promotion ran during week 2." in prompt
    assert "Do not recalculate" in prompt
    assert "possible explanations" in prompt


def test_generate_insight_routes_to_selected_provider():
    original = _PROVIDER_CALLS["claude"]
    calls = {}

    def fake_provider(stats, context, model):
        calls["stats"] = stats
        calls["context"] = context
        calls["model"] = model
        return "Insight text"

    try:
        _PROVIDER_CALLS["claude"] = fake_provider

        result = generate_insight(
            {"mean": 100, "nested": {"anomaly_count": 1}},
            context="Known promotion period.",
            provider="claude",
            model="test-model",
        )
    finally:
        _PROVIDER_CALLS["claude"] = original

    assert result == "Insight text"
    assert calls["stats"]["mean"] == 100
    assert calls["context"] == "Known promotion period."
    assert calls["model"] == "test-model"


def test_generate_insight_routes_to_llama_provider():
    original = _PROVIDER_CALLS["llama"]
    calls = {}

    def fake_provider(stats, context, model):
        calls["stats"] = stats
        calls["context"] = context
        calls["model"] = model
        return "Hosted Llama insight"

    try:
        _PROVIDER_CALLS["llama"] = fake_provider

        result = generate_insight(
            {"mean": 250, "growth_rate_pct": 15.5},
            context="Holiday sale occurred.",
            provider="llama",
            model="meta-llama/test",
        )
    finally:
        _PROVIDER_CALLS["llama"] = original

    assert result == "Hosted Llama insight"
    assert calls["stats"]["growth_rate_pct"] == 15.5
    assert calls["context"] == "Holiday sale occurred."
    assert calls["model"] == "meta-llama/test"


def test_generate_insight_rejects_raw_dataframe_payloads():
    result = generate_insight(
        {"mean": 100, "raw_data": pd.DataFrame({"revenue": [100, 200]})},
        provider="claude",
    )

    assert "Insight generation failed" in result
    assert "unsupported raw-data value" in result


def test_generate_insight_handles_unknown_provider():
    result = generate_insight({"mean": 100}, provider="unknown")

    assert "unsupported provider" in result
    assert "claude" in result
    assert "gemini" in result
    assert "llama" in result
    assert "openai" in result
