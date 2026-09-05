# Analytics AI Platform - Build Roadmap

This project is an analytics/insight engine, not a chatbot and not a generative-content tool.

The core rule is simple:

> Python computes the numbers. The LLM explains the already-computed numbers.

That means pandas/numpy are the source of truth for statistics, charts are generated from deterministic outputs, and Claude/OpenAI or another pre-trained model is used only for plain-English narrative summaries.

## Product Direction

The platform will become a paid SaaS product for business analytics.

- Manual CSV/Excel upload comes first.
- Company database connectors come later.
- Shopify and other business integrations come after the core is stable.
- Market/stock analytics is an add-on, framed as historical pattern and risk analysis, not guaranteed prediction.
- Free/open-source access can exist for the basic local engine, but the hosted business product should be paid.

## Phase 0 - Environment Setup

Goal: make the project easy to run locally.

Steps:

1. Use Python 3.11+.
2. Create a virtual environment.
3. Install dependencies from `requirements.txt`.
4. Run the core engine against a sample dataset.
5. Put the project in Git version control.

Done when:

- You can run the test/demo commands locally.
- The core package imports without errors.

## Phase 1 - Core Statistical Engine

Goal: create the deterministic source of truth for all calculations.

Current status: started.

The engine computes:

- mean
- median
- meaningful mode
- standard deviation
- variance
- min/max
- total
- growth rate
- period-over-period percent change
- volatility
- z-score anomaly detection

Done when:

- The engine works on at least three datasets: sales, market/stock, and categorical/business data.
- Edge cases are handled safely: empty data, single-row data, duplicate rows, missing values, first value equals zero.
- Tests cover the calculation rules.

## Phase 1.5 - Data Contract And Profiling

Goal: keep the engine data-source agnostic.

Every data source must become the same internal contract:

```python
DatasetInput(
    dataframe=df,
    source_type="csv | excel | database | shopify | market_api",
    value_column="Revenue",
    date_column="Date",
    category_column="Product",
    metadata={}
)
```

Why this matters:

- CSV upload is only the first input method.
- Company databases, Shopify, and stock APIs should all feed the same engine.
- The LLM never sees raw data by default. It receives the summary payload.

Done when:

- `analyze_dataframe()` is the main engine function.
- `analyze_dataset()` is only a file-loading wrapper.
- The output includes data-quality warnings.

## Phase 2 - Charting Layer

Goal: automatically choose and generate the correct chart.

Rules:

- Date/time + numeric value -> line chart.
- Category + numeric value -> bar chart.
- One numeric distribution -> histogram.
- Anomalies should be highlighted where useful.

Done when:

- `generate_chart(result, chart_type="auto")` returns a Plotly figure.
- The chart visually matches the computed stats.

## Phase 3 - AI Insight Layer

Goal: use a pre-trained LLM for narrative explanation only.

Current status: provider-agnostic base module started.

Important:

- Do not train a model from scratch for the first version.
- Use Claude/OpenAI or another pre-trained model through an API.
- The model receives only numbers, warnings, and metadata from `summarize_as_dict()`.
- The model must not calculate or invent metrics.

Done when:

- The summary accurately explains computed stats.
- No hallucinated numbers appear in the narrative.
- The app can swap between models later for different paid tiers.
- Provider routing works for Claude, Gemini, and OpenAI through one internal interface.

## Phase 4 - Local App / Web MVP

Goal: let a real user upload data and see results.

Backend:

- FastAPI.
- Upload endpoint.
- Analysis endpoint.
- Result retrieval endpoint.

Frontend:

- Start simple.
- A web dashboard can come before a mobile/desktop app.
- The first screen should let users upload data, run analysis, view charts, and read the summary.

Done when:

- A stranger can use the browser UI without you explaining it.

## Phase 5 - Company Database Connector

Goal: support installed business environments.

Architecture:

- A read-only connector runs inside or near the company's environment.
- Admins choose which tables/views the platform can access.
- The connector converts database results into `DatasetInput`.
- Credentials must be encrypted and never sent to the LLM.

Done when:

- A local database table can be analyzed without changing the core engine.

## Phase 6 - Shopify Integration

Goal: pull business sales/order data automatically.

Steps:

- Create a Shopify app.
- Implement OAuth.
- Pull order/sales data.
- Convert it into the standard data contract.
- Run the same Phase 1-3 pipeline.

Done when:

- A test Shopify store produces stats, charts, and insights automatically.

## Phase 7 - Market Analytics Add-On

Goal: add stock/market analytics as a paid add-on.

Use cases:

- OHLCV analysis.
- volatility
- moving averages
- RSI/MACD/Bollinger indicators later
- unusual-volume detection
- backtesting later
- plain-English market insight reports

Framing rule:

Call this historical pattern analysis and risk support, not guaranteed stock prediction.

Done when:

- A ticker's historical data produces accurate descriptive analysis.

## Phase 8 - Security And Reliability

Goal: make the product trustworthy for real business data.

Requirements:

- encrypted credentials
- read-only access by default
- no raw stack traces for users
- logging
- background jobs
- clear privacy policy and terms

Done when:

- The platform can run unattended without silent failures.

## Phase 9 - Paid SaaS Tiering

Goal: make this a real business, not just a demo.

Possible tiers:

- Individual
- Pro
- Business
- Enterprise

Gated features:

- usage limits
- model quality
- integrations
- export formats
- scheduled analysis
- team access
- private deployment

Done when:

- A user can hit a limit, upgrade, and unlock the feature server-side.

## Phase 10 - Real Users And Scale

Goal: learn from actual users and prepare for larger customers.

Steps:

- test with 10-20 users
- track confusion and retention
- improve weekly
- move to Postgres
- add requested integrations
- prepare enterprise/security requirements

Done when:

- Users return because the product saves them time or reveals useful business insight.

## Current Next Step

Finish Phase 1 and Phase 1.5 properly.

After that, build Phase 2 charting, then Phase 3 LLM summaries, then the FastAPI web MVP.
