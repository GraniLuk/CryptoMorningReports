# Prompt & Data Expansion Plan

This document lists potential future data fields and incremental improvements for the analysis prompt without breaking current usage.

## Current Allowed Placeholders
- `news_feeded`
- `indicators_message`
- `price_data`

## Proposed Future Safe Additions (Placeholders)
Add these only when the pipeline can reliably supply them. Until then they must not appear in the active prompt strings.

| Placeholder | Description | Value Type | Minimal Source Requirement | Primary Use |
|-------------|------------|-----------|----------------------------|-------------|
| `{open_interest}` | 24h delta & current OI notes | string | Derivatives API | Detect conviction / leverage buildup |
| `{funding_rates}` | Current + trend (rising/falling) | string | Perp funding feed | Assess directional bias stress |
| `{liquidation_heatmap}` | Key liquidation cluster levels | string | Aggregated liq map provider | Spot squeeze zones |
| `{long_short_ratio}` | Ratio or skew | string | Exchange metrics | Crowd positioning |
| `{onchain_metrics}` | 24h active addresses, tx volume deltas | string | On‑chain provider (Glassnode etc.) | Fundamental confirmation |
| `{orderbook_snapshot}` | Top-of-book liquidity walls | string | Exchange depth snapshot | Entry timing / fakeout risk |
| `{volume_profile}` | VAH / VAL / POC | string | Derived from recent candles | Structural target & invalidation |
| `{dominance_metrics}` | BTC dominance; ETH/BTC ratio | string | Market data aggregator | Rotation context |
| `{event_calendar}` | Upcoming macro/crypto events | string | Calendar feed | Volatility scheduling |
| `{sentiment_inputs}` | Fear-Greed, social spikes | string | Sentiment API | Contrarian signals |
| `{current_positions}` | Existing user exposure | string | User portfolio state | Avoid correlated stacking |
| `{risk_budget}` | Fractional daily risk allocation | float/string | User config | Position sizing |
| `{account_equity}` | Account equity base currency | float | User config or brokerage | Concrete sizing |

## Integration Roadmap
1. Instrument data collectors (module per data family) returning normalized dicts.
2. Serialization layer: map raw dict → formatted string snippet.
3. Validation guard: drop placeholder insertion if field is empty; else include.
4. Add optional variant prompts referencing new placeholders; keep legacy stable.
5. Unit tests: ensure fallback to MISSING when omitted.

## JSON Output Validation
Later add a lightweight validator:
- Parses JSON section at end
- Ensures required keys: symbols_analyzed, chosen_primary_symbol, setups, scenarios, missing_data, notes
- Logs anomalies for iterative refinement.

## Risk Controls to Embed (Future)
- ATR-based dynamic stop distance suggestion
- Aggregated expected portfolio daily R if multiple setups
- Confidence scoring based on data completeness (e.g., completeness_ratio = present_fields / total_expected_fields)

## Non-Functional Enhancements
- Prompt length monitoring: warn if > X tokens before API call.
- Caching: reuse unchanged sections (e.g., static macro events) daily.

## Change Management
- Introduce new prompt constants with `_V2`, `_V3` suffix to allow A/B testing.
- Keep original names pointing to the currently “stable” version until migration complete.

---
This file is informational only and not imported by runtime code.
