# TickStock Templates Organization

## Directory Structure

```
templates/
├── README.md                       # This documentation file
├── auth/                          # Authentication Pages
│   ├── change_password.html       # Password change form
│   ├── initiate_password_reset.html # Password reset initiation
│   ├── login.html                 # User login form
│   ├── register.html              # User registration form
│   ├── reset_password.html        # Password reset with SMS verification
│   └── verify_phone.html          # Phone number verification
├── account/                       # Account Management Pages
│   ├── account.html               # Account settings and profile
│   ├── subscription.html          # Subscription management
│   └── subscription_renewal.html  # Subscription renewal for expired users
├── dashboard/                     # Main Application Pages
│   ├── index.html                 # Main dashboard (post-webclean placeholder)
│   ├── health_dashboard.html      # TickStockPL health monitoring
│   ├── backtest_dashboard.html    # Backtesting interface
│   └── pattern_alerts.html        # Pattern alerts management
├── legal/                         # Legal & Compliance Pages
│   ├── terms_and_conditions.html  # Terms of service
│   └── privacy_notice.html        # Privacy policy
├── system/                        # System & Administrative Pages
│   ├── error.html                 # Error page display
│   └── trace.html                 # System tracing (admin only)
├── dev/                          # Development & Testing Pages
│   ├── simple_test.html          # Basic functionality tests
│   ├── chart.html                # Chart development testing
│   └── activity.html             # Activity monitoring (dev only)
└── email/                        # Email Templates
    ├── account_update_email.html  # Account update notifications
    ├── change_password_email.html # Password change confirmations
    ├── disable_email.html         # Account disable notifications
    ├── email_change_notification.html # Email change alerts
    ├── lockout_email.html         # Account lockout notifications
    ├── reset_email.html           # Password reset emails
    ├── subscription_cancelled_email.html # Subscription cancellation
    ├── subscription_reactivated_email.html # Subscription reactivation
    ├── temp_code_email.html       # Temporary verification codes
    ├── verification_email.html    # Email verification
    └── welcome_email.html         # Welcome messages
```

## Flask Route Mapping

### Authentication Routes (auth.py)
```python
# Template Path → Flask Route
'auth/login.html'                    → /login
'auth/register.html'                 → /register
'auth/change_password.html'          → /change_password
'auth/initiate_password_reset.html'  → /initiate_password_reset
'auth/reset_password.html'           → /reset_password/<token>
'auth/verify_phone.html'             → /verify_phone, /renewal_sms_challenge
```

### Main Application Routes (main.py)
```python
# Template Path → Flask Route
'dashboard/index.html'               → / (main dashboard)
'dashboard/health_dashboard.html'    → /health-dashboard
'dashboard/backtest_dashboard.html'  → /backtest-dashboard  
'dashboard/pattern_alerts.html'     → /pattern-alerts
'account/account.html'               → /account
'account/subscription.html'          → /subscription
'account/subscription_renewal.html'  → /subscription_renewal
'legal/terms_and_conditions.html'   → /terms
'legal/privacy_notice.html'          → /privacy
'system/trace.html'                  → /trace/ScoobyDoo123
```

## Template Categories

### 🔐 Authentication Templates (auth/)
**Purpose**: User authentication, registration, and account security
- **Form-heavy templates** with validation and CAPTCHA integration
- **SMS verification** integration for security
- **Error handling** for failed authentication attempts
- **Responsive design** for mobile authentication

**Key Features**:
- CSRF protection on all forms
- Phone number validation (libphonenumber integration)
- Lockout protection against brute force attacks
- Multi-step verification processes

### 👤 Account Management (account/)
**Purpose**: User profile management and subscription handling
- **Account settings** and profile updates
- **Subscription management** with billing information
- **Payment processing** forms and validation
- **Renewal workflows** for expired subscriptions

**Key Features**:
- Secure billing information handling
- Email and phone update workflows
- Subscription status management
- Payment method updates

### 📊 Dashboard Templates (dashboard/)
**Purpose**: Main application interfaces and TickStockPL integration
- **Main dashboard** (post-webclean with placeholder)
- **Health monitoring** for TickStockPL integration
- **Backtesting interface** for strategy testing
- **Pattern alerts** management system

**Post-Webclean Changes**:
- **index.html**: Simplified to single GridStack placeholder
- **Integration ready**: Prepared for TickStockPL data display
- **Real-time capable**: WebSocket integration preserved

### ⚖️ Legal Templates (legal/)
**Purpose**: Legal compliance and policy display
- **Terms of Service** with version tracking
- **Privacy Policy** with GDPR compliance
- **Static content** with legal formatting

### 🔧 System Templates (system/)
**Purpose**: System administration and error handling
- **Error pages** with user-friendly messaging
- **Trace interface** for system debugging (admin only)
- **System monitoring** and diagnostics

### 🧪 Development Templates (dev/)
**Purpose**: Development, testing, and debugging
- **Test interfaces** for feature development
- **Chart testing** for visualization components
- **Activity monitoring** for development metrics

**Note**: These templates should not be accessible in production environments.

### 📧 Email Templates (email/)
**Purpose**: Automated email communications
- **Transactional emails** for account actions
- **Notification emails** for system events
- **Security alerts** for account changes
- **Subscription management** communications

## Template Standards

### HTML Structure
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Page Title - TickStock</title>
    <!-- CSS imports -->
    <link rel="stylesheet" href="{{ url_for('static', filename='css/main.css') }}">
    <!-- Page-specific CSS if needed -->
</head>
<body>
    <!-- Template content -->
    <!-- JavaScript imports at bottom -->
</body>
</html>
```

### CSS Integration
**All templates use the unified CSS system:**
```html
<!-- Single CSS import for all styles -->
<link rel="stylesheet" href="{{ url_for('static', filename='css/main.css') }}">
```

**Page-specific styling is handled through:**
- `pages/auth.css` → Authentication pages
- `pages/dashboard.css` → Dashboard pages
- Component CSS for reusable elements

### JavaScript Integration

#### Core Application (dashboard templates)
```html
<!-- Core modules in dependency order -->
<script src="{{ url_for('static', filename='js/core/app-core.js') }}"></script>
<script src="{{ url_for('static', filename='js/core/app-universe.js') }}"></script>
<script src="{{ url_for('static', filename='js/core/app-filters.js') }}"></script>
<script src="{{ url_for('static', filename='js/core/app-events.js') }}"></script>
<script src="{{ url_for('static', filename='js/core/app-gridstack.js') }}"></script>
```

#### TickStockPL Integration (dashboard templates)
```html
<!-- Sprint 10 integration -->
<script src="{{ url_for('static', filename='js/core/tickstockpl-integration.js') }}"></script>
<!-- Pattern alerts management (pattern_alerts.html only) -->
<script src="{{ url_for('static', filename='js/services/pattern-alerts-manager.js') }}"></script>
```

#### Authentication (auth templates)
```html
<!-- Phone validation -->
<script src="{{ url_for('static', filename='js/vendor/libphonenumber-min.js') }}"></script>
```

## Security Considerations

### CSRF Protection
All forms include CSRF tokens:
```html
{{ csrf.hidden_tag() }}
```

### Input Validation
- Server-side validation in Flask routes
- Client-side validation in forms
- Phone number validation using libphonenumber
- Email validation with verification workflows

### Access Control
- `@login_required` decorators on protected routes
- Session management for authentication state
- Role-based access for admin functions (trace.html)

## Responsive Design

### Mobile-First Approach
All templates use responsive design:
- **Mobile breakpoint**: 480px and below
- **Tablet breakpoint**: 768px and below
- **Desktop breakpoint**: 1024px and above

### GridStack Responsive Behavior
- **Desktop**: Full drag/resize functionality
- **Tablet**: Limited interaction
- **Mobile**: GridStack disabled, stacked layout

## Development Workflow

### Adding New Templates

1. **Determine category**: auth, account, dashboard, legal, system, dev
2. **Create template** in appropriate directory
3. **Update Flask route** to reference new path
4. **Add CSS integration** (main.css import)
5. **Add JavaScript** if needed (following module patterns)
6. **Test responsive behavior**
7. **Update this documentation**

### Template Naming Conventions
- Use descriptive, lowercase names with underscores
- Match Flask route names where possible
- Keep consistency within categories

### Flask Route Updates
When moving templates, update routes in:
- `src/app.py` → Main application routes
- `src/api/rest/main.py` → Dashboard and account routes
- `src/api/rest/auth.py` → Authentication routes

## Error Handling

### Template Not Found Errors
If Flask cannot find a template:
1. **Check file path** in route definition
2. **Verify file exists** in correct directory
3. **Check spelling** and case sensitivity
4. **Restart Flask** if template was recently moved

### Common Issues After Reorganization
- Route references old template paths
- CSS/JS references broken due to path changes
- Template inheritance issues (if using base templates)

## Post-Webclean Architecture

### Simplified Dashboard
- **Single placeholder** container in index.html
- **GridStack framework** preserved for future development
- **Real-time infrastructure** maintained (WebSocket, Socket.IO)
- **Component framework** ready for new additions

### TickStockPL Integration
- **Health monitoring** → health_dashboard.html
- **Backtesting interface** → backtest_dashboard.html
- **Pattern alerts** → pattern_alerts.html
- **Redis integration** ready for data flow

## Future Development

### Template Expansion
- **Base template system** for common layouts
- **Component templates** for reusable UI elements
- **Email template improvements** with modern styling
- **Dark mode support** through CSS variable system

### Integration Opportunities
- **Real-time updates** for dashboard templates
- **Progressive Web App** features
- **Advanced form validation** with real-time feedback
- **Template caching** for performance optimization

## Version History

- **v2.0.0** - Post Webclean Reorganization (Current)
  - Organized templates into logical categories
  - Updated all Flask route references
  - Created comprehensive documentation
  - Simplified dashboard architecture
  - Prepared for TickStockPL integration

- **v1.0.0** - Initial Template Structure
  - Basic pages/ directory organization
  - Email templates in email/ directory
  - Mixed organization without clear categories