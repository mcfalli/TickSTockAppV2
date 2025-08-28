# TickStock CSS Organization

## Directory Structure

```
css/
├── main.css                        # Main CSS entry point - import this in templates
├── base/                          # Foundation & Design System
│   ├── reset.css                  # CSS reset and base element styling
│   └── variables.css              # Design tokens, colors, spacing, typography
├── layout/                        # Structural Layout
│   ├── grid.css                   # GridStack integration and placeholder content
│   └── layout.css                 # Main application layout and structure
├── components/                    # Reusable UI Components
│   ├── gauges.css                 # GridStack items and placeholder styling (post-webclean)
│   ├── modals.css                 # Modal dialogs and overlays
│   ├── navbar.css                 # Navigation bar and header
│   ├── status-bar.css             # Footer status bar and controls
│   └── user-menu.css              # User dropdown and settings menu
├── pages/                         # Page-specific Styles
│   ├── auth.css                   # Authentication pages (login, register, etc.)
│   └── dashboard.css              # Dashboard pages (health, backtest, pattern alerts)
├── utilities/                     # Helper Classes & Processing
│   ├── animations.css             # Animation utilities and keyframes
│   ├── dialogs.css                # Dialog manager and system dialogs
│   ├── events.css                 # Event processing utilities (post-webclean placeholders)
│   └── filters.css                # Filter modal and filtering UI components
└── README.md                       # This documentation file
```

## CSS Loading Strategy

### Single Import Pattern
**All templates should use only:**
```html
<link rel="stylesheet" href="{{ url_for('static', filename='css/main.css') }}">
```

### Import Order in main.css (Critical)
```css
/* 1. Foundation */
@import url('base/variables.css');     /* Design tokens first */
@import url('base/reset.css');         /* CSS reset */

/* 2. Layout */
@import url('layout/layout.css');      /* Main structure */
@import url('layout/grid.css');        /* GridStack system */

/* 3. Components */
@import url('components/navbar.css');   /* Navigation */
@import url('components/user-menu.css'); /* User controls */
@import url('components/gauges.css');   /* GridStack items */
@import url('components/status-bar.css'); /* Footer */
@import url('components/modals.css');   /* Dialogs */

/* 4. Pages */
@import url('pages/auth.css');         /* Auth pages */
@import url('pages/dashboard.css');    /* Dashboard pages */

/* 5. Utilities */
@import url('utilities/events.css');   /* Event processing */
@import url('utilities/filters.css');  /* Filtering UI */
@import url('utilities/dialogs.css');  /* System dialogs */
@import url('utilities/animations.css'); /* Animations */
```

## Post-Webclean Architecture

### Simplified Component System
After the webclean process, the CSS architecture was simplified:

#### Removed Components
- **Velocity dashboard styles** - No longer needed
- **Complex event grid layouts** - Simplified to placeholders
- **8 market data components** - Reduced to single placeholder
- **Percentage bar styling** - Component removed

#### Preserved Components
- **GridStack framework** - Base functionality maintained
- **Authentication UI** - Full auth system styling preserved  
- **Navigation system** - Complete navbar and user menu
- **Modal system** - All dialogs and overlays functional
- **Status indicators** - Footer and connection status

### Current State
- **Single placeholder container** with drag/resize capability
- **Clean foundation** ready for new component development
- **Dark mode preparation** via CSS custom properties
- **Scalable architecture** for future component additions

## Design System

### CSS Custom Properties (variables.css)
```css
/* Colors */
--color-primary: #2196f3;
--color-background-primary: #fff;
--color-text-primary: #333;

/* Spacing */
--spacing-xs: 4px;
--spacing-sm: 8px;
--spacing-md: 16px;
--spacing-lg: 24px;

/* Typography */
--font-weight-normal: 400;
--font-weight-bold: 700;

/* Layout */
--border-radius-sm: 4px;
--border-radius-md: 8px;
```

### Theming Strategy
The CSS architecture is prepared for theming:
- All colors use CSS custom properties
- Component styles reference design tokens
- Ready for dark mode implementation via property overrides

## Component Guidelines

### Writing New Components
1. **Use CSS custom properties** for all colors, spacing, and typography
2. **Follow BEM methodology** for class naming
3. **Include responsive behavior** with mobile-first approach
4. **Add to appropriate directory** (components/ for reusable, pages/ for specific)
5. **Import in main.css** in the correct section

### Component Structure Template
```css
/*
===============================================================================
COMPONENT NAME - BRIEF DESCRIPTION
===============================================================================
*/

.component-name {
    /* Base styles using design tokens */
    color: var(--color-text-primary);
    padding: var(--spacing-md);
}

.component-name__element {
    /* BEM element styles */
}

.component-name--modifier {
    /* BEM modifier styles */
}

/* Responsive behavior */
@media (max-width: 768px) {
    .component-name {
        padding: var(--spacing-sm);
    }
}
```

## Page-Specific Styles

### Authentication Pages (pages/auth.css)
Used by: login.html, register.html, reset_password.html, etc.
- Form styling and validation states
- Authentication layout and responsive behavior
- Error message styling

### Dashboard Pages (pages/dashboard.css)  
Used by: health_dashboard.html, backtest_dashboard.html, pattern_alerts.html
- Dashboard-specific layouts
- Chart integration styling
- Dashboard navigation and controls

## Responsive Design

### Breakpoint Strategy
```css
/* Mobile First Approach */
.component { /* Mobile styles (default) */ }

@media (min-width: 768px) {
    .component { /* Tablet styles */ }
}

@media (min-width: 1024px) {
    .component { /* Desktop styles */ }
}

@media (min-width: 1400px) {
    .component { /* Large desktop styles */ }
}
```

### GridStack Responsive Behavior
- **Desktop**: Full drag/resize functionality
- **Tablet**: Limited interaction
- **Mobile**: GridStack disabled, stacked layout

## Performance Optimizations

### CSS Containment
```css
.events-list {
    contain: layout style paint;
}
```

### Hardware Acceleration
```css
.animate-pulse,
.modal {
    will-change: transform;
    transform: translateZ(0);
}
```

### Print Styles
```css
@media print {
    .navbar, .status-bar, .loading-overlay {
        display: none !important;
    }
}
```

## Development Workflow

### Adding New Styles
1. **Determine category**: component, page-specific, or utility
2. **Create/modify file** in appropriate directory
3. **Use design tokens** from variables.css
4. **Add import** to main.css in correct section
5. **Test responsive behavior**
6. **Update this documentation** if needed

### CSS Organization Principles
- **Single responsibility** - Each file has one clear purpose  
- **Design token usage** - All values reference variables
- **Cascade respect** - Imports ordered for proper cascade
- **Performance first** - Optimized for fast loading
- **Maintainability** - Clear structure and naming

## Browser Support

### Modern CSS Features Used
- **CSS Custom Properties** (IE 11+ with polyfill)
- **CSS Grid** (with flexbox fallbacks)
- **CSS Containment** (progressive enhancement)

### Fallback Strategy
- Flexbox fallbacks for CSS Grid layouts
- Standard properties alongside custom properties
- Progressive enhancement for advanced features

## Future Development

### Planned Additions
- **utilities/themes.css** - Dark mode implementation
- **components/forms.css** - Extract form components from auth.css
- **components/loading.css** - Loading state components
- **components/charts.css** - Chart integration styling

### Theme System Implementation (v4.0.0)

**Complete light/dark theme system with toggle button:**

```css
/* Theme classes applied to <html> and <body> elements */
.theme-light {
    --color-background-primary: #ffffff !important;
    --color-background-secondary: #f8f9fa !important;
    --color-text-primary: #333333 !important;
}

.theme-dark {
    --color-background-primary: #1a1a1a !important;
    --color-background-secondary: #2d2d2d !important;
    --color-text-primary: #ffffff !important;
}

/* Bootstrap override system with high specificity */
html.theme-light body .navbar,
.theme-light .navbar {
    background-color: #3a3a3a !important;
    color: #ffffff !important;
}
```

**JavaScript Integration:**
- Toggle button in navbar with theme icon switching (🌙/☀️)
- LocalStorage persistence (`tickstock-theme`)
- System preference detection (`prefers-color-scheme`)
- Smooth 0.3s transition animations
- Theme classes applied to both `<html>` and `<body>` elements

## Version History

- **v4.0.0** - Complete Theme System Implementation (Current)
  - **PRODUCTION READY**: Full light/dark theme switching with toggle button
  - **Bootstrap Override System**: High-specificity CSS to override external frameworks
  - **Theme Persistence**: LocalStorage integration with system preference detection
  - **Component Coverage**: All major components (navbar, status bar, body, cards) themed
  - **Professional UI**: Consistent color scheme matching top/bottom navigation bars
  - **Smooth Transitions**: 0.3s animation effects for theme switching
  - **Accessibility**: Proper contrast ratios and screen reader support

- **v3.0.0** - Dark Theme Ready & Button Cleanup
  - Comprehensive dark/light theme support in variables.css
  - Removed unused universe and filter modal styles
  - Cleaned orphaned CSS selectors and rules
  - Enhanced modal system for Button1/Button2 placeholders
  - Optimized CSS architecture for theming

- **v2.0.0** - Post Webclean Organization
  - Moved main.css to root directory
  - Created pages/ directory for page-specific styles
  - Moved UI components to components/ directory
  - Removed post-webclean unused files (velocity.css)
  - Added comprehensive documentation

- **v1.0.0** - Initial Modular Structure
  - Separated CSS into logical modules
  - Established import strategy in main.css
  - Created design token system in variables.css