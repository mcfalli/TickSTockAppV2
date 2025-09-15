# TickStockAppV2 Troubleshooting Guide

This directory contains comprehensive troubleshooting documentation for common issues encountered in the TickStock system.

## **Available Troubleshooting Guides**

### **Integration & Communication Issues**
- **[`redis_subscriber_zero_issue.md`](redis_subscriber_zero_issue.md)** - Redis Event Subscriber not running, pattern data pipeline failure

## **Quick Diagnostic Commands**

### **Redis Integration Health**
```bash
# Check Redis subscriber count (should be 1 when TickStockApp running)
redis-cli pubsub numsub tickstock.events.patterns

# Monitor Redis channel activity
redis-cli monitor | grep "tickstock.events.patterns"

# Test Redis connectivity
redis-cli ping
```

### **Service Status**
```bash
# Check if TickStockApp is running
tasklist | findstr python     # Windows
ps aux | grep tickstock       # Linux/Mac

# Check pattern table counts
python -c "
import psycopg2
conn = psycopg2.connect('postgresql://app_readwrite:LJI48rUEkUpe6e@localhost:5433/tickstock')
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM daily_patterns')
print(f'Daily patterns: {cur.fetchone()[0]}')
cur.execute('SELECT COUNT(*) FROM intraday_patterns')  
print(f'Intraday patterns: {cur.fetchone()[0]}')
conn.close()
"
```

### **Database Health**
```bash
# Check TimescaleDB hypertable status
PGPASSWORD=LJI48rUEkUpe6e psql -h localhost -p 5433 -U app_readwrite -d tickstock -c "
SELECT hypertable_name, num_chunks FROM timescaledb_information.hypertables 
WHERE hypertable_name IN ('daily_patterns', 'intraday_patterns');
"
```

## **Common Issues & Quick Fixes**

### **🚨 Redis Subscriber Count = 0**
**Symptom**: Pattern events not flowing, Multi-Tier Dashboard empty  
**Quick Fix**: Start TickStockApp service (`python src/app.py`)  
**Details**: See [`redis_subscriber_zero_issue.md`](redis_subscriber_zero_issue.md)

### **🚨 Database Insert Errors**
**Symptom**: TimescaleDB hypertables rejecting pattern inserts  
**Quick Fix**: Create initial hypertable chunks with test records  
**Details**: See [`redis_subscriber_zero_issue.md`](redis_subscriber_zero_issue.md#step-1-fix-database-configuration)

### **🚨 WebSocket Connection Issues**
**Symptom**: Frontend not receiving real-time updates  
**Quick Check**: Verify TickStockApp running and Redis Event Subscriber active  
**Log Location**: Check `logs/` directory for WebSocket errors

## **Escalation Guidelines**

### **When to Use This Documentation**
1. **First Response**: Check relevant troubleshooting guide
2. **Quick Diagnostics**: Run diagnostic commands from guide
3. **Apply Solution**: Follow step-by-step resolution process

### **When to Escalate**
- Issue not covered in existing troubleshooting guides
- Solution steps don't resolve the problem
- Multiple system components failing simultaneously
- Performance degradation beyond documented thresholds

## **Contributing New Troubleshooting Guides**

### **Guide Format**
```markdown
# Issue Title - Component Troubleshooting

**Issue**: Brief description
**Root Cause**: What caused the problem  
**Resolution**: How it was fixed
**Date Resolved**: When issue was resolved
**Affected Components**: What parts of system were impacted

## Issue Summary
## Root Cause Analysis  
## Solution Steps
## Diagnostic Commands for Future Use
## Prevention Measures
## Success Metrics
```

### **File Naming Convention**
- Use descriptive names: `component_symptom_issue.md`
- Include date in content, not filename
- Focus on root cause, not just symptoms
- Example: `redis_subscriber_zero_issue.md`

---

**Last Updated**: September 12, 2025  
**Directory Created**: September 12, 2025  
**Documentation Standard**: Comprehensive root cause analysis with prevention measures