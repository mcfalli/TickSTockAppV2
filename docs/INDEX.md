# TickStockAppV2 Documentation Index

**Quick Navigation Guide to All Documentation**

## 🚀 Start Here

1. **[CURRENT_STATUS.md](CURRENT_STATUS.md)** - Live system status, what's working now
2. **[README.md](README.md)** - Main documentation overview
3. **[architecture/system-architecture.md](architecture/system-architecture.md)** - How the system works

## 📁 By Category

### Planning & Vision
- **[planning/project-overview.md](planning/project-overview.md)** - Complete project vision
- **[planning/user_stories.md](planning/user_stories.md)** - User requirements
- **[planning/evolution_index.md](planning/evolution_index.md)** - Project history

### Sprint Documentation
- **[planning/sprints/sprint25a/](planning/sprints/sprint25a/)** - Latest integration fixes
- **[planning/sprints/sprint25/](planning/sprints/sprint25/)** - Current sprint (Multi-tier Dashboard)
- **[planning/sprints/multi_sprint_roadmap/](planning/sprints/multi_sprint_roadmap/)** - Sprint 25-30 roadmap

### Architecture
- **[architecture/system-architecture.md](architecture/system-architecture.md)** - System overview with Sprint 25A updates
- **[architecture/database-architecture.md](architecture/database-architecture.md)** - Database design
- **[architecture/redis-integration.md](architecture/redis-integration.md)** - Redis pub-sub patterns
- **[architecture/websockets-integration.md](architecture/websockets-integration.md)** - Real-time updates

### Development
- **[development/coding-practices.md](development/coding-practices.md)** - Development standards
- **[development/unit_testing.md](development/unit_testing.md)** - Testing guidelines
- **[development/code-documentation-standards.md](development/code-documentation-standards.md)** - Documentation standards
- **[project_structure.md](project_structure.md)** - Folder organization

### Implementation Details
- **[implementation/database_integration_logging_implementation.md](implementation/database_integration_logging_implementation.md)** - Integration logging (Sprint 25A)
- **[implementation/duplicate_subscriber_fix.md](implementation/duplicate_subscriber_fix.md)** - Architecture fix (Sprint 25A)

### Guides & Operations
- **[guides/integration-guide.md](guides/integration-guide.md)** - TickStockPL integration
- **[guides/startup-guide.md](guides/startup-guide.md)** - How to start the system
- **[guides/historical-data-loading.md](guides/historical-data-loading.md)** - Data loading procedures
- **[guides/administration-system.md](guides/administration-system.md)** - Admin features

### API Documentation
- **[api/rest-api.md](api/rest-api.md)** - REST API endpoints
- **[api/websocket-api.md](api/websocket-api.md)** - WebSocket events

### Troubleshooting
- **[troubleshooting/common-issues.md](troubleshooting/common-issues.md)** - Common problems and solutions

## 📊 Key Database Tables

### Integration Monitoring
- `integration_events` - All integration activity
- `pattern_flow_analysis` - Pattern flow metrics (view)

### Pattern Data
- `daily_patterns` - Daily tier patterns
- `intraday_patterns` - Intraday patterns
- `pattern_detections` - All patterns

### User Data
- `symbols` - Stock metadata
- `user_universe` - User preferences
- `cache_entries` - Universe definitions

## 🔍 Quick Commands

### Check System Health
```sql
SELECT * FROM integration_events
WHERE timestamp > NOW() - INTERVAL '1 hour'
ORDER BY timestamp DESC;
```

### Monitor Patterns
```bash
redis-cli subscribe tickstock.events.patterns
python scripts/monitor_system_health.py
```

### Start System
```bash
python start_both_services.py
```

## 🏷️ Documentation Status

### Recently Updated (Sprint 25A)
- ✅ system-architecture.md - Added integration fixes
- ✅ CURRENT_STATUS.md - Created for live status
- ✅ README.md - Updated versions and status
- ✅ sprint25a/ - Complete sprint documentation

### Needs Review
- ⚠️ Some sprint documentation references old sprints (10-13)
- ⚠️ API documentation may need pattern endpoint updates

### Archive Candidates
- 📦 Old sprint folders (pre-Sprint 20)
- 📦 Duplicate project overviews

---

**Pro Tip**: Always check [CURRENT_STATUS.md](CURRENT_STATUS.md) first for the latest system state!