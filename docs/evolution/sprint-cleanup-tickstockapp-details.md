# TickStockAppV2 Sprint 4 Detailed Cleanup Plan
## Comprehensive Gutting and Architecture Preparation

**Created:** 2025-08-25  
**Sprint:** 4 - TickStockApp Cleanup & Refactoring  
**Phase:** 2 - Cleanup & Prep  
**Version:** 1.0  

---

## Executive Summary

This document provides a comprehensive, prioritized cleanup plan for TickStockAppV2 Sprint 4. The goal is to **GUT THE APPLICATION TO ESSENTIALS** - transforming TickStockApp from a heavy, monolithic production-ready application into a **minimal pre-production core** that serves as a lightweight data ingestion and event consumption hub.

**🎯 PRE-PRODUCTION OBJECTIVES:**
- **Minimal Viable Core**: User login + basic dashboard + data ingestion
- **Essential Functionality Only**: Remove all non-critical processing
- **Database Cleanup**: Remove unused tables, simplify schema to essentials
- **Clean Foundation**: Prepare for TickStockPL integration with minimal bloat

**Scope:** Remove ~50-70% of current codebase, keeping only essential core functionality.  
**Timeline:** 5-7 days intensive gutting  
**Risk Level:** Medium-High (aggressive cleanup to essentials only)  
**Success Criteria**: User can log in, see basic dashboard, data flows to Redis  

---

## Pre-Production Core Functionality Definition

### ✅ ESSENTIAL FUNCTIONALITY TO PRESERVE
**The Absolute Minimum for a Working Application:**

1. **User Authentication & Session Management**
   - User login/logout functionality
   - Session persistence
   - Basic user registration (if needed for testing)
   - Flask-Login integration

2. **Basic Web Interface**
   - Login page rendering
   - Dashboard page rendering (even if mostly empty)
   - Basic navigation between pages
   - Static asset serving (CSS, JS, images)

3. **Core Data Ingestion**
   - Basic WebSocket connection to data source
   - Data reception and forwarding to Redis
   - Configuration management for data sources

4. **Minimal WebSocket Client Connectivity**
   - User can connect via WebSocket
   - Basic connection/disconnection handling
   - Simple message passing (even just heartbeat)

### ❌ NON-ESSENTIAL FUNCTIONALITY TO REMOVE
**Everything Else Can Go:**

- All event detection and processing logic
- Complex user filtering systems
- Analytics, metrics, and performance monitoring
- Multi-channel processing pipelines
- Complex caching systems
- Universe management complexity
- Event storage and replay systems
- Complex error handling and recovery systems
- Advanced configuration management
- Background processing threads (beyond basic data forwarding)
- Complex logging systems (keep basic logging only)

### 🎯 END GOAL: MINIMAL VIABLE SHELL
**What the cleaned application should do:**
1. Start successfully
2. Allow user to log in
3. Display a basic dashboard
4. Connect to WebSocket for real-time data
5. Forward data to Redis (for future TickStockPL integration)
6. Handle basic errors without crashing

**What it WON'T do (and that's OK for pre-production):**
- Process or analyze market data
- Generate events or alerts  
- Store historical data
- Provide advanced user features
- Handle complex error scenarios
- Provide detailed monitoring or analytics

---

## 📋 DOCUMENTATION CLEANUP MANDATE

### **CRITICAL RULE: NO OBSOLETE DOCS LEFT BEHIND**

**Every phase of this cleanup MUST include documentation updates.** Leaving outdated documentation is worse than having no documentation - it misleads future developers and creates confusion.

### **Documentation Cleanup Responsibilities by Phase:**

**📋 During Code Removal:**
- **IMMEDIATELY** remove/update associated documentation
- **NEVER** leave documentation referencing deleted code  
- **UPDATE** any README files in affected directories
- **CLEAN** docstrings and inline comments

**📋 Documentation Types to Track:**
1. **Feature Documentation**: `docs/features/*.md` 
2. **API Documentation**: REST endpoint docs, WebSocket event docs
3. **Architecture Documentation**: `docs/architecture/*.md`
4. **Setup Documentation**: Installation, configuration guides  
5. **Code Documentation**: README files, docstrings, inline comments
6. **User Documentation**: How-to guides, user manuals

**📋 Tracking Strategy:**
- **Create Documentation Log**: Track each file that needs updating
- **Phase Reviews**: Verify documentation cleanup before moving to next phase
- **Final Audit**: Comprehensive documentation review in Phase 11

**⚠️ WARNING: Documentation debt will slow down TickStockPL integration!**

---

## Phase 1: Pre-Cleanup Assessment & Preparation
**Duration:** Day 1 (Morning)  
**Priority:** CRITICAL  

### Phase 1.1: Codebase Analysis & Documentation Audit
- **Create backup branch**: `sprint-4-cleanup-backup`
- **Document current state**: Create inventory of all major components
- **Identify dependencies**: Map critical integration points
- **Test baseline**: Ensure current system works before cleanup begins
- **📋 DOCUMENTATION AUDIT**: Inventory ALL documentation files that will become obsolete
  - List all .md files in docs/
  - Identify README files throughout codebase
  - Note inline code documentation that references removed components
  - Create "Documentation Cleanup Checklist" for each phase

### Phase 1.2: Safety Measures
- **Create rollback strategy**: Document steps to restore if needed
- **Backup configuration**: Archive all current .env and config files  
- **Test environment**: Set up isolated cleanup environment
- **Version control**: Establish frequent commit strategy during cleanup

---

## Phase 2: Database Schema Cleanup & Simplification
**Duration:** Day 1 (Afternoon)  
**Priority:** CRITICAL  
**Impact:** Remove unused tables, simplify schema to core essentials

### Phase 2.1: Database Analysis & Cleanup Planning
**Current Database Assessment:**
- **User Tables**: `users`, `user_filters`, `user_universe` - **KEEP ESSENTIAL USER DATA**
- **Cache Tables**: `cache_entries` - **EVALUATE FOR MINIMAL NEEDS**
- **Analytics Tables**: `analytics_data`, `market_analytics` - **LIKELY REMOVE**
- **Session/Processing Tables**: Various accumulation/session tables - **LIKELY REMOVE**

### Phase 2.2: Database Table Removal
**Tables to REMOVE (Pre-production simplification):**
```sql
-- Remove analytics and processing tables
DROP TABLE IF EXISTS market_analytics;
DROP TABLE IF EXISTS analytics_data; 
DROP TABLE IF EXISTS session_analytics;
DROP TABLE IF EXISTS processing_stats;
DROP TABLE IF EXISTS event_history;
DROP TABLE IF EXISTS performance_metrics;

-- Remove complex caching if not essential
-- Evaluate: DROP TABLE IF EXISTS cache_entries; (decision needed)
```

**Tables to PRESERVE (Essential for core functionality):**
- `users` - Authentication essentials
- `user_filters` - User preferences (may be needed for future)
- Database migration tracking tables
- Any tables required for basic Flask-Login functionality

### Phase 2.3: Database Model Cleanup
**Files to Clean:**
- `src/infrastructure/database/models/analytics.py` - **REMOVE ENTIRELY**
- `src/infrastructure/database/models/base.py` - **KEEP, SIMPLIFY**
- Remove model references from app initialization
- Update SQLAlchemy imports throughout application

### Phase 2.4: Migration Strategy & Documentation Cleanup
- **Create Migration**: Document table removal for rollback
- **Data Backup**: Export any critical data before deletion
- **Clean Migration History**: Remove unused migration files
- **Update Schema**: Ensure minimal schema supports core functionality
- **📋 DATABASE DOCS CLEANUP**:
  - Update/remove `docs/architecture/database_*.md`
  - Remove analytics-related documentation
  - Update any API docs referencing removed tables
  - Clean up docstrings in database model files

---

## Phase 3: Legacy Event Detection System Removal
**Duration:** Day 1-2  
**Priority:** HIGH  
**Impact:** Major codebase reduction (~30% of processing logic)  

### Phase 2.1: Core Detection Engine Removal
**Files to Remove/Gut:**
- `src/processing/detectors/highlow_detector.py` - **REMOVE ENTIRELY**
- `src/processing/detectors/surge_detector.py` - **REMOVE ENTIRELY**  
- `src/processing/detectors/trend_detector.py` - **REMOVE ENTIRELY**
- `src/processing/detectors/manager.py` - **REMOVE ENTIRELY**
- `src/processing/detectors/engines.py` - **REMOVE ENTIRELY**
- `src/processing/detectors/utils.py` - **REMOVE ENTIRELY**
- `src/processing/detectors/buysell_engine.py` - **REMOVE ENTIRELY**
- `src/processing/detectors/buysell_tracker.py` - **REMOVE ENTIRELY**

### Phase 2.2: Event Processing Pipeline Cleanup + Documentation
**Files to Modify:**
- `src/processing/pipeline/event_detector.py` - **STRIP TO STUB**
  - Remove all pattern detection logic
  - Keep only basic event structure/interface
  - Prepare for TickStockPL integration hooks
- `src/processing/pipeline/event_processor.py` - **SIMPLIFY HEAVILY**
  - Remove event generation logic  
  - Keep only event forwarding/routing
  - Add Redis pub-sub hooks for TickStockPL integration
- `src/shared/utils/event_factory.py` - **SIMPLIFY**
  - Remove event creation logic
  - Keep only event structure definitions
  - Add transport conversion utilities for Redis

**📋 EVENT SYSTEM DOCS CLEANUP:**
- **Remove**: `docs/features/event-detection.md` - **DELETE ENTIRELY**
- **Remove**: `docs/features/highlow-detector.md` - **DELETE ENTIRELY**
- **Remove**: `docs/features/surge-detection.md` - **DELETE ENTIRELY**  
- **Remove**: `docs/features/trend-detection.md` - **DELETE ENTIRELY**
- **Update**: Any README files in `src/processing/` directories
- **Clean**: All docstrings referencing removed detection logic

### Phase 2.3: Channel System Simplification  
**Files to Modify:**
- `src/processing/channels/event_creators.py` - **REMOVE**
- `src/processing/channels/` - **ASSESS FOR REMOVAL**
  - Keep basic channel infrastructure if needed for data flow
  - Remove event creation and processing logic
  - Simplify to data forwarding only

### Phase 2.4: Domain Events Cleanup
**Files to Modify:**
- `src/core/domain/events/` - **PRESERVE BUT SIMPLIFY**
  - Keep base event structures (needed for transport)
  - Remove complex event creation logic
  - Simplify to basic data containers
  - Add `to_transport_dict()` methods for Redis pub-sub

---

## Phase 3: User Filtering System Overhaul  
**Duration:** Day 2-3  
**Priority:** HIGH  
**Impact:** Significant complexity reduction  

### Phase 3.1: Filter Logic Removal
**Files to Modify:**
- `src/presentation/websocket/data_filter.py` - **MAJOR GUTTING**
  - Remove all event filtering logic (Lines 38-164, 289-442)
  - Keep only basic data forwarding structure  
  - Add hooks for future TickStockPL filtered events
- `src/core/services/user_filters_service.py` - **PRESERVE DATABASE LOGIC**
  - Keep user preference storage/retrieval
  - Remove event filtering application logic (Lines 394-816)
  - Simplify to configuration management only

### Phase 3.2: WebSocket Publisher Simplification
**Files to Modify:**
- `src/presentation/websocket/publisher.py` - **MAJOR SIMPLIFICATION**
  - Remove user-specific filtering logic
  - Keep basic WebSocket event emission
  - Add Redis subscription for TickStockPL events
  - Simplify to basic event forwarding

### Phase 3.3: Filter Cache System Cleanup + Documentation
**Files to Assess:**
- `src/presentation/websocket/filter_cache.py` - **EVALUATE FOR REMOVAL**
  - May be needed for user preferences
  - Remove if only used for event filtering
  - Keep if needed for UI state management

**📋 FILTERING SYSTEM DOCS CLEANUP:**
- **Update/Remove**: `docs/features/filtering-system.md` - **MAJOR REWRITE OR DELETE**
- **Update**: Any user guide documentation referencing filtering
- **Clean**: All API documentation for filter endpoints
- **Remove**: Filter-related sections from user documentation
- **Update**: CLAUDE.md to reflect simplified filtering architecture

---

## Phase 4: Universe Management System Cleanup
**Duration:** Day 2-3  
**Priority:** MEDIUM-HIGH  
**Impact:** Architecture simplification  

### Phase 4.1: Universe Services Evaluation
**Files to Assess:**
- `src/core/services/universe_service.py` - **EVALUATE NECESSITY**
- `src/core/services/universe_coordinator.py` - **EVALUATE NECESSITY**  
- `src/core/services/universe/` - **ASSESS ENTIRE DIRECTORY**
  - Determine if universe concept is still needed
  - May be replaced by TickStockPL symbol management
  - Consider preserving user universe preferences only

### Phase 4.2: Universe Cache Cleanup
**Files to Modify:**
- `src/presentation/websocket/universe_cache.py` - **SIMPLIFY OR REMOVE**
  - Remove complex caching logic if not needed
  - Keep basic symbol list management if required for data forwarding

---

## Phase 5: Multi-Channel Processing Removal
**Duration:** Day 3  
**Priority:** MEDIUM  
**Impact:** Significant code reduction  

### Phase 5.1: Channel Infrastructure Assessment
**Directory to Evaluate:** `src/processing/channels/`
- `base_channel.py` - **ASSESS NECESSITY**
- `channel_config.py` - **LIKELY REMOVE**
- `channel_metrics.py` - **LIKELY REMOVE**  
- `channel_router.py` - **LIKELY REMOVE**
- `fmv_channel.py` - **LIKELY REMOVE**
- `ohlcv_channel.py` - **ASSESS FOR DATA FORWARDING**
- `tick_channel.py` - **ASSESS FOR DATA FORWARDING**

**Decision Criteria:**
- Keep if needed for basic data flow to Redis
- Remove if only used for internal event processing
- Simplify to basic data forwarding infrastructure

### Phase 5.2: Stream Manager Simplification  
**Files to Modify:**
- `src/processing/stream_manager.py` - **MAJOR SIMPLIFICATION**
  - Remove complex processing logic
  - Keep basic data ingestion and forwarding
  - Add Redis publishing for TickStockPL consumption

---

## Phase 6: Data Source Integration Cleanup
**Duration:** Day 3-4  
**Priority:** MEDIUM  
**Impact:** Maintain core data ingestion, remove processing complexity  

### Phase 6.1: Synthetic Data Provider Cleanup
**Files to Modify:**
- `src/infrastructure/data_sources/synthetic/` - **SIMPLIFY**
  - Keep basic synthetic data generation for development
  - Remove complex event simulation logic
  - Simplify to basic OHLCV tick generation
  - Ensure output format matches TickStockPL requirements

### Phase 6.2: Polygon Integration Cleanup
**Files to Modify:**
- `src/infrastructure/data_sources/polygon/` - **PRESERVE AND ENHANCE**
  - Keep and improve WebSocket data ingestion
  - Implement per-minute OHLCV forwarding to Redis  
  - Remove internal event processing
  - Add proper data formatting for TickStockPL consumption

### Phase 6.3: Data Adapter Simplification
**Files to Modify:**
- `src/infrastructure/data_sources/adapters/realtime_adapter.py` - **SIMPLIFY**
  - Remove event processing logic
  - Keep data ingestion and forwarding only
  - Add Redis publishing hooks

---

## Phase 7: WebSocket System Refactoring
**Duration:** Day 4  
**Priority:** HIGH  
**Impact:** Core functionality preservation with simplification  

### Phase 7.1: WebSocket Manager Cleanup
**Files to Modify:**
- `src/presentation/websocket/manager.py` - **PRESERVE CORE, SIMPLIFY**
  - Keep user connection management
  - Keep authentication integration
  - Remove complex event processing hooks
  - Add Redis subscription for TickStockPL events

### Phase 7.2: Data Publisher Transformation
**Files to Modify:**
- `src/presentation/websocket/data_publisher.py` - **TRANSFORM**
  - Remove internal event generation  
  - Transform to Redis event subscriber
  - Keep WebSocket emission to users
  - Simplify to event forwarding service

### Phase 7.3: Display Converter Simplification
**Files to Modify:**
- `src/presentation/websocket/display_converter.py` - **SIMPLIFY**
  - Remove complex event conversion logic
  - Keep basic data formatting for UI
  - Add handling for TickStockPL event format

---

## Phase 8: Core Services Cleanup  
**Duration:** Day 4-5  
**Priority:** MEDIUM  
**Impact:** Reduce service complexity while maintaining essential functions  

### Phase 8.1: Analytics Services Assessment
**Files to Evaluate:**
- `src/core/services/analytics_*.py` - **ASSESS NECESSITY**
  - May be needed for basic metrics
  - Remove if only used for internal event analytics
  - Keep if needed for user dashboard metrics

### Phase 8.2: Market Data Service Simplification
**Files to Modify:**
- `src/core/services/market_data_service.py` - **MAJOR SIMPLIFICATION**
  - Remove event processing orchestration
  - Keep data ingestion coordination
  - Add Redis publishing coordination
  - Simplify to data hub management

### Phase 8.3: Session Management Cleanup
**Files to Assess:**
- `src/core/services/session_manager.py` - **PRESERVE IF NEEDED**
- `src/core/services/accumulation_manager.py` - **ASSESS NECESSITY**
- `src/core/services/memory_accumulation.py` - **LIKELY REMOVE**

---

## Phase 9: App.py and Main Entry Point Refactoring
**Duration:** Day 5  
**Priority:** CRITICAL  
**Impact:** Core application startup and architecture  

### Phase 9.1: App.py Major Cleanup
**File to Modify:** `src/app.py` - **MAJOR REFACTORING**

**Lines to Remove/Modify:**
- **Lines 21-22**: Remove EventDetectionManager import
- **Lines 73-157**: Simplify `initialize_market_services()`
  - Remove event_manager initialization
  - Simplify to data_provider and basic market_service only
- **Lines 269-506**: Simplify WebSocket connection handlers
  - Remove complex filter loading logic
  - Simplify to basic authentication and connection management
- **Lines 591-685**: Remove complex database sync logic
  - Replace with simple Redis pub-sub management
- **Lines 769-825**: Remove multi-user filter cache initialization
  - Replace with basic Redis connection setup

**New Additions Needed:**
- Redis client initialization for TickStockPL communication
- TickStockPL event subscriber setup
- Basic data forwarding service initialization

### Phase 9.2: Configuration Cleanup
**Files to Modify:**
- `config/app_config.py` - **SIMPLIFY**
  - Remove event processing configurations
  - Add Redis and TickStockPL integration configs
  - Simplify to data ingestion and WebSocket configs

---

## Phase 10: Testing and Validation
**Duration:** Day 5-6  
**Priority:** CRITICAL  
**Impact:** Ensure functionality preservation  

### Phase 10.1: Core Functionality Testing
**Test Items:**
- **Data Ingestion**: Verify Polygon WebSocket still works
- **User Authentication**: Ensure login/WebSocket auth works
- **Basic UI**: Verify dashboard loads and connects
- **Configuration**: Test with both synthetic and Polygon data
- **Redis Integration**: Verify basic pub-sub functionality

### Phase 10.2: Integration Testing
**Test Items:**
- **WebSocket Flow**: Mock data input → Redis output
- **User Management**: Authentication and session handling
- **Error Handling**: Verify graceful degradation
- **Performance**: Ensure cleanup improved performance

### Phase 10.3: Mock TickStockPL Integration
**Test Items:**
- **Event Subscription**: Mock TickStockPL events via Redis
- **Event Display**: Verify UI can display forwarded events
- **Filter Integration**: Test user preferences still work for display

---

## Phase 11: Documentation and Finalization
**Duration:** Day 6-7  
**Priority:** HIGH  
**Impact:** Project continuity and handoff  

### Phase 11.1: Architecture Documentation
**Documents to Create:**
- **New Architecture Diagram**: Show simplified TickStockApp role
- **Integration Guide**: How to connect TickStockPL
- **API Documentation**: Redis pub-sub channels and formats
- **Configuration Guide**: New environment variables and setup

### Phase 11.2: COMPREHENSIVE Documentation Cleanup & Update
**CRITICAL**: Update/Remove ALL obsolete documentation

**📋 MAJOR DOCUMENTATION CLEANUP:**
- **Main README.md**: Complete rewrite reflecting minimal architecture
- **CLAUDE.md**: Major update removing references to deleted components
- **All component READMEs**: Update or remove throughout `src/` directories
- **API Documentation**: Remove endpoints for deleted functionality
- **User Documentation**: Simplify to core login + dashboard only

**📋 OBSOLETE DOCS TO REMOVE:**
- `docs/features/event-detection.md` - **DELETE**
- `docs/features/highlow-detector.md` - **DELETE**  
- `docs/features/surge-detection.md` - **DELETE**
- `docs/features/trend-detection.md` - **DELETE**
- `docs/features/filtering-system.md` - **DELETE OR MAJOR REWRITE**
- `docs/features/memory-first-processing.md` - **LIKELY DELETE**
- Any analytics documentation in `docs/`

**📋 DOCS TO UPDATE:**
- `docs/project_structure.md` - Reflect simplified structure
- `docs/technical_overview.md` - Major simplification
- All architecture documentation in `docs/architecture/`
- Integration patterns documentation
- Any user guides or API references

**📋 CODE COMMENT CLEANUP:**
- Remove docstrings referencing deleted functionality
- Update class/function headers throughout codebase  
- Clean inline comments referring to removed features
- Add simple comments for TickStockPL integration points

**📋 CONFIGURATION DOCS:**
- Update environment variable documentation
- Simplify setup/installation instructions
- Remove configuration docs for deleted features
- Add Redis integration configuration docs

---

## Risk Mitigation Strategies

### High-Risk Areas
1. **WebSocket System**: Critical for user experience - test extensively
2. **Data Ingestion**: Core functionality - ensure Polygon integration intact
3. **User Management**: Authentication must continue working
4. **Configuration**: Environment setup must remain functional

### Rollback Plan
1. **Git Strategy**: Frequent commits with descriptive messages
2. **Backup Branch**: Full backup before starting
3. **Incremental Testing**: Test after each phase
4. **Critical Path Protection**: Never remove authentication or basic connectivity simultaneously

### Success Criteria (Pre-Production Minimal Viable Shell)
1. **Aggressive Code Reduction**: 50-70% reduction in codebase size
2. **Startup Performance**: Application starts in <10 seconds (vs current complexity)
3. **Memory Usage**: <200MB baseline memory consumption
4. **Essential Functionality**: **ONLY** core essentials work:
   - User login/logout ✅
   - Basic dashboard display ✅  
   - Data ingestion → Redis forwarding ✅
   - Basic WebSocket client connectivity ✅
5. **Database Cleanup**: Minimal schema with only essential tables
6. **Integration Ready**: Clear, simple hooks for TickStockPL integration
7. **Stability**: No crashes during basic operations
8. **Simplicity**: Codebase simple enough for rapid TickStockPL integration

---

## Post-Cleanup Architecture

### What Remains (The Shell)
```
TickStockAppV2/
├── Data Ingestion Layer
│   ├── Polygon WebSocket Client (simplified)
│   ├── Synthetic Data Provider (simplified)
│   └── Data Formatting & Forwarding
├── Redis Integration Layer
│   ├── Data Publisher (to TickStockPL)
│   ├── Event Subscriber (from TickStockPL)
│   └── Pub-Sub Channel Management
├── User Management Layer
│   ├── Authentication System
│   ├── Session Management
│   └── User Preferences Storage
├── WebSocket Layer
│   ├── User Connection Management
│   ├── Event Broadcasting
│   └── Basic Error Handling
└── Web Interface Layer
    ├── Dashboard Framework
    ├── Basic UI Components
    └── Real-time Display System
```

### What Gets Removed
- All internal event detection engines
- Complex user filtering logic
- Multi-channel processing pipeline
- Internal analytics and accumulation
- Event generation and processing
- Complex universe management
- Legacy synthetic data complexity
- Internal event storage and replay systems

---

## Integration Readiness Checklist

### Redis Pub-Sub Channels
- [ ] `tickstock_data` - Raw data to TickStockPL
- [ ] `tickstock_patterns` - Pattern events from TickStockPL  
- [ ] `tickstock_alerts` - Alert events from TickStockPL
- [ ] `tickstock_config` - Configuration updates

### Data Format Specifications
- [ ] OHLCV message format documented
- [ ] Pattern event format documented
- [ ] Error handling format documented
- [ ] Heartbeat/health check format documented

### Configuration Management
- [ ] Redis connection settings
- [ ] TickStockPL service discovery
- [ ] Channel subscription management
- [ ] Fallback behavior configuration

---

## Conclusion

This comprehensive cleanup plan transforms TickStockAppV2 from a monolithic event processing system into a lean data hub optimized for integration with TickStockPL. The phased approach ensures minimal risk while achieving significant code reduction and architectural clarity.

**Next Sprint**: With this cleanup complete, Sprint 5 can focus on TickStockPL pattern library implementation while Sprint 6 handles the integration between the two systems.

**Key Success Metric**: A working TickStockApp shell that can ingest data, forward it via Redis, receive pattern events, and display them to users - all with 40-50% less code than the current implementation.