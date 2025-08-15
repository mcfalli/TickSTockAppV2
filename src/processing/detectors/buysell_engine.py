import time
from typing import Dict, List, Any, Optional
from datetime import datetime
import pytz
from config.logging_config import get_domain_logger, LogDomain

logger = get_domain_logger(LogDomain.CORE, 'buysell_tracker')

class BuySellTracker:
    """
    Base class for buy/sell pressure trackers.
    Provides common functionality for market pressure calculations.
    """
    
    def __init__(self, config, tracker_name="generic"):
        """
        Initialize the buy/sell tracker base class.
        
        Args:
            config: Application configuration dictionary
            tracker_name: Name identifier for this tracker
        """
        self.config = config
        self.tracker_name = tracker_name
        
        # Set window size for calculations - subclasses should override config key name
        self.window_seconds = config.get(f'BUYSELL_{tracker_name.upper()}_WINDOW', 10.0)
        
        # Activity level thresholds - controllable through config
        self.activity_threshold_low = config.get(f'BUYSELL_{tracker_name.upper()}_THRESHOLD_LOW', 5000000)
        self.activity_threshold_moderate = config.get(f'BUYSELL_{tracker_name.upper()}_THRESHOLD_MODERATE', 10000000)
        self.activity_threshold_high = config.get(f'BUYSELL_{tracker_name.upper()}_THRESHOLD_HIGH', 20000000)

        # Activity level scale factor - allows quick adjustment of all thresholds
        self.activity_scale_factor = config.get(f'BUYSELL_{tracker_name.upper()}_SCALE_FACTOR', 1.0)
    
    def calculate_net_score(self, buying_count: int, selling_count: int, activity_count: int) -> float:
        """
        Calculate net buying/selling pressure score with database constraint validation.
        🚨 FIXED: Clamps to valid database range (-10 to +10).
        
        Args:
            buying_count: Volume-weighted buying activity
            selling_count: Volume-weighted selling activity
            activity_count: Total volume activity
            
        Returns:
            float: Net score clamped to database valid range (-10 to +10)
        """
        if activity_count == 0:
            return 0.0
        
        # Calculate raw net score
        raw_net_score = ((buying_count - selling_count) / activity_count) * 100
        
        # 🚨 CRITICAL: Clamp to database constraint range (-10 to +10)
        clamped_net_score = max(-10.0, min(10.0, raw_net_score))
        
        return round(clamped_net_score, 2)
    
    def calculate_activity_level(self, activity_count: int) -> str:
        """
        Determine activity level based on volume with auto-scaling.
        
        Args:
            activity_count: Total volume activity
            
        Returns:
            str: Activity level description
        """
        # Base thresholds from config
        base_low = self.activity_threshold_low
        base_moderate = self.activity_threshold_moderate
        base_high = self.activity_threshold_high
        
        # Auto-scaling approach - ensure we get a mix of activity levels
        # Based on recent history of calculations
        tracker_data = getattr(self, f"buysell_{self.tracker_name.lower()}", {})
        recent_counts = [calc.get('activity_count', 0) for calc in tracker_data.get('calculations', [])]
        
        # If we have some history, use it to calibrate
        if recent_counts:
            max_recent = max(recent_counts) if recent_counts else activity_count
            avg_recent = sum(recent_counts) / len(recent_counts) if recent_counts else activity_count
            
            # Adaptive thresholds based on recent history
            dynamic_low = avg_recent * 0.5  # 50% of average is "low"
            dynamic_moderate = avg_recent * 1.0  # Average is "moderate"
            dynamic_high = avg_recent * 2.0  # 2x average is "high"
            
            # Use the larger of our dynamic or scaled thresholds
            effective_low = max(dynamic_low, base_low * self.activity_scale_factor)
            effective_moderate = max(dynamic_moderate, base_moderate * self.activity_scale_factor)
            effective_high = max(dynamic_high, base_high * self.activity_scale_factor)
        else:
            # Without history, start with basic scaled thresholds
            effective_low = base_low * self.activity_scale_factor
            effective_moderate = base_moderate * self.activity_scale_factor
            effective_high = base_high * self.activity_scale_factor
        
        # Determine level using effective thresholds
        if activity_count < effective_low:
            return "low"
        elif activity_count < effective_moderate:
            return "moderate"
        elif activity_count < effective_high:
            return "high"
        else:
            return "extreme"
    '''
    def get_latest_metrics(self) -> Dict[str, Any]:
        """
        Get the latest calculated metrics.
        
        Returns:
            dict: Latest pressure metrics or empty dict if no calculations yet
        """
        tracker_data = getattr(self, f"buysell_{self.tracker_name.lower()}", {})
        calculations = tracker_data.get("calculations", [])
        if not calculations:
            return {}
        return calculations[-1]
    def get_metrics_history(self) -> List[Dict[str, Any]]:
        """
        Get history of calculated metrics.
        
        Returns:
            list: List of metric dictionaries
        """
        tracker_data = getattr(self, f"buysell_{self.tracker_name.lower()}", {})
        return tracker_data.get("calculations", [])
    '''
