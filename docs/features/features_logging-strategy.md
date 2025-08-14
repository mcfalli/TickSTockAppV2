# TickStock Logging Architecture

**Version:** 2.0  
**Last Updated:** JUNE 2025  
**Status:** Production Standard

## Overview

TickStock implements a domain-specific logging architecture that provides precise diagnostics while maintaining performance. The system uses five distinct logging domains to separate concerns and enable efficient troubleshooting.

## Logging Domains

### Available Domains

```python
from logging_config import get_domain_logger, LogDomain

# Infrastructure and WebSocket management
LogDomain.CORE

# Authentication, sessions, and billing
LogDomain.AUTH_SESSION  

# User preferences and settings
LogDomain.USER_SETTINGS

# Market calculations and event detection  
LogDomain.DATA_EVENT_CALCS

# Universe filtering and membership
LogDomain.UNIVERSE_TRACKING
Domain Assignment by Component
ComponentDomainPurposeEventProcessorCOREInfrastructure and orchestrationDataPublisherCOREWebSocket emission and routingWorkerPoolManagerCOREThread managementHealthMonitorCORESystem monitoringTickProcessorDATA_EVENT_CALCSMarket data validationEventDetectorDATA_EVENT_CALCSEvent detection algorithmsTrendDetectorDATA_EVENT_CALCSTrend calculationsSurgeDetectorDATA_EVENT_CALCSSurge analysisUserUniverseManagerUSER_SETTINGSUser preferencesUserFiltersServiceUSER_SETTINGSFilter configurationsUniverseCoordinatorUNIVERSE_TRACKINGUniverse membershipSubscriptionManagerUNIVERSE_TRACKINGSubscription trackingAuthenticationManagerAUTH_SESSIONUser authenticationSessionManagerAUTH_SESSIONSession management
Logger Setup Pattern
python# Standard pattern for all components
from logging_config import get_domain_logger, LogDomain

# Create domain-specific logger
logger = get_domain_logger(LogDomain.DATA_EVENT_CALCS, 'event_detector')
Logging Levels
Production Logging Strategy
ERROR - Always logged

Critical failures requiring immediate attention
Data corruption or loss risks
Service connectivity failures

pythonlogger.error(f"Failed to connect to Polygon API: {e}")
logger.error(f"Database transaction failed for user {user_id}: {e}")
WARNING - Always logged

Recoverable issues with fallback behavior
Performance degradation warnings
Configuration problems

pythonlogger.warning("Polygon API unavailable, using synthetic data")
logger.warning(f"User {user_id} exceeded rate limit, throttling applied")
INFO - Selectively logged

Key business events and state changes
User actions and system milestones
Performance checkpoints

pythonlogger.info(f"User {username} authenticated successfully")
logger.info(f"WebSocket connection established for {len(stocks)} stocks")
logger.info(f"Trend detected: {symbol} - {direction} strength {strength}")
DEBUG - Development only

Detailed technical information
Variable states and calculations
Step-by-step processing flow

pythonlogger.debug(f"Processing tick: {symbol} price={price} volume={volume}")
logger.debug(f"Cache hit rate: {hit_rate}% for universe {universe_name}")
Configuration
Environment Variables
python# Console output control
LOG_CONSOLE_VERBOSE=false      # Hide INFO from console
LOG_CONSOLE_DEBUG=false        # Hide DEBUG from console

# File output control
LOG_FILE_ENABLED=true          # Create domain log files
LOG_FILE_PRODUCTION_MODE=true  # Only ERROR/WARNING to files

Best Practices
Message Quality
Good Examples:
python# Clear context and actionable information
logger.info(f"User {username} selected universe {universe_name} containing {stock_count} stocks")
logger.error(f"WebSocket disconnected: attempting reconnect {attempt}/{max_attempts}")
logger.warning(f"Rate limit approached: {current}/{limit} requests for user {user_id}")
Avoid:
python# Too vague
logger.info("Processing data")  # What data? For whom?

# Too noisy for production  
logger.info(f"Processing tick {i} of {total}")  # Floods logs

# Missing context
logger.error("Connection failed")  # Which connection? Why?
Performance Considerations
python# Use DEBUG level for high-frequency operations
for stock in stocks:
    logger.debug(f"Processing {stock}")  # Not INFO level

# Conditional expensive operations
if logger.isEnabledFor(logging.DEBUG):
    logger.debug(f"Expensive result: {expensive_calculation()}")
Component Migration Checklist
When adding logging to a component:

 Import appropriate domain logger
 Choose correct LogDomain based on component purpose
 Use descriptive module name in logger creation
 Apply appropriate log levels (ERROR/WARNING for production)
 Include relevant context in all messages
 Avoid logging in tight loops (use DEBUG if needed)

Integration with Monitoring
The domain-specific logs integrate with:

Prometheus: Metrics extracted from log patterns
CloudWatch/ELK: Log aggregation by domain
Alerting: ERROR/WARNING patterns trigger alerts
Performance Analysis: Domain-specific performance tracking

Quick Reference
python# Import pattern
from logging_config import get_domain_logger, LogDomain

