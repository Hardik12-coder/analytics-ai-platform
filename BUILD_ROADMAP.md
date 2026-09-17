# Analytics AI Platform — Build Roadmap

This is a step-by-step algorithm for building the platform, broken into phases.
Each phase has a clear "done" condition before moving to the next one — don't
skip ahead, since later phases depend on earlier ones being solid.

---

## Current Build Status

Built so far:

- Phase 1 deterministic statistics engine
- Phase 1.5 data-source-agnostic input contract and profiling
- Phase 2 chart recommendation plus Plotly-compatible chart JSON
- Phase 2.5 deterministic sales/business metrics
- Phase 4 backend foundation with a no-LLM `/analyze` pipeline
- Phase 3 provider-agnostic LLM wrapper exists, but it is not wired into the backend yet

Current rule:

> Keep building deterministic analysis first. Do not let the LLM calculate anything.

---

## PHASE 0 — Environment Setup (Day 1)

1. Install Python 3.11+, set up a virtual environment (`python -m venv venv`)
2. Install core libraries: `pip install pandas numpy matplotlib plotly fastapi uvicorn python-multipart anthropic openai google-genai together`
3. Set up a GitHub repo — even solo, version control matters once Codex/AI tools are writing code alongside you, so you can always roll back
4. Decide your project structure now (see "Project Structure" section below)

**Done when:** you can run `python core_engine.py sample.csv Revenue Date` and get output.

---

## PHASE 1 — Core Statistical Engine (Week 1) ✅ started

Algorithm:
1. `load_dataset(filepath)` → read CSV/Excel, clean column names, parse dates
2. `analyze_dataset(...)` → compute mean, median, mode, std dev, variance, growth rate,
   period-over-period % change, volatility (std dev of % changes), z-score anomaly detection
3. `summarize_as_dict(...)` → strip down to primitives only (this is what gets handed to the AI layer later — never raw data)

**Critical rule:** all math happens in `pandas`/`numpy`, never inside an LLM prompt.
LLMs are unreliable at precise arithmetic — they interpret numbers, they don't compute them.

**Done when:** engine correctly analyzes at least 3 different real/sample datasets
(sales data, stock price data, a categorical dataset) without errors, and anomaly
detection flags things a human would agree are actually anomalies.

---

## PHASE 2 — Charting Layer (Week 1-2)

Algorithm:
1. Given a `cleaned_df` and `value_column`, auto-detect chart type:
   - Time-series data (has a date column) → line chart
   - Categorical comparison (e.g. sales by product) → bar chart
   - Distribution analysis → histogram
2. Use `plotly` (not matplotlib) — plotly charts are interactive and export to JSON,
   which makes them easy to send to a web frontend later
3. Auto-highlight anomalies on the chart (different color/marker for flagged points)
4. Function signature to build: `generate_chart(analysis_result, chart_type="auto") -> plotly.Figure`

**Done when:** you can feed the Phase 1 output into this and get a chart that visually
matches what the stats say (e.g. the anomaly point is visibly different).

---

## PHASE 2.5 — Sales Metrics Engine ✅ started

Goal: compute business-specific sales facts before any LLM sees the result.

Algorithm:
1. Accept a DataFrame plus column names:
   - `date_column`
   - `revenue_column`
   - `profit_column`
   - `units_column`
   - `category_column`
2. Compute:
   - total revenue
   - total profit
   - profit margin %
   - total units sold
   - average and median revenue per transaction
   - average and median monthly revenue
   - month-over-month revenue growth
   - best/worst month by revenue
   - best category/product by revenue
3. Return a primitive-only dictionary that can later be handed to the LLM.

**Done when:** sales metrics are tested and can be returned by the backend with no LLM calls.

---

## PHASE 3 — AI Insight / Narrative Layer (Week 2-3)

Algorithm:
1. Take the `summarize_as_dict()` output (numbers only) + optional user-provided context
   (e.g. "we ran a promotion March 10-15")
2. Construct a prompt for the LLM through the provider-agnostic insight layer that:
   - Gives it ONLY the computed numbers, never raw data or code
   - Explicitly instructs it to interpret, not calculate
   - Asks it to flag correlations with user-provided context as *possible* explanations,
     not certainties (this matters for honesty and for avoiding overclaiming to users)
3. Parse the LLM response into a clean summary paragraph + bullet list of notable findings

Supported first-stage providers:
- Claude
- Gemini
- OpenAI
- Hosted Llama through Together AI

Do not self-host Llama/open-weight model weights during the MVP. Use hosted inference first so the team can move quickly without GPU infrastructure.

**Prompt design principle:** the LLM should never see the CSV. It only ever sees the
dict of pre-computed stats. This guarantees numeric accuracy regardless of which
model you use, and makes swapping models later (e.g. upgrading tiers) trivial.

**Done when:** for a given dataset, the AI-generated summary accurately reflects
the computed stats and reads naturally, without hallucinated numbers.
Provider routing should work through one interface: `generate_insight(stats, context, provider, model)`.

---

## PHASE 4 — Web Interface (Week 3-4)

Algorithm:
1. Build a FastAPI backend with endpoints:
   - `GET /health` → confirms the backend is alive
   - `POST /analyze` → accepts CSV/Excel, runs deterministic Phase 1, 2, and 2.5 pipeline, returns results
   - `GET /results/{result_id}` → retrieves a past analysis
2. Keep the first backend mode LLM-free:
   - return statistical summary
   - return sales metrics
   - return chart JSON
   - return `llm_enabled: false`
3. Build a minimal frontend (can start with Gradio for speed, or React/Next.js if
   you want production-grade from day one)
4. Flow: user uploads file → sees loading state → sees chart + stats + sales metrics
5. Store results temporarily (in-memory or a simple database like SQLite for now —
   Postgres later once you have real users)

**Done when:** a stranger can upload a CSV through a browser and get a working
result with zero explanation from you. LLM summaries can be added after the deterministic backend is stable.

---

## PHASE 5 — First Live Integration: Shopify (Week 5-7)

Algorithm:
1. Register a Shopify Partner account, create a development app
2. Implement OAuth flow: user clicks "Connect Shopify" → redirected to Shopify login
   → grants permission → your backend receives an access token → store it securely (encrypted)
3. Use Shopify's Admin API to pull order/sales data on a schedule (e.g. nightly sync)
4. Feed the pulled data through your existing Phase 1-3 pipeline unchanged —
   this is why building the engine data-source-agnostic in Phase 1 matters
5. Handle token refresh, API rate limits, and disconnection gracefully

**Done when:** a real Shopify test store's data flows in automatically and produces
the same quality of chart/stats/insight as a manual CSV upload did.

---

## PHASE 6 — Stock/Market Data Integration (Week 7-8)

Algorithm:
1. Sign up for a market data API (Alpha Vantage or Polygon.io have usable free tiers)
2. Build a connector that pulls OHLCV (open/high/low/close/volume) data for a
   user-specified ticker
3. Feed into the same Phase 1-3 pipeline — same stats, same chart engine
4. **Framing discipline:** label everything as "historical pattern analysis" —
   volatility, deviation, trend — never as price prediction. This is both an
   honesty requirement and a legal-risk-reduction one (investment prediction
   claims carry real regulatory exposure).

**Done when:** a ticker's historical data produces accurate stats/volatility
analysis, clearly labeled as descriptive (what happened) not predictive (what will happen).

---

## PHASE 7 — Security & Reliability (Week 8-10)

Algorithm:
1. Encrypt all stored credentials/tokens at rest
2. Add error handling for every external API call (Shopify down, malformed CSV, etc.)
   — the user should never see a raw stack trace
3. Add background job scheduling (e.g. `celery` or `APScheduler`) for automatic
   data refresh, so connected accounts stay current without manual re-upload
4. Write a real privacy policy and terms of service before handling anyone's real
   business data — a template from a service like Termly is a reasonable starting
   point, but have it reviewed once you have paying customers
5. Basic logging/monitoring so you know when something breaks before a user tells you

**Done when:** the platform runs unattended for a week without silent failures.

---

## PHASE 8 — Tiering & Access Control (Week 10-11)

Algorithm:
1. Add user accounts + authentication (e.g. `fastapi-users` or Clerk/Auth0 for speed)
2. Add a `tier` field per user: `free`, `pro`, `business`
3. Gate features by tier in the backend (not just the frontend — always enforce
   server-side): usage caps, which model powers the insight layer, which
   integrations are available, export formats
4. Integrate a payments provider (Stripe is the standard choice) for subscription billing

**Done when:** you can sign up as free, hit a usage cap, upgrade, and get access
to gated features — the whole loop works end to end.

---

## PHASE 9 — Real User Testing & Iteration (Week 11-16)

Algorithm:
1. Get 10-20 real users (from your earlier validation conversations) onto the
   platform with their real data
2. Track: do they come back? Where do they get confused? What do they ask for
   that you don't have?
3. Iterate weekly based on this feedback — this phase reshapes the product more
   than any planning did

**Done when:** you have real retention data and testimonials you can point to.

---

## PHASE 10 — Scale Prep (Month 4+)

Algorithm:
1. Move from SQLite to Postgres if you haven't already
2. Add more integrations based on actual user requests (QuickBooks, Square, etc.)
3. Consider SOC 2 compliance process if enterprise customers require it
4. Prepare fundraising materials using real metrics from Phase 9

---

## Project Structure (set this up in Phase 0)

```
analytics-ai-platform/
├── core/
│   ├── core_engine.py       # Phase 1 - stats engine (data-source agnostic)
│   ├── sales_engine.py      # Phase 2.5 - sales/business metrics
│   ├── charting.py          # Phase 2 - chart generation
│   └── insight.py           # Phase 3 - LLM narrative layer
├── integrations/
│   ├── shopify_connector.py # Phase 5
│   └── market_data.py       # Phase 6
├── api/
│   ├── analysis_pipeline.py  # no-LLM deterministic pipeline
│   ├── main.py               # FastAPI app, routes
│   └── auth.py                # Phase 8 - user accounts, tiering
├── frontend/                  # Phase 4
├── tests/
└── BUILD_ROADMAP.md           # this file
```

Keeping `core/` completely independent of *where* data comes from is the single
most important architectural decision — it's what lets Shopify data, a manual CSV,
and stock market data all flow through the identical, already-tested stats and
insight pipeline.

---

## Realistic Time Expectations

Given you already know Python and are pairing with AI coding tools:
- Phases 0-4 (working MVP with manual upload): **3-4 weeks**, not months
- Phase 5-6 (first two live integrations): **another 3-4 weeks**
- Phases 7-10: **stretches over the rest of the year**, driven by real usage
  and feedback rather than a fixed calendar

Use AI coding tools to accelerate implementation of each phase, but review and
understand every piece of the core engine (Phase 1) and insight layer (Phase 3)
yourself — those are the parts your entire product's credibility rests on.
