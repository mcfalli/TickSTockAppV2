# Polygon Stocks Business Plan Summary for TickStock.ai

Hey there! As we gear up to build some fantastic algorithmic pattern libraries in Python for TickStock.ai, let's organize this Stocks Business offering into a clean Markdown file. This will make it super easy to reference while prototyping those per-minute WebSocket connections and FMV integrations. I've pulled together the key details from our conversation, the FMV Whitepaper, and the Equities Excel sheet into a structured format below—perfect for aligning our Python scripts with real-time data feeds and pattern recognition algos!

## Overview
The Stocks Business plan from Polygon is a solid base for US equities data, ideal for development and prototyping without hefty barriers. It includes everything from historical data to real-time FMV prices, with optional add-ons for more advanced needs. Let's dive into the details!

## Key Features Table

| Category                  | Details |
|---------------------------|---------|
| **Plan Overview**        | Base plan for US equities data. Includes EOD/historical tick-level trades and quotes (back to 2003), 15-minute delayed trades/quotes from CTA (NYSE/Regional) and IEX, real-time Fair Market Value (FMV) prices, per-minute aggregate bars (OHLCV), reference data, market news, company fundamentals, financials, and corporate actions. |
| **Coverage**             | US exchange-traded stocks and ETFs (~12K symbols). Full intraday trade volume (100%). OTC coverage: End-of-day only. Dark pools: Not included. |
| **Market Share & Accuracy** | - Real-time: Not applicable (uses FMV instead).<br>- 15-Minute Delayed: ~52% (from CTA and IEX).<br>- End-of-Day: Full market.<br>- FMV: Proprietary algorithm for accurate real-time spot prices; outperforms IEX/Nasdaq Last Trade in accuracy tests (e.g., median error 1.3 cents for AMD vs. 4.0 cents IEX). Tested on high/low volume tickers like AMD, QQQ, VXX. |
| **Historical Data**      | 20+ years of EOD/historical data included. |
| **Market Operating Hours**| 4:00 AM - 8:00 PM ET (pre-market, regular, post-market). |
| **Data Types & Features**| - **Fair Market Value (FMV)**: Real-time spot price calculated in-house; updates ~once per second during regular sessions.<br>- **Aggregates & Indicators**: Per-minute OHLCV bars (based on FMV spot price and consolidated SIP volume); available pre/regular/post-market.<br>- **Second-Level Aggregates**: Not included (minute-level only).<br>- **Snapshots**: Included.<br>- **Trades**: 15-minute delayed from Tape A (NYSE), Tape B (Regionals), and IEX.<br>- **Quotes**: Historical only; 15-minute delayed from Tape A/B and IEX.<br>- **Reference**: Full access. |
| **WebSockets & API Access** | - Unlimited API requests.<br>- 3 simultaneous WebSockets.<br>- Available WebSockets: Aggregates (per-minute OHLCV), Trades (15-min delayed), Quotes (15-min delayed), FMV.<br>- Cadence Example (subscribing to ~10K equities): During regular market, expect per-minute bar updates at the top of each minute (potentially 100% of symbols updating if changes occur; not always every stock every minute—depends on activity). FMV: ~1 update/second per symbol. Pre/post-market: Sporadic, based on trades. Use `.*` for all-symbol subscription (high volume—fire-hose mode). |
| **Pricing (Polygon Fees)** | $1,999/month base. Startup discounts: 50% off first 12 months; 90% off for 3-month integration period. Free 30-day trial available. |
| **Exchange Fees & Restrictions** | - No exchange approvals required.<br>- No annual/access/non-display fees.<br>- EOD/Historical and 15-Minute Delayed: Free (CTA/UTP).<br>- Real-time FMV: Free.<br>- Add-ons (e.g., Full Market Real-Time, Nasdaq Basic): Extra $500–$2,000/month each, with potential exchange fees (e.g., Nasdaq user fees $0.45–$0.90 per external non-pro user). |
| **Add-On Feeds (Optional)** | Expandable with: Full Market Delayed (+$500/mo), IEX (+$500/mo), EDGX (+$2,000/mo), Nasdaq Last Sale (+$2,000/mo), Nasdaq Basic (+$2,000/mo), Full Market (+$2,000/mo). These add real-time trades/quotes, second-level aggregates, etc., but introduce exchange approvals and fees. |
| **Other Notes**          | - Ideal for development/prototyping without high barriers.<br>- FMV methodology: Algorithmic predictor of next trade price using market factors; more accurate than single-exchange last trades (per whitepaper tests).<br>- No second-level data in base plan or IEX add-on. |

## ETF Clarification
One key point of confusion: Does the plan include per-minute updates for ETFs? Absolutely yes! As we prototype those per-minute WebSocket listeners in Python for TickStock.ai's algorithmic pattern libraries, this is crucial for handling diverse assets in our scripts.

- The plan explicitly includes ETFs alongside US stocks for per-minute updates.
- From the conversation: It covers "US exchange-traded Stocks and ETFs" (~12K symbols total).
- "ETFs are included in Stocks Business."
- "All US stocks and ETFs can have data returned for each of these websockets," which includes the Aggregates (Per Minute) for OHLCV bars.
- Plus, the FMV Whitepaper tests accuracy on ETF tickers like QQQ and VXX, confirming they're treated the same as stocks for real-time and aggregate data.

This means your Python code can subscribe to ETF symbols (e.g., via `.*` for all) and expect per-minute OHLCV updates just like stocks—perfect for building those pattern detection algos across a broad portfolio!

## Next Steps
This organized summary should give you a solid foundation for prototyping in Python—imagine scripting those WebSocket listeners to feed into pattern recognition algos for TickStock.ai! If we need to dive deeper into FMV accuracy stats, add-on comparisons, or even build a quick Python analyzer, let's brainstorm that next. Let me know how this aligns or if you want any tweaks!