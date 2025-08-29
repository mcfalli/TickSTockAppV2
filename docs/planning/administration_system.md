# TickStock Administration System

**Document Version**: 2.0  
**Last Updated**: 2025-08-29  
**Sprint**: Admin System Complete (Role System + Health Monitor)

## Overview

The TickStock Administration System provides secure, web-based management interfaces for critical system operations. The admin system features a comprehensive role-based access control system with three admin modules, unified navigation, and production-grade security.

## Role-Based Access Control System

### User Roles

| Role | Access Level | Description |
|------|-------------|-------------|
| **`user`** | Regular Pages | Dashboard, account management, market data viewing |
| **`moderator`** | Regular Pages | Future use - currently same as user |
| **`admin`** | Admin Pages Only | User management, historical data, health monitoring |
| **`super`** | **Full Access** | Both regular pages AND all admin functionality |

### Access Patterns
- **Regular users**: Cannot access admin routes (`/admin/*`)
- **Admin users**: Cannot access regular routes (`/`, `/account`, etc.)
- **Super users**: Full system access - ideal for system administrators

### Security Features
- All admin routes protected by `@admin_required` decorator
- Self-protection: Users cannot remove their own admin privileges
- Comprehensive audit logging of all admin actions
- Session management and automatic logout

## Current Admin Modules

### 1. Historical Data Management (`/admin/historical-data`)

**Status**: ✅ Implemented  
**Security Level**: `@admin_required` (admin/super roles)  
**Purpose**: Comprehensive management of historical market data loading and maintenance.

#### Features Implemented:
- **Dashboard Interface**: Real-time data statistics and job monitoring
- **Interactive Data Loading**: 
  - Universe-based loading (top_50, sp500, etc.)
  - Symbol-specific loading with custom lists
  - Flexible timeframes (daily/1-minute data)
  - Configurable date ranges (0.1-10 years)
- **Background Job Management**:
  - Real-time progress tracking
  - Job cancellation capabilities
  - Success/failure monitoring
  - Historical job logs
- **Data Quality Tools**:
  - Duplicate record cleanup
  - Old data removal
  - Data gap detection
  - Quality metrics dashboard
- **Production Integration**:
  - CLI scheduler integration
  - Cron job generation
  - Systemd service support
  - Configuration management

#### Technical Implementation:
- **Routes**: `src/api/rest/admin_historical_data.py`
- **Templates**: `web/templates/admin/historical_data_dashboard.html`
- **Background Processing**: Thread-based job execution
- **Data Source**: PolygonHistoricalLoader integration
- **Job Tracking**: In-memory (production should use Redis/database)

#### Usage Examples:
```bash
# Access via web interface
http://localhost:5000/admin/historical-data

# CLI execution  
python load_historical_data.py --universe top_50 --years 1
python src/jobs/historical_data_scheduler.py --daemon
```

#### Configuration:
- **Config File**: `config/historical_data_scheduler.json`
- **Environment Variables**: `POLYGON_API_KEY`, `DATABASE_URI`
- **Scheduling**: Configurable daily/weekly/monthly jobs

### 2. User Management System (`/admin/users`)

**Status**: ✅ Implemented  
**Security Level**: `@admin_required` (admin/super roles)  
**Purpose**: Comprehensive user account and role management with real-time controls.

#### Features Implemented:
- **User Dashboard**: Paginated user listing with statistics
- **Role Management**: Live role switching (user/moderator/admin/super)
- **Account Controls**: Activate, deactivate, disable user accounts
- **User Statistics**: Total users, active users, verified users, new users (7d)
- **Role Distribution**: Visual breakdown of user roles
- **Safety Features**: Self-protection from role removal
- **Audit Logging**: All admin actions logged with user details
- **Responsive UI**: Bootstrap-based interface with toast notifications

#### Technical Implementation:
- **Routes**: `src/api/rest/admin_users.py` (Blueprint-based)
- **Templates**: `web/templates/admin/users_dashboard.html`
- **Security**: `@admin_required` decorator with role validation
- **AJAX Operations**: Real-time role and status updates
- **Error Handling**: Comprehensive error handling with user feedback

#### Usage:
- Navigate to `/admin/users` 
- View all users with search and pagination
- Click role dropdown to change user roles
- Use action buttons to activate/deactivate accounts
- Monitor changes via toast notifications

### 3. Health Monitor (`/admin/health`)

**Status**: ✅ Implemented  
**Security Level**: `@admin_required` (admin/super roles)  
**Purpose**: Real-time monitoring of TickStockAppV2 ↔ TickStockPL connectivity and system health.

#### Features Implemented:
- **System Health Dashboard**: Real-time status monitoring
- **Database Connectivity**: PostgreSQL/TimescaleDB health checks
- **Redis Integration**: Connection and performance monitoring  
- **WebSocket Status**: Active connections and message throughput
- **TickStockPL Integration**: Cross-system communication health
- **Real-time Updates**: Live status updates and alerts
- **Performance Metrics**: Response times and system performance

#### Technical Implementation:
- **Routes**: `src/api/rest/admin_users.py` (health_dashboard function)
- **Templates**: `web/templates/admin/health_dashboard.html`
- **Real-time**: Socket.IO integration for live updates
- **Health Checks**: Comprehensive system diagnostics
- **Visual Interface**: Color-coded status indicators and charts

## Admin System Navigation

### Unified Admin Navigation
All admin modules feature consistent navigation with:
- **Admin Brand**: "TickStock Admin" with dashboard icon
- **Module Buttons**: Historical Data, User Management, Health Monitor
- **Quick Access**: "Back to App" for regular dashboard
- **Responsive Design**: Works on desktop, tablet, mobile

### Access URLs
- **Historical Data**: http://localhost:5000/admin/historical-data
- **User Management**: http://localhost:5000/admin/users
- **Health Monitor**: http://localhost:5000/admin/health

### Admin User Setup

#### Current Admin User
- **Email**: test@example.com
- **Username**: BobChuckFred
- **Role**: admin → **upgrade to 'super' recommended**

#### User Role Management Scripts
```bash
# View and upgrade users to admin
python scripts/admin/add_admin_system.py

# Quick setup for test@example.com
python scripts/admin/quick_admin_setup.py

# Upgrade existing admin to super (full access)
python scripts/admin/upgrade_to_super.py

# Reset any user's password
python scripts/admin/reset_password.py
```

#### Role Upgrade Recommendation
**Upgrade test@example.com to 'super' role** to access both regular pages and admin pages with the same credentials:

```bash
python scripts/admin/upgrade_to_super.py
# Select test@example.com when prompted
```

## Planned Admin Modules

### 4. Data Quality & Validation (`/admin/data-quality`)

**Status**: 📋 Planned  
**Priority**: Medium  
**Purpose**: Comprehensive data validation and quality assurance.

#### Proposed Features:
- **Data Integrity Checks**: Missing data detection, consistency validation
- **Pattern Validation**: Event detection accuracy, false positive analysis
- **Data Lineage Tracking**: Source tracking, transformation history
- **Quality Metrics Dashboard**: Data completeness, accuracy scores
- **Automated Data Healing**: Gap filling, error correction workflows
- **Data Export/Import**: Bulk operations, backup/restore functions

### 5. Configuration Management (`/admin/config`)

**Status**: 📋 Planned  
**Priority**: Medium  
**Purpose**: Centralized system configuration management.

#### Proposed Features:
- **Environment Configuration**: Runtime settings modification
- **Feature Toggles**: Enable/disable system features dynamically
- **API Configuration**: Rate limits, timeouts, retry policies
- **Alert Configuration**: Notification settings, escalation rules
- **Integration Settings**: Third-party service configurations
- **Backup/Restore**: Configuration versioning and rollback

### 6. Security & Audit (`/admin/security`)

**Status**: 📋 Planned  
**Priority**: High  
**Purpose**: Security monitoring, threat detection, and audit management.

#### Proposed Features:
- **Security Dashboard**: Failed login attempts, suspicious activity
- **Audit Log Viewer**: Comprehensive activity logging and search
- **Access Control Management**: IP whitelisting, rate limiting rules
- **Security Alerts**: Real-time threat notifications
- **Compliance Reporting**: Generate security and audit reports
- **Session Management**: Active session monitoring and termination

## Security Framework

### Current Security Status: ⚠️ NEEDS ENHANCEMENT

**Current Protection**:
- ✅ Flask-Login integration (`@login_required`)
- ✅ Basic authentication required
- ✅ CSRF protection (Flask-WTF)
- ✅ Secure session management

**Required Security Enhancements**:

#### 1. Role-Based Access Control (RBAC)
```python
# TODO: Implement admin role checking
@admin_required  # Custom decorator
def admin_route():
    pass

# User roles hierarchy
ROLES = {
    'user': 0,
    'moderator': 1, 
    'admin': 2,
    'superadmin': 3
}
```

#### 2. Admin-Specific Authentication
```python
# TODO: Multi-factor authentication for admin routes
@admin_mfa_required
def sensitive_admin_route():
    pass
```

#### 3. IP-Based Restrictions
```python
# TODO: Admin IP whitelist
ADMIN_ALLOWED_IPS = ['127.0.0.1', '10.0.0.0/8']
```

#### 4. Enhanced Audit Logging
```python
# TODO: Comprehensive admin action logging
def log_admin_action(user, action, details):
    # Log to secure audit trail
    pass
```

#### 5. Session Security
```python
# TODO: Admin session timeout and monitoring
ADMIN_SESSION_TIMEOUT = 30  # minutes
ADMIN_CONCURRENT_SESSIONS = 1  # limit
```

## Technical Architecture

### Route Organization
```
/admin/                     # Admin base route
├── historical-data/        # Historical data management
├── users/                  # User management (planned)
├── system/                 # System monitoring (planned)
├── data-quality/          # Data validation (planned)
├── config/                # Configuration management (planned)
└── security/              # Security & audit (planned)
```

### Template Structure
```
web/templates/admin/
├── base_admin.html         # Admin layout template (needed)
├── dashboard.html          # Admin dashboard (needed)
├── historical_data_dashboard.html  # ✅ Implemented
├── user_management.html    # Planned
├── system_health.html      # Planned
└── security_audit.html     # Planned
```

### Security Architecture
```
Security Layers:
1. Network Level: IP restrictions, SSL/TLS
2. Application Level: Authentication, authorization
3. Route Level: Role-based access control
4. Action Level: Permission checking
5. Audit Level: Comprehensive logging
```

## Development Standards

### Admin Route Conventions
```python
# Route naming
@app.route('/admin/<module>/<action>')

# Security decorators (all admin routes)
@login_required
@admin_required  # TODO: Implement
@audit_log       # TODO: Implement

# Error handling
try:
    # Admin operation
    pass
except Exception as e:
    log_admin_error(current_user, action, str(e))
    flash(f'Error: {str(e)}', 'error')
    return redirect(admin_dashboard)
```

### Template Standards
```html
<!-- All admin templates extend base_admin.html -->
{% extends "admin/base_admin.html" %}

<!-- Security context in templates -->
{% if current_user.has_admin_role() %}
<!-- Admin content -->
{% endif %}

<!-- Audit trail integration -->
<div data-audit-action="data-load-trigger">
```

### Logging Standards
```python
# Admin action logging
logger.info(f"ADMIN-ACTION: {current_user.username} - {action} - {details}")

# Security event logging
logger.warning(f"ADMIN-SECURITY: {ip} - {event} - {user}")

# Error logging
logger.error(f"ADMIN-ERROR: {user} - {action} - {error}")
```

## Production Deployment

### Security Checklist
- [ ] **Role-based access control implemented**
- [ ] **Admin user roles properly configured**
- [ ] **IP whitelist configured for admin routes**
- [ ] **Multi-factor authentication enabled**
- [ ] **Admin session timeout configured**
- [ ] **Comprehensive audit logging active**
- [ ] **Admin activity monitoring dashboard**
- [ ] **Security alert notifications configured**

### Monitoring Setup
- [ ] **Admin route performance monitoring**
- [ ] **Failed authentication alerting** 
- [ ] **Suspicious activity detection**
- [ ] **Audit log retention and archival**
- [ ] **Admin user activity reporting**

### Access Control Configuration
```bash
# Environment variables for admin security
ADMIN_REQUIRE_MFA=true
ADMIN_SESSION_TIMEOUT=1800  # 30 minutes
ADMIN_IP_WHITELIST="127.0.0.1,10.0.0.0/8"
ADMIN_AUDIT_LOG_LEVEL=INFO
ADMIN_MAX_LOGIN_ATTEMPTS=3
```

## Future Enhancements

### Phase 1: Security Hardening (Priority: Critical)
- Implement role-based access control
- Add multi-factor authentication
- Create comprehensive audit system
- IP-based access restrictions

### Phase 2: Core Admin Modules (Priority: High)
- User management system
- System health monitoring
- Security dashboard and alerting

### Phase 3: Advanced Features (Priority: Medium)
- Data quality management
- Configuration management
- Advanced reporting and analytics

### Phase 4: Enterprise Features (Priority: Future)
- LDAP/SSO integration
- Advanced threat detection
- Compliance reporting automation
- API management interface

## Integration Points

### With TickStock Core System
- **Authentication**: Leverages existing Flask-Login system
- **Database**: Uses same PostgreSQL/TimescaleDB instance
- **Redis**: Shares Redis instance for session management
- **Logging**: Integrates with existing logging infrastructure

### With TickStockPL System
- **Data Pipeline**: Admin controls for TickStockPL job management
- **Configuration**: TickStockPL parameter management
- **Monitoring**: TickStockPL health and performance monitoring

### External Integrations
- **Polygon.io**: API key management, usage monitoring
- **Notification Services**: Slack, email, webhook integrations
- **Monitoring Tools**: Metrics export, alerting integration

## Testing Strategy

### Security Testing
- **Penetration Testing**: Regular security assessments
- **Access Control Testing**: Role and permission validation
- **Session Security Testing**: Timeout and hijacking tests
- **Audit Log Testing**: Log integrity and completeness validation

### Functional Testing
- **Admin Workflow Testing**: End-to-end admin operation tests
- **UI Testing**: Admin interface responsiveness and usability
- **Integration Testing**: Cross-module functionality validation
- **Performance Testing**: Admin system load and stress testing

## Documentation Updates Needed

1. **Security Documentation**: Complete security implementation guide
2. **Admin User Guide**: Step-by-step operational procedures
3. **API Documentation**: Admin API endpoints and authentication
4. **Troubleshooting Guide**: Common admin issues and resolution
5. **Deployment Guide**: Production admin system setup

---

**Next Sprint Tasks**:
1. Implement role-based access control for admin routes
2. Create admin user management system
3. Add comprehensive audit logging
4. Develop system health monitoring dashboard
5. Create admin security documentation and procedures