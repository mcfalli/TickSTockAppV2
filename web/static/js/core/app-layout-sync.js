// frontend/js/app-layout-sync.js
class LayoutSyncManager {
    constructor(gridManager) {
        this.gridManager = gridManager;
        this.syncInProgress = false;
        this.settingKey = 'gridstack_layout';
        this.isLoading = false;
    }

    async loadLayoutFromDB() {
        
        if (this.isLoading) {
            return;
        }
        this.isLoading = true;
        
        try {
            // Show default layout immediately
            this.gridManager.applyLayout(this.gridManager.getDefaultLayout());

            
            // Load from database if authenticated
            if (window.userContext?.isAuthenticated) {
                
                const response = await fetch(`/api/user/settings/${this.settingKey}`, {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': window.csrfToken
                    },
                    credentials: 'same-origin'
                });


                if (response.ok) {
                    const data = await response.json();
                    
                    // Check multiple possible response structures
                    let layout = null;
                    
                    // Check if layout is directly in setting_value
                    if (data.setting_value?.layout && Array.isArray(data.setting_value.layout)) {
                        layout = data.setting_value.layout;
                    }
                    // Check if setting_value IS the layout array
                    else if (Array.isArray(data.setting_value)) {
                        layout = data.setting_value;
                    }
                    
                    if (layout && layout.length > 0) {
                        this.gridManager.applyLayout(layout);
                    }
                } else if (response.status === 404) {
                    // 404
                } else {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
            } 
            
        } catch (error) {
            this.showError('Failed to load saved layout');
        } finally {
            this.isLoading = false;
        }
    }
    
    async saveLayout(layout) {  // Or rename to just saveLayout
        
        if (this.syncInProgress) {
            return false;
        }
        
        this.syncInProgress = true;
        
        try {
            const payload = {
                setting_value: {
                    layout: layout,
                    updated_at: Date.now()
                }
            };
            
            const response = await fetch(`/api/user/settings/${this.settingKey}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.csrfToken
                },
                credentials: 'same-origin',
                body: JSON.stringify(payload)
            });


            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            return true;
            
        } catch (error) {
            this.showError('Failed to save layout');
            return false;
        } finally {
            this.syncInProgress = false;
        }
    }    

    showError(message) {
        // Use existing toast mechanism with error styling
        const toast = document.createElement('div');
        toast.className = 'layout-save-toast error';
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            bottom: 60px;
            right: 20px;
            background: #dc3545;
            color: white;
            padding: 10px 20px;
            border-radius: 4px;
            z-index: 10000;
            animation: fadeInOut 3s ease-in-out;
        `;
        
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }
}