# Fix Required: streaming_routes.py

**File**: `C:\Users\McDude\TickStockAppV2\src\api\streaming_routes.py`

**Problem**: Lines 20-33 define a Flask route `/streaming/` that tries to render the deleted `streaming.html` template. This conflicts with the sidebar JavaScript navigation.

---

## Required Change

**Comment out lines 20-33**:

### BEFORE:
```python
@streaming_bp.route('/')
@login_required
def streaming_dashboard():
    """
    Real-time streaming dashboard page.

    Shows live pattern detections and indicator alerts from market hours streaming.
    """
    try:
        logger.info(f"STREAMING-ROUTE: Dashboard requested by user {current_user.id}")
        return render_template('dashboard/streaming.html')
    except Exception as e:
        logger.error(f"STREAMING-ROUTE-ERROR: Dashboard route failed: {e}")
        return jsonify({'error': 'Failed to load streaming dashboard'}), 500
```

### AFTER:
```python
# @streaming_bp.route('/')
# @login_required
# def streaming_dashboard():
#     """
#     DISABLED: This route conflicts with sidebar navigation (SPA model).
#     Live Streaming is now accessed via sidebar JavaScript, not a Flask route.
#
#     The streaming dashboard is rendered by StreamingDashboardService (JavaScript)
#     when user clicks "Live Streaming" in the sidebar navigation.
#     """
#     pass
```

---

## Why This Fix is Needed

1. **Sidebar navigation uses JavaScript** - The "Live Streaming" link loads content via `StreamingDashboardService` class
2. **No template needed** - The UI is rendered dynamically by JavaScript, not Flask
3. **Route causes 404** - The route tries to render `streaming.html` which we deleted
4. **Proper pattern** - Sprint 33 Phase 5 intended SPA model, not standalone page

---

## After Making This Change

1. **Save the file**
2. **Restart TickStockAppV2**:
   ```bash
   # Stop current services (Ctrl+C)
   # Restart
   python start_all_services.py
   ```

3. **Test navigation**:
   - Go to: `http://localhost:5000/dashboard`
   - Click "Live Streaming" in sidebar
   - Should load JavaScript dashboard (not a 404)

---

## Alternative: Complete Removal

If you prefer to completely remove the function instead of commenting:

```python
# Streaming dashboard is now part of SPA - see sidebar-navigation-controller.js
# and streaming-dashboard.js for the client-side implementation
```

Then delete lines 20-33 entirely.

---

**Status**: Waiting for manual fix (permissions prevent automatic editing)
