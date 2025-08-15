# Grid-Stack Quick Reference Guide

## Overview
Grid-Stack is a JavaScript library that enables drag-and-drop, resizable grid layouts. Think of it as giving your users the power to customize their dashboard like desktop widgets.

## Basic Concepts

### The Grid System
- **12 columns** wide (by default)
- **Rows** are dynamically added as needed
- **Cell Height** determines the height of one grid unit (default: 70px)

### Grid Coordinates
```
Column: 0 -------- 6 -------- 11
Row 0:  [Widget A  ] [Widget B  ]
Row 1:  [    Widget C          ]
Row 2:  [Widget D] [Widget E   ]
```

## HTML Structure

### Basic Grid Item
```html
<div class="grid-stack-item" 
     data-gs-width="6"      <!-- Width in columns (1-12) -->
     data-gs-height="3"     <!-- Height in rows -->
     data-gs-x="0"          <!-- X position (0-11) -->
     data-gs-y="0"          <!-- Y position (row) -->
     data-gs-id="my-widget"> <!-- Unique identifier -->
    <div class="grid-stack-item-content">
        <!-- Your widget content here -->
    </div>
</div>
```

## Size & Position Attributes

### Required Attributes
- `data-gs-width` - How many columns wide (1-12)
- `data-gs-height` - How many rows tall
- `data-gs-id` - Unique identifier for saving/loading

### Optional Position
- `data-gs-x` - Starting column (0-11)
- `data-gs-y` - Starting row
- If omitted, grid-stack auto-positions the widget

## Constraints (Min/Max)

### Size Constraints
```html
data-gs-min-width="3"   <!-- Can't be resized smaller than 3 columns -->
data-gs-max-width="8"   <!-- Can't be resized larger than 8 columns -->
data-gs-min-height="2"  <!-- Can't be shorter than 2 rows -->
data-gs-max-height="6"  <!-- Can't be taller than 6 rows -->
```

### Locking Widgets
```html
data-gs-no-resize="true"  <!-- Prevent resizing -->
data-gs-no-move="true"    <!-- Prevent dragging -->
data-gs-locked="true"     <!-- Prevent both -->
```

## Common Patterns

### Full-Width Widget
```html
<div class="grid-stack-item" 
     data-gs-width="12" 
     data-gs-height="2">
```

### Half-Width Widgets (Side by Side)
```html
<!-- Left widget -->
<div class="grid-stack-item" 
     data-gs-width="6" 
     data-gs-height="4"
     data-gs-x="0">

<!-- Right widget -->
<div class="grid-stack-item" 
     data-gs-width="6" 
     data-gs-height="4"
     data-gs-x="6">
```

### Quarter-Width Widgets (4 across)
```html
data-gs-width="3" 
```

## JavaScript Configuration

### Default Layout (for reset button)
```javascript
getDefaultLayout() {
    return [
        {id: 'widget-1', x: 0, y: 0, w: 6, h: 3},
        {id: 'widget-2', x: 6, y: 0, w: 6, h: 3},
        {id: 'widget-3', x: 0, y: 3, w: 12, h: 4}
    ];
}
```

### Priority Order
1. **User's saved layout** (localStorage) - Always wins
2. **HTML attributes** - Initial page load
3. **JS default** - Only for reset
4. **Min/Max constraints** - Always enforced

## Responsive Behavior

### Mobile (≤768px)
- Grid automatically disabled
- Widgets stack vertically
- Full width, natural height

### Desktop (>768px)
- Full grid functionality
- Drag & drop enabled
- Resize handles visible

## Best Practices

### 1. Set Reasonable Minimums
```html
<!-- Good: Gauges need space -->
data-gs-min-width="4" 
data-gs-min-height="3"

<!-- Bad: Too restrictive -->
data-gs-min-width="8"
```

### 2. Use Consistent Defaults
- Set same values in HTML and JS
- Users expect reset to match initial view

### 3. Consider Content
- Text-heavy widgets need minimum widths
- Charts need minimum heights
- Tables benefit from max-heights

### 4. Test Extreme Cases
- All widgets at minimum size
- One widget maximized
- Mobile view fallback

## Common Issues & Solutions

### Widgets Overlapping
- Check x/y positions don't conflict
- Enable `float: true` in options

### Can't Drag Widgets
- Ensure grid isn't disabled
- Check for `data-gs-locked="true"`
- Verify edit mode is active

### Layout Not Saving
- Confirm localStorage is enabled
- Check save/load functions are called
- Verify unique `data-gs-id` on each widget

## TickStock-Specific Examples

### Gauge Widget
```html
<div class="grid-stack-item" 
     data-gs-width="6" 
     data-gs-height="3"
     data-gs-min-width="4"
     data-gs-min-height="3"
     data-gs-id="core-gauge">
```

### Event List (Highs/Lows)
```html
<div class="grid-stack-item" 
     data-gs-width="6" 
     data-gs-height="4"
     data-gs-min-width="3"
     data-gs-min-height="3"
     data-gs-max-height="8"
     data-gs-id="highs">
```

### Percentage Bar
```html
<div class="grid-stack-item" 
     data-gs-width="12" 
     data-gs-height="1"
     data-gs-no-resize="true"
     data-gs-id="percentage-bar">
```