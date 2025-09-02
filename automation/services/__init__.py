"""
TickStock Automation Services

This package contains automation services that run separately from TickStockApp:
- IPO monitoring and symbol change detection
- Data quality monitoring and automated remediation
- Equity types integration and processing rules

All services follow the TickStock architecture pattern:
- Services are producers with full database access
- TickStockApp is a consumer via Redis pub-sub
- Loose coupling maintained through Redis messaging
"""

__version__ = "14.2.0"