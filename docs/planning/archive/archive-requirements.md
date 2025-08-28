# TickStock.ai Requirements

## Functional Requirements
(Tie-in to user stories from our Sprint 1 backlog—e.g., real-time Doji detection, extensible patterns, data blending, etc. Detailed in separate user_stories.md.)

## Non-Functional Requirements
- **Performance**: Latency <50ms for real-time pattern detections in TickStockPL (e.g., processing WebSockets updates and publishing events).
- **Scalability**: Memory usage <2GB when scanning 1k symbols simultaneously; support parallel processing in PatternScanner.
- **Quality**: Achieve 80% test coverage target across src/ (patterns, data, analysis) using pytest or similar.
- **Compatibility**: Support for 1min and daily timeframes out of the gate, with extensibility for others (e.g., hourly) via DataBlender resampling.
- **Reliability**: Bootstrap-friendly with lightweight deps; handle errors gracefully (e.g., API fallbacks, retries).
- **Security/Usability**: Events and data handled via Redis with pub-sub for loose coupling; UI in TickStockApp for param customization and visuals.

These reqs guide our Python implementation, ensuring TickStock.ai's pattern libraries are efficient, testable, and ready for growth.