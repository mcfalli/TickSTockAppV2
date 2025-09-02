# cache_entries database table

## About cache_entries:
cache_entries table is a table that is loaded into our src\infrastructure\cache\cache_control.py CacheControl class where keys and values are loaded at application startup and stored for quick access in the cache. 
The CacheControl class is fairly structured with what it expects from a key and value and access perspective.  This class can be cleaned up based on usage through out the code (search for methods and functions in use or not in use to clean up).
There are two primary types of features logged in this table and extended in code:
1. app_settings:  (type=app_settings, name=app_settings) not as widely used as I would like.  I feel this table has the ability to replace much of the config (.env) files content and at start up load settings based on environment loaded (e.g. production, development, test).
2. stocks content:  (see Table Documentation section below for distinct type, name, key values below).  Exposed via CacheControl the intent is to shape various organization within the stocks into sectors, themes, universes, groups. 

## cache_entries Goal for Use
organize stocks into logical groups to describe stocks sectors, themes, priority groups, stock universes, etc.  

## Goals for this sprint:
- Understand the history and use of the table contents.
- Leverate existing script meta data to help build organization structure of cache_entries relative to stocks and ETFs.
- devise an organization structure for stocks and ETFs in cache_entries table (market cap, sectors, themes, industry, top X, etc.).
- have one process / job (src/core/services/cache_entries_synchronizer.py) that performs all the organization updates to cache_entries. 

## End Goal Success Criteria
[ ] cache_entries retains the original app_settings content untouched.
[ ] cache_entries has well orgnazed entries defining stock, equiities, ETFs into logical groups allowing the current or future state to leverage in back-end processing and front-end functionality.
[ ] CacheControl code is cleaned up only exposing what is used throughout the code and defined grouping and organization.
[ ] Admin historical load page contains post stock or ETF load process to run the 'update and organize the cache' and can be ran at any time to delete and re-insert stock and ETF data into cache_entries without disrupting other types (i.e. app_settings)
[ ] Remove "current scripts to assist" once new job completed.
[ ] Update documentation relative to historical data loading and running cache job.


## Current Scripts to assist
### Read and Report cache_entries
A helpful reporting script to understand the contents of the cache_entries table: scripts\dev_tools\maint_read_stock_cache_entries.py
### Current Loading Mechanism
Currently the following scripts historically assist in shaping and loading the cache_entries table.  From these there is meta data that can be leveraged for the new process. 
scripts\dev_tools\load_stocks_cache_entries.py
scripts\dev_tools\maint_load_stock_cache_entries.py

## Table Documentation
### cache_entries current type, name, key values
"type","name","key"
"app_settings","app_settings","SECRET_KEY"
"app_settings","app_settings","MAX_LOGIN_ATTEMPTS"
"app_settings","app_settings","SESSION_DURATION"
"app_settings","app_settings","SESSION_EXPIRY_DAYS"
"app_settings","app_settings","LOCKOUT_DURATION_MINUTES"
"app_settings","app_settings","MAX_LOCKOUTS"
"app_settings","app_settings","MAIL_SERVER"
"app_settings","app_settings","MAIL_PORT"
"app_settings","app_settings","MAIL_USE_TLS"
"app_settings","app_settings","MAIL_USE_SSL"
"app_settings","app_settings","MAIL_DEFAULT_SENDER"
"app_settings","app_settings","MAIL_TIMEOUT"
"app_settings","app_settings","SQLALCHEMY_TRACK_MODIFICATIONS"
"app_settings","app_settings","SERVER_NAME"
"app_settings","app_settings","BASE_URL"
"app_settings","app_settings","REDIS_URL"
"priority_stocks","processing","priority_list"
"priority_stocks","processing","top_priority"
"priority_stocks","processing","secondary_priority"
"stock_universe","market_cap","mega_cap"
"stock_universe","market_cap","large_cap"
"stock_universe","market_cap","mid_cap"
"stock_universe","market_cap","small_cap"
"stock_universe","market_cap","micro_cap"
"stock_universe","sector_leaders","top_10_consumer_staples"
"stock_universe","sector_leaders","top_10_real_estate"
"stock_universe","sector_leaders","top_10_healthcare"
"stock_universe","sector_leaders","top_10_energy"
"stock_universe","sector_leaders","top_10_industrials"
"stock_universe","sector_leaders","top_10_materials"
"stock_universe","sector_leaders","top_10_utilities"
"stock_universe","sector_leaders","top_10_consumer_discretionary"
"stock_universe","sector_leaders","top_10_financial_services"
"stock_universe","sector_leaders","top_10_technology"
"stock_universe","sector_leaders","top_10_communication_services"
"themes","AI","list"
"stock_universe","themes","ai"
"themes","Biotech","list"
"stock_universe","themes","biotech"
"themes","Cloud","list"
"stock_universe","themes","cloud"
"themes","Crypto","list"
"stock_universe","themes","crypto"
"themes","Cybersecurity","list"
"stock_universe","themes","cybersecurity"
"themes","EV","list"
"stock_universe","themes","ev"
"themes","Fintech","list"
"etf_universe","International ETFs","etf_international"
"etf_universe","Technology ETFs","etf_technology"
"stock_universe","themes","fintech"
"themes","Marijuana","list"
"stock_universe","themes","marijuana"
"themes","Quantum","list"
"stock_universe","themes","quantum"
"themes","Robotics","list"
"stock_universe","themes","robotics"
"themes","Semi","list"
"stock_universe","themes","semi"
"themes","Space","list"
"stock_universe","themes","space"
"stock_universe","market_leaders","top_10_stocks"
"stock_universe","market_leaders","top_50"
"stock_universe","market_leaders","top_100"
"stock_universe","market_leaders","top_250"
"stock_universe","market_leaders","top_500"
"stock_universe","industry","banks"
"stock_universe","industry","insurance"
"stock_universe","industry","software"
"stock_universe","industry","retail"
"stock_universe","complete","all_stocks"
"stock_stats","universe","summary"
"etf_universe","Broad Market ETFs","etf_broad_market"
"etf_universe","Sector ETFs","etf_sectors"
"etf_universe","Growth ETFs","etf_growth"
"etf_universe","Value ETFs","etf_value"
"stock_universe","Dev Top 10 Stocks","dev_top_10"
"stock_universe","Dev Sector Representatives","dev_sectors"
"etf_universe","Dev ETF Selection","dev_etfs"
"etf_universe","Bond ETFs","etf_bonds"
"etf_universe","Commodity ETFs","etf_commodities"


### cache_entries current value structure examples
This content contains three primary data structures: **JSON objects** representing a stock universe, **JSON arrays** of stock tickers, and a **JSON object** providing an overview of a stock portfolio.
***
Stock Universe JSON Object
This is the most common structure. It's an object with keys like `"count"` and `"stocks"`. The `"stocks"` value is an array of objects, where each object represents a single stock with details like its **name, rank, sector, ticker, exchange, industry**, and **market cap**.
* Example: `{"count": 87, "stocks": [{"name": "Nvidia Corp", "rank": 1, "sector": "Technology", "ticker": "NVDA", "exchange": "XNAS", "industry": "Semiconductors", "market_cap": 4347325922407.0, ...}`
* Example: `{"count": 10, "stocks": [{"name": "Coca-Cola Company", "rank": 1, "sector": "Consumer Staples", "ticker": "KO", "exchange": "XNYS", "industry": "Beverages", "market_cap": 297168223751.0}, ...}`
***
Stock Ticker JSON Array
This is a simple array of strings, where each string is a **stock ticker symbol**. This format is used to list a group of stocks without providing any additional details.
* Example: `["MSFT", "NVDA", "GOOGL", "AVGO", "PLTR", "AMD", "ADBE", ...]`
* Example: `["TSLA", "GM", "F", "RIVN", "LCID", "BYD", "EVGO", "CHPT"]`
***
Stock Portfolio Overview JSON Object
This is a single JSON object that provides high-level statistics about a collection of stocks. It includes keys such as `"total_stocks"`, `"unique_sectors"`, `"total_market_cap"`, and `"average_market_cap"`.
* Example: `{"overview": {"total_stocks": 5198, "unique_sectors": 12, "total_market_cap": 73617795359585.0, ...}`