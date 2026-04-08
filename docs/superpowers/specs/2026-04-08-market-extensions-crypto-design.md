# Unified Market Extensions And Crypto Support Design

**Date:** 2026-04-08

**Status:** Approved design, pending implementation plan

## Goal

Extend `TradingAgents-AShare` so it can analyze crypto spot instruments in the same upstream-compatible style as A-shares, while keeping Docker deployments self-contained and minimizing merge friction with `TauricResearch/TradingAgents`.

This design also generalizes the current single-market A-share seam into a shared market-extension layer, so future market-specific logic stays inside our own modules instead of spreading across upstream files.

## Constraints

- Docker must run independently.
- Core runtime must not depend on host-local tools such as `autocli`, `agent-reach`, or workspace scripts.
- Upstream graph and analyst structure should remain intact.
- Market-specific logic should live inside our own extension modules whenever possible.
- `social` remains optional. Users may deselect it.
- First version only supports crypto spot analysis.
- Public unauthenticated endpoints should be enough to run the default path.
- Optional API keys may improve resilience, but missing keys must not break the system.

## Scope

### In Scope

- Add a shared market-extension dispatcher usable by both A-share and crypto.
- Add `extensions/crypto` with market detection, normalization, policy, routing, and providers.
- Support crypto inputs such as `BTC`, `ETH`, `BTCUSDT`, `ETHUSDT`, `BTC-USD`, and `ETH-USD`.
- Route crypto market and indicator data primarily through Binance Spot public endpoints.
- Route crypto fundamentals primarily through CoinGecko.
- Add a low-confidence, optional crypto `social` path based on public web/news style sources.
- Preserve current A-share behavior through the new shared dispatcher.
- Add regression coverage for both A-share and crypto routing.

### Out Of Scope

- Order placement, account data, balances, positions, or any authenticated trading workflow.
- Binance signed endpoints.
- Futures, perpetuals, funding rates, open interest, options, or margin products.
- On-chain wallets, DEX routing, DeFi, NFT, or smart-money features.
- Host-only integrations such as `autocli`, `agent-reach`, browser state, or workspace scripts in the Docker runtime path.
- High-confidence social sentiment. First-version `social` is optional and best-effort only.
- Rewriting the upstream graph, analyst topology, or tool names.

## Recommended Architecture

Use a shared market-extension protocol with one thin upstream-facing dispatcher and market-specific implementations beneath it.

The upstream-facing contract stays the same:

- `get_stock_data`
- `get_indicators`
- `get_fundamentals`
- `get_balance_sheet`
- `get_cashflow`
- `get_income_statement`
- `get_news`
- `get_global_news`
- `get_insider_transactions`

The graph and analysts continue calling these abstract tools. Market selection happens below that layer.

### Why This Approach

- It matches the current A-share extension direction instead of fighting it.
- It keeps most future diffs under `tradingagents/extensions/*`.
- It avoids baking `if crypto` branches into multiple analyst and graph files.
- It keeps future upstream sync conflicts concentrated in a small number of thin adapter files.

## Target Module Layout

### Thin Upstream-Touching Files

- `tradingagents/dataflows/interface.py`
  - Generalize the current A-share-specific extension seam into a shared market-extension dispatcher.
  - Keep abstract method names unchanged.
- `tradingagents/dataflows/stockstats_utils.py`
  - Allow crypto OHLCV loading through the shared extension path so stockstats-based indicators can still work.
- Small prompt/context helpers only if market-aware wording is needed.

### Shared Extension Layer

- `tradingagents/extensions/market_ext/`
  - Shared types
  - Shared registry
  - Shared market dispatcher
  - Shared routing utilities

This is not a full framework rewrite. It is a small common protocol so both `ashare` and `crypto` use the same shape.

### Existing A-share Extension

- `tradingagents/extensions/ashare/`
  - Kept as our implementation module
  - Adapted lightly to the shared market-extension protocol
  - Existing provider chains and fallbacks remain intact

### New Crypto Extension

- `tradingagents/extensions/crypto/types.py`
- `tradingagents/extensions/crypto/normalize.py`
- `tradingagents/extensions/crypto/policy.py`
- `tradingagents/extensions/crypto/registry.py`
- `tradingagents/extensions/crypto/routing.py`
- `tradingagents/extensions/crypto/providers/binance_spot.py`
- `tradingagents/extensions/crypto/providers/coingecko.py`
- `tradingagents/extensions/crypto/news/` or `social/` helpers for formatting and source aggregation

## Input Normalization Rules

First version should accept:

- `BTC`
- `ETH`
- `BTCUSDT`
- `ETHUSDT`
- `BTC-USD`
- `ETH-USD`

Internal normalized fields:

- `raw_input`: original user input
- `base_symbol`: normalized base asset such as `BTC`
- `quote_symbol`: normalized quote asset such as `USDT`, `USD`, or `USDC`
- `trading_pair`: normalized pair such as `BTCUSDT`
- `market`: `crypto`

### Normalization Policy

- Bare symbols like `BTC` default to `USDT` for pair-driven market data.
- Explicit pair inputs preserve the quoted asset when supported.
- `BTC-USD` style inputs normalize to `base_symbol=BTC`, `quote_symbol=USD`, and a Binance-compatible pair when possible.
- If a pair is unsupported on Binance Spot, the market provider may fall back to symbol-level CoinGecko data.

This allows user-friendly symbol input while keeping provider implementations deterministic.

## Provider Responsibilities

### Binance Spot Provider

Purpose:

- Public spot market data only

Responsibilities:

- Symbol existence checks
- Latest price
- OHLCV / kline data
- Basic market microstructure context such as ticker stats or bid/ask where useful

Usage:

- Primary provider for `get_stock_data` and `get_indicators` on crypto
- Supplemental market context for `fundamentals` when useful

Must not do:

- Authenticated endpoints
- Orders
- Accounts
- Futures or derivatives

### CoinGecko Provider

Purpose:

- Symbol-level crypto fundamentals and market context

Responsibilities:

- Coin ID resolution
- Market cap and supply data
- Price history fallback
- Project-level market context useful for fundamentals

Usage:

- Primary provider for crypto `get_fundamentals`
- Fallback for market data if Binance Spot is unavailable or unsupported

### Crypto News And Social Sources

Purpose:

- Optional, best-effort enrichment only

Requirements:

- Docker-safe
- Publicly accessible
- No host browser or desktop dependency

Behavior:

- `news` should use public web/news style sources that can run in-container.
- `social` may use public-web-derived sources, but must be labeled low-confidence.
- Failure to retrieve `news` or `social` must not fail the entire analysis run.

## Routing Policy

### Crypto

- `get_stock_data`
  - Prefer Binance Spot
  - Fall back to CoinGecko if needed
- `get_indicators`
  - Prefer Binance-backed OHLCV
  - Fall back to CoinGecko-backed OHLCV if necessary
- `get_fundamentals`
  - Prefer CoinGecko
  - Optionally append lightweight Binance market context
- `get_news`
  - Use public web/news provider chain
- `get_global_news`
  - Use public macro/news provider chain
- `get_insider_transactions`
  - Unsupported for crypto in first version

### A-share

- Preserve the current A-share provider chains
- Do not introduce behavior regressions while moving to the shared dispatcher

## Social Analyst Behavior

`social` remains an optional analyst. This is important for both UX and implementation:

- Users can deselect it.
- The system must run cleanly without it.
- Crypto `social` in v1 should be explicitly best-effort and low-confidence.

The analyst interface itself should not be rewritten. If a small market-aware prompt tweak is needed, it should be done through a narrow helper or context string, not a new analyst architecture.

## Error Handling And Fallback Rules

### Provider Failures

- Providers signal failure at the extension layer so routing can fall through.
- Provider failures should not leak raw Python tracebacks into analyst prompts.
- Final tool outputs should be user-readable and analysis-safe.

### Missing Keys

- Optional keys such as `COINGECKO_API_KEY` may improve resilience.
- Missing optional keys must only degrade capability, never break core execution.

### Unsupported Instrument Shapes

- Unsupported or ambiguous crypto inputs should return a clean explanation.
- The dispatcher should avoid silently routing unsupported crypto inputs to stock vendors.

## Docker Runtime Requirements

Docker images must be able to run the default crypto path without relying on:

- host browser sessions
- `autocli`
- `agent-reach`
- workspace-local helper scripts

Default runtime assumptions:

- LLM key is present
- Public Binance Spot endpoints are reachable
- Public CoinGecko endpoints are reachable

Optional runtime enhancements:

- `COINGECKO_API_KEY`

## File-Level Change Summary

Expected change surface:

- Modify `tradingagents/dataflows/interface.py`
- Modify `tradingagents/dataflows/stockstats_utils.py`
- Add shared extension support under `tradingagents/extensions/market_ext/`
- Adapt `tradingagents/extensions/ashare/` to shared extension protocol
- Add `tradingagents/extensions/crypto/`
- Add focused tests for dispatcher, normalization, providers, and routing

Expected non-change surface:

- No graph rewrite
- No analyst topology rewrite
- No Docker dependence on host-only tooling

## Test Strategy

Add targeted tests for:

- shared dispatcher behavior
- A-share regression routing
- crypto market detection
- crypto normalization
- Binance Spot provider behavior
- CoinGecko provider behavior
- interface routing for crypto
- stockstats/indicator loading with crypto OHLCV
- graceful failure when optional providers are unavailable

Representative test files:

- `tests/test_market_extension_dispatch.py`
- `tests/test_crypto_market_detection.py`
- `tests/test_crypto_normalization.py`
- `tests/test_crypto_binance_provider.py`
- `tests/test_crypto_coingecko_provider.py`
- `tests/test_crypto_interface_routing.py`

Existing A-share coverage should also be rerun to prove no behavior regression.

## Risks

### Upstream Sync Risk

Low to moderate if the dispatcher change stays concentrated in `interface.py` and a small supporting set of files.

### Provider Drift Risk

Moderate. Public endpoints may change, especially CoinGecko rate/availability behavior. This is why optional-key support should exist even though the default path should work without keys.

### Social Quality Risk

High. First-version crypto `social` is intentionally low-confidence and should be treated as optional enrichment, not a core signal.

## Decision Record

- Use a shared market-extension dispatcher instead of adding more ad hoc `if` branches.
- Keep market-specific logic inside `tradingagents/extensions/*`.
- Add crypto support as `extensions/crypto`, not as scattered tool/analyst rewrites.
- Keep Docker runtime self-contained.
- Keep `social` optional.
- Do not add A-share Xueqiu if it depends on host-local tooling.
- First version supports crypto spot only.

## Implementation Readiness

This design is intentionally sized for a narrow implementation plan:

- one thin shared dispatcher seam
- one new market extension
- one lightweight A-share adaptation
- no trading/execution scope
- no host-only runtime dependencies

That keeps the work aligned with the original project goal: add new market capability without turning the fork into an upstream-hostile rewrite.
