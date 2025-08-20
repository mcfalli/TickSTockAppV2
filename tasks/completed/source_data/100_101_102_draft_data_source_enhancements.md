Sprint 100: Product Requirements Document
Multi-Frequency Data Source Support for WebSocket and Simulated Interfaces

Executive Summary
Sprint Goal
Enhance TickStock's data ingestion architecture to support multiple concurrent data frequencies (per-second, per-minute, fair market value) from Polygon WebSocket and Simulated/Synthetic data sources while maintaining backward compatibility with existing per-second processing.
Business Value

Flexibility: Support various data update frequencies to accommodate different use cases and reduce costs
Scalability: Enable parallel processing of multiple data streams without interference
Development Efficiency: Enhanced synthetic data simulation for all production frequencies
Future-Ready: Architectural foundation for RESTful data sources and additional providers

Success Criteria

 Multiple WebSocket subscriptions running concurrently without data loss
 Configuration-driven frequency selection for both production and test modes
 Synthetic data accurately simulating all supported frequencies
 Zero impact on existing per-second processing performance
 Complete documentation of configuration options and processing flows


Background & Context
Current State
TickStock currently operates with:

Per-second WebSocket updates from Polygon.io via PolygonWebSocketClient
Synthetic/Simulated data processor mimicking per-second updates for development
Event-driven architecture built around high-frequency tick processing
Real-time processing pipeline optimized for sub-millisecond latency

Problem Statement
The current architecture is tightly coupled to per-second updates, limiting:

Cost optimization through lower-frequency subscriptions
Support for different data types (fair market value, aggregated data)
Testing scenarios with varied update frequencies
Integration with providers offering different temporal resolutions

Proposed Solution
Implement a frequency-agnostic data ingestion layer that:

Maintains existing per-second processing as default
Adds configurable support for multiple concurrent frequencies
Enhances synthetic data to simulate all production frequencies
Prepares architecture for future RESTful integrations


Technical Requirements
1. Architecture Documentation
Objective: Document current implementation for clear understanding
Deliverables:

Current WebSocket Architecture

PolygonWebSocketClient class structure and event flow
RealTimeDataAdapter integration patterns
WebSocket subscription lifecycle management
Connection health monitoring and reconnection logic


Synthetic Data Architecture

SimulatedDataProvider class implementation
Data generation algorithms and patterns
Configuration-driven behavior controls
Integration with DataProviderFactory


Configuration System

Environment variables: USE_POLYGON_API, USE_SYNTHETIC_DATA
Cache control settings via CacheControl singleton
Debug flags and monitoring toggles
Current subscription management approach



2. Configuration Enhancement Plan
Objective: Design flexible configuration system for multi-frequency support
Requirements:

Environment Mode Selection
python# Master toggle for production vs test
DATA_SOURCE_MODE = "production" | "test" | "hybrid"

# Provider selection
ACTIVE_DATA_PROVIDERS = ["polygon", "synthetic", "both"]

Subscription Configuration
python# WebSocket subscriptions (JSON structure)
WEBSOCKET_SUBSCRIPTIONS = {
    "per_second": {
        "enabled": true,
        "symbols": ["*"],  # or specific list
        "handler": "handle_tick"
    },
    "per_minute": {
        "enabled": true,
        "symbols": ["SPY", "QQQ"],
        "handler": "handle_minute_bar"
    },
    "fair_market_value": {
        "enabled": false,
        "symbols": [],
        "handler": "handle_fmv"
    }
}

Processing Configuration
python# Processing behavior controls
PROCESSING_CONFIG = {
    "batch_processing": true,
    "batch_size": 100,
    "parallel_streams": true,
    "stream_isolation": true,
    "fallback_on_error": true
}


3. WebSocket Enhancement Implementation
Objective: Support multiple concurrent WebSocket subscriptions
Code Updates Required:
3.1 Enhanced PolygonWebSocketClient
pythonclass PolygonWebSocketClient:
    def __init__(self):
        self.subscriptions = {}  # frequency -> subscription details
        self.handlers = {}       # frequency -> handler function
        
    def subscribe_multi_frequency(self, config):
        """Subscribe to multiple data frequencies simultaneously"""
        for frequency, settings in config.items():
            if settings['enabled']:
                self.subscribe_frequency(
                    frequency=frequency,
                    symbols=settings['symbols'],
                    handler=settings['handler']
                )
    
    def subscribe_frequency(self, frequency, symbols, handler):
        """Subscribe to specific frequency with dedicated handler"""
        # Implementation for frequency-specific subscription
3.2 Parallel Stream Processing
pythonclass DataStreamManager:
    def __init__(self):
        self.streams = {}  # frequency -> stream processor
        
    def process_stream(self, frequency, data):
        """Route data to appropriate stream processor"""
        if frequency not in self.streams:
            self.streams[frequency] = self.create_processor(frequency)
        return self.streams[frequency].process(data)
3.3 Event Router Enhancement
pythonclass EventProcessor:
    def route_by_frequency(self, tick_data, frequency):
        """Route events based on data frequency"""
        if frequency == "per_second":
            return self.handle_tick(tick_data)
        elif frequency == "per_minute":
            return self.handle_minute_bar(tick_data)
        elif frequency == "fair_market_value":
            return self.handle_fmv(tick_data)
4. Synthetic Data Enhancement
Objective: Simulate all production data frequencies
Implementation Requirements:
4.1 Multi-Frequency Generator
pythonclass SimulatedDataProvider:
    def __init__(self, config):
        self.generators = {
            "per_second": PerSecondGenerator(),
            "per_minute": PerMinuteGenerator(),
            "fair_market_value": FMVGenerator()
        }
        
    def start_simulation(self, frequency_config):
        """Start generating data for configured frequencies"""
        for frequency, settings in frequency_config.items():
            if settings['enabled']:
                self.start_frequency_generator(frequency, settings)
4.2 Frequency-Specific Generators

PerSecondGenerator: Existing implementation (maintain compatibility)
PerMinuteGenerator: Aggregate 60 seconds of synthetic ticks into OHLCV bars
FMVGenerator: Generate fair market value updates at configurable intervals

4.3 Realistic Data Patterns

Market session awareness (pre-market, regular, after-hours)
Volume patterns matching frequency characteristics
Price movement correlation across frequencies
Configurable volatility and trend patterns

5. Documentation Requirements
Objective: Comprehensive documentation for configuration and usage
Documentation Deliverables:
5.1 Configuration Guide

Complete environment variable reference
JSON configuration schema documentation
Migration guide from single to multi-frequency
Best practices for frequency selection

5.2 Architecture Documentation

Updated data flow diagrams including multi-frequency paths
Sequence diagrams for parallel stream processing
Component interaction maps
Performance implications of various configurations

5.3 Developer Guide

API documentation for new handlers
Testing strategies for multi-frequency scenarios
Debugging multi-stream processing
Monitoring and metrics for each frequency



## Polygon WebSockets Docs:

### Fair Market Value
WS
Business: wss://business.polygon.io/stocks
Access to this API begins at the Stocks Business plan level.
Stream real-time Fair Market Value (FMV) data for a specified stock ticker via WebSocket. This proprietary metric, available exclusively to Business plan users, provides an algorithmically derived, real-time estimate of a security’s fair market price. By delivering accurate, continuous valuation data, this feed supports informed trading decisions, enhanced analytics, and more effective risk management.

Use Cases: Pricing strategies, algorithmic modeling, risk assessment, investor decision-making.

Parameters
Reset values
ticker
string
required
*
Specify a stock ticker or use * to subscribe to all stock tickers. You can also use a comma separated list to subscribe to multiple stock tickers. You can retrieve available stock tickers from our Stock Tickers API.
Response Attributes
ev
enum (FMV)
The event type.
fmv
number
Fair market value is only available on Business plans. It is our proprietary algorithm to generate a real-time, accurate, fair market value of a tradable security. For more information, contact us.
sym
string
The ticker symbol for the given security.
t
integer
The nanosecond timestamp.


### Aggregates (Per Minute)
Real-Time: wss://socket.polygon.io/stocks
Stream minute-by-minute aggregated OHLC (Open, High, Low, Close) and volume data for specified tickers via WebSocket. These aggregates are updated continuously in Eastern Time (ET) and cover pre-market, regular, and after-hours sessions. Each bar is constructed solely from qualifying trades that meet specific conditions; if no eligible trades occur within a given minute, no bar is emitted. By providing a steady flow of aggregate bars, this endpoint enables users to track intraday price movements, refine trading strategies, and power live data visualizations.

Use Cases: Real-time monitoring, dynamic charting, intraday strategy development, automated trading.

Parameters
Reset values
ticker
string
required
*
Specify a stock ticker or use * to subscribe to all stock tickers. You can also use a comma separated list to subscribe to multiple stock tickers. You can retrieve available stock tickers from our Stock Tickers API.
Response Attributes
ev
enum (AM)
The event type.
sym
string
The ticker symbol for the given stock.
v
integer
The tick volume.
av
integer
Today's accumulated volume.
op
number
Today's official opening price.
vw
number
The tick's volume weighted average price.
o
number
The opening tick price for this aggregate window.
c
number
The closing tick price for this aggregate window.
h
number
The highest tick price for this aggregate window.
l
number
The lowest tick price for this aggregate window.
a
number
Today's volume weighted average price.
z
integer
The average trade size for this aggregate window.
s
integer
The start timestamp of this aggregate window in Unix Milliseconds.
e
integer
The end timestamp of this aggregate window in Unix Milliseconds.
otc
boolean
Whether or not this aggregate is for an OTC ticker. This field will be left off if false.

Sample Response:
{
  "ev": "AM",
  "sym": "GTE",
  "v": 4110,
  "av": 9470157,
  "op": 0.4372,
  "vw": 0.4488,
  "o": 0.4488,
  "c": 0.4486,
  "h": 0.4489,
  "l": 0.4486,
  "a": 0.4352,
  "z": 685,
  "s": 1610144640000,
  "e": 1610144700000
}


### Polygon Background Documentation "Stocks Overview"
Stocks Overview
At Polygon.io, we provide real-time streaming access to U.S. stock market data through WebSockets, delivering a continuous flow of updates directly to your applications. Our WebSocket feeds include trades, quotes, aggregates (bars), limit-up/limit-down (LULD) events, and Fair Market Value (FMV) measurements, enabling developers, traders, and analysts to receive live, push-based market data with minimal latency. By tapping into these streaming endpoints, you can power dynamic dashboards, feed algorithmic trading strategies, and monitor market conditions as they unfold -- without the need for repeated requests.

Market Hours and Timezone
All stock market data delivered over WebSockets follows the standard U.S. equity trading sessions in Eastern Time (ET):

Pre-Market: 4:00 AM to 9:30 AM ET
Regular Market: 9:30 AM to 4:00 PM ET
After-Hours: 4:00 PM to 8:00 PM ET
While streaming endpoints remain active outside regular hours, the frequency and type of updates may vary depending on market activity and the data feed in question. All timestamps are provided as Unix timestamps (seconds since epoch, UTC). When converting these timestamps into human-readable form (e.g., market open at 9:30 AM), remember they represent UTC time, not Eastern Time (ET). To correctly align data with market hours or dates, you'll need to explicitly convert timestamps from UTC to ET during your analysis.

Infrastructure and Reliability
Our WebSocket infrastructure is engineered for speed, stability, and scalability. By co-locating servers with exchanges and Securities Information Processors (SIPs), we minimize latency and ensure that you receive updates as quickly as possible. Redundant data centers and load balancing further enhance reliability, allowing us to maintain steady data delivery even under high load or challenging network conditions.

This real-time architecture ensures seamless, continuous data streams, ideal for latency-sensitive applications such as algorithmic trading, live charting, and event-driven analyses.

Data Flow: From Exchanges to You
Polygon.io’s WebSocket feeds draw data from the same robust sources as our REST endpoints. We combine direct connections to all major U.S. stock exchanges with SIP-consolidated feeds, ensuring that you receive the most accurate, timely, and comprehensive market data available.

As soon as trades, quotes, or other market events are published by the exchanges and consolidated by the SIPs, they are relayed through our infrastructure and pushed over our WebSocket channels to your subscribed clients. This near-instantaneous delivery supports real-time decision-making and dynamic updates to your trading or analytical systems.

Available WebSocket Feeds for Stocks
Our WebSocket channels deliver a broad range of streaming data, covering all critical aspects of market activity:

Aggregates (Per Minute): Receive OHLC (Open, High, Low, Close) bars updated every minute. Ideal for intraday charting, real-time technical analysis, and monitoring market trends.
Aggregates (Per Second): Obtain second-by-second OHLC bars for ultra-fine-grained analysis. Useful for high-frequency strategies, liquidity assessments, and rapid response trading models.
Trades: Stream every executed trade in real-time, including price, size, exchange, and conditions. Perfect for tick-level analyses, order flow studies, and highly responsive trading algorithms.
Quotes: Access NBBO (National Best Bid and Offer) quotes as they update. This feed supports monitoring the evolving price landscape, evaluating spreads, and identifying liquidity conditions.
Limit Up - Limit Down (LULD): Track real-time volatility safeguards and price bands triggered by regulatory mechanisms. Useful for detecting trading halts, resumption signals, and understanding rapid market movements.
Fair Market Value (FMV): Obtain our proprietary real-time FMV metric, exclusively available to Business plan users, offering an algorithmically derived estimate of a security’s fair market price.
By subscribing to these WebSocket feeds, you gain uninterrupted, event-driven data flow, eliminating the overhead of polling for updates and ensuring that your applications always stay in sync with the latest market conditions.

Next Steps
Leverage our documentation to integrate these WebSocket feeds into your applications. With a simple subscription model, you can dynamically select which tickers and data streams you need, enabling tasks such as:

Powering live dashboards and visualizations
Feeding algorithmic models with instantaneous updates
Conducting real-time risk management and compliance checks
Enhancing trading platforms with low-latency insights
By utilizing Polygon.io’s stock WebSocket feeds, you position your applications at the cutting edge of real-time market intelligence, empowering rapid, data-driven decision-making and innovation in the U.S. equity markets.