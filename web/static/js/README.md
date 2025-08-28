# TickStock JavaScript Organization

## Directory Structure

```
js/
├── core/                           # Application Core Modules
│   ├── app-core.js                # Main application logic, Socket.IO, UI management
│   ├── app-events.js              # Event processing utilities (post-webclean placeholders)
│   ├── app-gridstack.js           # GridStack layout management (simplified post-webclean)
│   └── tickstockpl-integration.js # TickStockPL integration (Sprint 10)
├── services/                       # Business Logic Services
│   └── pattern-alerts-manager.js  # Pattern alerts management system
├── vendor/                         # Third-party Libraries
│   └── libphonenumber-min.js      # Phone number validation library
└── README.md                       # This documentation file
```

## Module Dependencies

### Core Module Loading Order (Critical)
**From index.html template:**
```html
<!-- Load in this exact order -->
<script src="js/core/app-core.js"></script>        <!-- First: Core functionality -->
<script src="js/core/app-events.js"></script>      <!-- Second: Event processing (placeholder) -->
<script src="js/core/app-gridstack.js"></script>   <!-- Last: Layout management -->
```

### Service Integration
- **Pattern Alerts**: Loads `services/pattern-alerts-manager.js` + `core/tickstockpl-integration.js`
- **Authentication**: Uses `vendor/libphonenumber-min.js` for phone validation

## Post-Webclean Changes

### Simplified Architecture
- **app-core.js**: Removed complex event processing, simplified to basic Socket.IO and UI
- **app-events.js**: Converted to placeholder functions for backward compatibility
- **app-gridstack.js**: Simplified to manage single placeholder container
- All modules maintain API compatibility while reducing complexity

### Future Development
- **Components Directory**: Removed (was empty) - create when needed for UI components
- **Utils Directory**: Removed (was empty) - create when needed for utility functions
- **Vendor Directory**: Ready for additional third-party libraries

## Development Guidelines

### Adding New Modules
1. **Core Modules**: Place in `core/` if they're fundamental to app operation
2. **Business Logic**: Place in `services/` if they handle specific business features
3. **Third-party**: Place in `vendor/` and update this documentation
4. **Utilities**: Create `utils/` directory when needed for helper functions

### Module Standards
- Use ES6+ features (const, let, arrow functions, classes)
- Follow existing naming conventions (`app-*.js` for core modules)
- Include comprehensive error handling
- Document public APIs with JSDoc comments
- Maintain backward compatibility when possible

### Performance Considerations
- Core modules loaded synchronously in dependency order
- Service modules loaded only when needed
- Vendor libraries loaded before modules that depend on them
- Consider async loading for non-critical functionality

## Template Integration

### Main Application (index.html)
```html
<!-- Core application modules -->
<script src="{{ url_for('static', filename='js/core/app-core.js') }}"></script>
<script src="{{ url_for('static', filename='js/core/app-events.js') }}"></script>
<script src="{{ url_for('static', filename='js/core/app-gridstack.js') }}"></script>
```

### Dashboard Pages
```html
<!-- TickStockPL integration -->
<script src="{{ url_for('static', filename='js/core/tickstockpl-integration.js') }}"></script>
<!-- Pattern alerts (pattern_alerts.html only) -->
<script src="{{ url_for('static', filename='js/services/pattern-alerts-manager.js') }}"></script>
```

### Authentication Pages
```html
<!-- Phone number validation -->
<script src="{{ url_for('static', filename='js/vendor/libphonenumber-min.js') }}"></script>
```

## Version History

- **v2.1.0** - Button Cleanup & Orphan Removal (Current)
  - Removed app-universe.js and app-filters.js (no longer used)
  - Simplified to core modules: app-core, app-events, app-gridstack
  - Cleaned up orphaned files and references
  - Updated loading order documentation

- **v2.0.0** - Post Webclean Organization
  - Simplified core modules after component removal
  - Cleaned up directory structure  
  - Moved vendor files to proper location
  - Added comprehensive documentation

- **v1.0.0** - Initial Modular Structure
  - Separated core application logic
  - Created service layer
  - Established vendor directory