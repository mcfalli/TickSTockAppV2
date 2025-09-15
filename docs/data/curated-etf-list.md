# Curated ETF List for TickStock Processing

**Created**: 2025-09-12  
**Purpose**: Standard list of essential ETFs for market data processing and pattern analysis  
**Strategy**: Focus on liquid, commonly-referenced ETFs across major asset classes and sectors  

## ETF Categories & Selection Criteria

### Broad Market ETFs (Core Holdings)
**Purpose**: Complete US market exposure  
**Criteria**: High AUM, low expense ratios, broad diversification

- **SPY** - SPDR S&P 500 ETF Trust (Largest S&P 500 ETF)
- **QQQ** - Invesco QQQ Trust (NASDAQ-100 Technology Focus)  
- **IWM** - iShares Russell 2000 ETF (Small-Cap Exposure)
- **VTI** - Vanguard Total Stock Market ETF (Complete US Market)
- **VOO** - Vanguard S&P 500 ETF (Low-Cost S&P 500)

### Sector ETFs (SPDR Sector Series)
**Purpose**: Sector-specific analysis and rotation strategies  
**Criteria**: Standard sector classification, high liquidity

- **XLK** - Technology Select Sector SPDR Fund
- **XLF** - Financial Select Sector SPDR Fund  
- **XLV** - Health Care Select Sector SPDR Fund
- **XLE** - Energy Select Sector SPDR Fund
- **XLI** - Industrial Select Sector SPDR Fund
- **XLP** - Consumer Staples Select Sector SPDR Fund
- **XLY** - Consumer Discretionary Select Sector SPDR Fund
- **XLU** - Utilities Select Sector SPDR Fund
- **XLB** - Materials Select Sector SPDR Fund
- **XLRE** - Real Estate Select Sector SPDR Fund
- **XLC** - Communication Services Select Sector SPDR Fund

### Style/Factor ETFs
**Purpose**: Growth/Value/Quality factor analysis  
**Criteria**: Clear factor exposure, institutional usage

- **VUG** - Vanguard Growth ETF (Large-Cap Growth)
- **VTV** - Vanguard Value ETF (Large-Cap Value)
- **MTUM** - Invesco MSCI USA Momentum Factor ETF
- **QUAL** - iShares MSCI USA Quality Factor ETF
- **USMV** - iShares MSCI USA Min Vol Factor ETF

### International ETFs
**Purpose**: Global market exposure and correlation analysis  
**Criteria**: Regional/Country representation

- **VEA** - Vanguard FTSE Developed Markets ETF (Developed International)
- **EEM** - iShares MSCI Emerging Markets ETF (Emerging Markets)
- **IEFA** - iShares Core MSCI EAFE IMI Index ETF (Europe/Asia)
- **VWO** - Vanguard FTSE Emerging Markets ETF

### Bond ETFs
**Purpose**: Fixed income analysis and stock-bond correlation  
**Criteria**: Broad bond market representation

- **AGG** - iShares Core U.S. Aggregate Bond ETF (Core Bonds)
- **BND** - Vanguard Total Bond Market ETF (Total Bond Market)
- **TLT** - iShares 20+ Year Treasury Bond ETF (Long-Term Treasuries)
- **IEF** - iShares 7-10 Year Treasury Bond ETF (Intermediate Treasuries)

### Cryptocurrency/Bitcoin ETFs  
**Purpose**: Digital asset exposure and correlation analysis  
**Criteria**: First-generation crypto ETFs, high liquidity

- **IBIT** - iShares Bitcoin Trust (Bitcoin Spot ETF)
- **FBTC** - Fidelity Wise Origin Bitcoin Fund (Bitcoin Spot ETF)
- **BITB** - Bitwise Bitcoin ETF (Bitcoin Spot ETF)  
- **ETHE** - Grayscale Ethereum Trust (Ethereum Exposure)
- **GBTC** - Grayscale Bitcoin Trust (Bitcoin Exposure)

### Additional Essential ETFs
**Purpose**: Market completeness and trading volume leaders  
**Criteria**: High AUM, commonly referenced, institutional usage

- **DIA** - SPDR Dow Jones Industrial Average ETF (Dow 30)
- **MDY** - SPDR S&P MidCap 400 ETF (Mid-Cap Core)
- **SLY** - SPDR S&P 600 Small Cap ETF (Small-Cap Core)
- **VGT** - Vanguard Information Technology ETF (Tech Alternative to XLK)
- **XLRE** - Real Estate Select Sector SPDR Fund (Already included above)

### Specialty/Thematic ETFs
**Purpose**: Thematic analysis and emerging trends  
**Criteria**: Significant AUM, clear theme

- **ARKK** - ARK Innovation ETF (Disruptive Innovation)
- **GLD** - SPDR Gold Shares (Gold Commodity)
- **SLV** - iShares Silver Trust (Silver Commodity)
- **SCHG** - Schwab U.S. Large-Cap Growth ETF
- **SCHV** - Schwab U.S. Large-Cap Value ETF
- **VIG** - Vanguard Dividend Appreciation ETF (Dividend Growth)
- **NOBL** - ProShares S&P 500 Dividend Aristocrats ETF (Dividend Quality)

## Total Count: 46 Curated ETFs

**Rationale**: 
- Comprehensive market coverage with minimal overlap
- High liquidity and institutional usage
- Clear categorization for analysis purposes  
- Manageable size for processing and pattern matching
- Industry-standard symbols traders reference

## Usage in TickStock System

**Load Strategy**: Replace bulk ETF loading with curated list  
**Processing**: Focus pattern analysis on liquid, representative ETFs  
**UI Display**: Organized by category in dropdowns and analysis tools  
**Cache Organization**: Separate cache entries by ETF category  

## Maintenance

**Review Frequency**: Quarterly  
**Update Criteria**: AUM changes, new standard ETFs, discontinued funds  
**Approval**: Require documentation update when modifying list  