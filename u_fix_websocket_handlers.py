#!/usr/bin/env python3
"""
Add missing WebSocket event handlers to frontend JavaScript
"""

from pathlib import Path

def fix_websocket_handlers():
    """Add missing WebSocket event handlers to frontend."""
    base_path = Path(r"C:\Users\McDude\TickStockAppV2")
    
    print("=" * 60)
    print("FIXING WEBSOCKET EVENT HANDLERS")
    print("=" * 60)
    
    # Find the main socket connection file
    js_files = list((base_path / "web/static/js").rglob("*.js")) if (base_path / "web/static/js").exists() else []
    
    # Events that need handlers
    missing_events = ['user_status_response', 'pong', 'test_event', 'error']
    
    # JavaScript handler template
    handler_template = """
// Auto-generated handlers for missing WebSocket events
socket.on('user_status_response', function(data) {
    console.log('User status response:', data);
    // TODO: Implement user status handling
    if (data.status) {
        updateUserStatus(data.status);
    }
});

socket.on('pong', function(data) {
    // Heartbeat response - keeps connection alive
    console.debug('Pong received:', data);
    lastPongTime = Date.now();
});

socket.on('test_event', function(data) {
    console.log('Test event received:', data);
    // Development/debugging event
    if (window.DEBUG_MODE) {
        displayDebugMessage('Test Event', data);
    }
});

socket.on('error', function(error) {
    console.error('WebSocket error:', error);
    // Display user-friendly error message
    if (error.message) {
        showNotification('Connection Error: ' + error.message, 'error');
    }
    // Attempt reconnection if needed
    if (error.code === 'CONNECTION_LOST') {
        setTimeout(() => {
            console.log('Attempting to reconnect...');
            socket.connect();
        }, 5000);
    }
});

// Helper functions if they don't exist
if (typeof updateUserStatus === 'undefined') {
    function updateUserStatus(status) {
        const statusElement = document.getElementById('user-status');
        if (statusElement) {
            statusElement.textContent = status;
            statusElement.className = 'status-' + status.toLowerCase();
        }
    }
}

if (typeof showNotification === 'undefined') {
    function showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = 'notification notification-' + type;
        notification.textContent = message;
        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), 5000);
    }
}

if (typeof displayDebugMessage === 'undefined') {
    function displayDebugMessage(title, data) {
        console.log(`[DEBUG] ${title}:`, data);
    }
}
"""
    
    # Find the best file to add handlers to
    target_file = None
    for js_file in js_files:
        content = js_file.read_text(encoding='utf-8')
        if 'socket.on(' in content or 'io(' in content or 'io.connect(' in content:
            target_file = js_file
            print(f"  Found WebSocket file: {js_file.name}")
            break
    
    if not target_file:
        # Create a new handlers file
        target_file = base_path / "web/static/js/websocket-handlers.js"
        target_file.parent.mkdir(parents=True, exist_ok=True)
        print(f"  Creating new handler file: {target_file}")
    
    try:
        # Read existing content
        if target_file.exists():
            content = target_file.read_text(encoding='utf-8')
            
            # Check which handlers are already present
            already_has = []
            for event in missing_events:
                if f"socket.on('{event}'" in content or f'socket.on("{event}"' in content:
                    already_has.append(event)
                    print(f"  ✓ Handler for '{event}' already exists")
            
            if len(already_has) < len(missing_events):
                # Add missing handlers
                content += "\n" + handler_template
                target_file.write_text(content, encoding='utf-8')
                print(f"  ✅ Added missing WebSocket handlers to {target_file.name}")
        else:
            # Create new file with handlers
            target_file.write_text(handler_template, encoding='utf-8')
            print(f"  ✅ Created {target_file.name} with WebSocket handlers")
            
    except Exception as e:
        print(f"  ❌ Failed to update WebSocket handlers: {e}")
    
    print("\n" + "=" * 60)
    print("WebSocket handler fix complete!")
    print("=" * 60)

if __name__ == "__main__":
    fix_websocket_handlers()