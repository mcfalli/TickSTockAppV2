"""
WebSocket Models
Shared data models for WebSocket subscription system to avoid circular imports.
"""

from datetime import datetime
from typing import Dict, Any
from dataclasses import dataclass, field


@dataclass
class UserSubscription:
    """User subscription configuration for any TickStockAppV2 feature."""
    user_id: str
    subscription_type: str      # 'tier_patterns', 'market_insights', 'alerts', 'backtest', etc.
    filters: Dict[str, Any]     # Feature-specific filtering criteria
    room_name: str              # WebSocket room assignment
    active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now()
    
    def matches_criteria(self, criteria: Dict[str, Any]) -> bool:
        """Check if subscription matches event criteria."""
        try:
            # Subscription type must match
            if 'subscription_type' in criteria:
                if criteria['subscription_type'] != self.subscription_type:
                    return False
            
            # Check feature-specific filters
            for key, expected_value in criteria.items():
                if key == 'subscription_type':
                    continue  # Already checked above
                
                # Check if user filter contains expected value
                if key in self.filters:
                    user_filter_values = self.filters[key]
                    
                    # Handle both single values and lists
                    if isinstance(user_filter_values, list):
                        if expected_value not in user_filter_values:
                            return False
                    else:
                        if expected_value != user_filter_values:
                            return False
                else:
                    # No filter means user accepts all values for this criteria
                    continue
            
            return True
            
        except Exception:
            return False