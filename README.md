# Analytics AI Platform

A Python-first analytics AI platform for business data, sales records, and market data.

This is not a chatbot. It is an analytics engine that computes statistics deterministically and uses a pre-trained LLM only to explain the results in plain English.

## Core Principle

All calculations happen in Python:

- pandas
- numpy
- deterministic business logic

The LLM layer never performs calculations. It only receives already-computed numbers from the engine.

## Current Status

The first core foundation is started:

- data-source-agnostic input contract
- CSV/Excel ingestion wrapper
- deterministic statistics engine
- data-quality profiling
- anomaly detection
- chart recommendation
- LLM-safe summary payload
- provider-agnostic insight layer for Claude/Gemini/OpenAI
- focused tests

## Project Structure

```text
analytics-ai-platform/
├── core/
│   ├── contracts.py
│   ├── ingestion.py
│   ├── core_engine.py
│   ├── insight.py
│   └── charting.py
├── tests/
│   ├── fixtures/
│   │   └── sample_sales.csv
│   └── test_core_engine.py
├── BUILD_ROADMAP.md
├── README.md
├── .env.example
├── requirements.txt
└── pyproject.toml
```

## Setup

From the project folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run A Demo Analysis

```bash
python -m core.core_engine tests/fixtures/sample_sales.csv Revenue Date
```

## Run Tests

```bash
pytest
```

## Generate An AI Insight

Set at least one API key in your shell:

```bash
export ANTHROPIC_API_KEY="your_key_here"
```

Then run:

```bash
python -m core.insight
```

In application code, use:

```python
from core.insight import generate_insight

summary = generate_insight(stats_dict, provider="claude")
```

Supported providers are `claude`, `gemini`, and `openai`. The provider and model are parameters so paid tiers can use stronger models later without rewriting the app.

