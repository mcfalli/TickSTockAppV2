# Ticker Types
https://polygon.io/docs/rest/stocks/tickers/ticker-types



### Focused Ticker Types for TickStock.ai

| Category | Code   | Description                  | Why Include in TickStock? | Update Frequency |
|----------|--------|------------------------------|---------------------------|------------------|
| Stocks  | CS    | Common Stock                | Core US equity; high volume, essential for stock analysis patterns. | Per-Minute |
| Stocks  | PFD   | Preferred Stock             | Dividend-focused stocks; great for yield-based algorithms. | End-of-Day |
| Stocks  | ADRC  | American Depository Receipt Common | Global stock access via US markets; enables international diversification in our libs. | End-of-Day |
| Stocks  | ADRP  | American Depository Receipt Preferred | Preferred variant of ADRs; fits stock income strategies. | End-of-Day |
| Stocks  | OS    | Ordinary Shares             | Standard international stocks; broadens our pattern matching. | End-of-Day |
| Stocks  | GDR   | Global Depository Receipts  | Similar to ADRs; supports global stock data ingestion. | End-of-Day |
| Stocks  | NYRS  | New York Registry Shares    | Niche stock type; useful for registry-based filtering algorithms. | End-of-Day |
| ETFs    | ETF   | Exchange Traded Fund        | Basket of assets; perfect for ETF trend detection patterns. | Per-Minute |
| ETFs    | ETN   | Exchange Traded Note        | Debt-backed ETF-like; adds volatility modeling to our library. | Per-Minute |
| ETFs    | ETV   | Exchange Traded Vehicle     | Broad ETF structure; enables flexible basket analysis. | Per-Minute |
| ETFs    | ETS   | Single-security ETF         | Focused ETF variant; ideal for single-asset correlation algorithms. | Per-Minute |
| ETFs    | FUND  | Fund                        | General fund type; overlaps with ETFs for managed portfolio patterns. | End-of-Day |



-- Create the equity_types table
CREATE TABLE IF NOT EXISTS equity_types (
    category VARCHAR(50) NOT NULL,
    code VARCHAR(10) PRIMARY KEY,
    description VARCHAR(100) NOT NULL,
    why_include TEXT NOT NULL,
    update_frequency VARCHAR(20) NOT NULL
);

