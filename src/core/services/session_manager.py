"""
Session Manager - Sprint 6C Implementation
Handles market session transitions, state management, and session-based resets.
Extracted from src.core.services and health_monitor
"""

import logging
import time
from datetime import datetime, date
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from config.logging_config import get_domain_logger, LogDomain
from src.shared.utils import get_eastern_time
import pytz

logger = get_domain_logger(LogDomain.CORE, 'session_manager')

class MarketSession(Enum):
    """Market session types."""
    PRE = "PRE"
    REGULAR = "REGULAR"
    AFTER = "AFTER"
    CLOSED = "CLOSED"
    UNKNOWN = "UNKNOWN"

@dataclass
class SessionTransition:
    """Represents a market session transition."""
    from_session: str
    to_session: str
    transition_time: float
    eastern_time: datetime
    affected_components: List[str]
    success: bool = True
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []

class SessionManager:
    """
    Manages market session transitions and coordinates session-based resets.
    """
    
    def __init__(self, config):
        """Initialize session manager with configuration."""
        self.config = self._extract_session_config(config)
        
        # Timezone setup
        self.eastern_tz = pytz.timezone(self.config['MARKET_TIMEZONE'])
        
        # Session tracking
        self.current_session = MarketSession.UNKNOWN
        self.last_session_check = 0
        self.session_history = []
        
        # Component callbacks for session changes
        self.session_change_callbacks = {}
        
        # Initialize current session
        self._update_current_session()
        
        logger.info(f"✅ SessionManager initialized - Current: {self.current_session.value}")
    
    def _extract_session_config(self, config: Dict) -> Dict:
        """Extract session manager specific configuration."""
        return {
            'MARKET_TIMEZONE': config.get('MARKET_TIMEZONE', 'US/Eastern'),
            'SESSION_CHECK_INTERVAL': config.get('SESSION_CHECK_INTERVAL', 60),
            'PRE_MARKET_START': config.get('PRE_MARKET_START', (4, 0)),
            'REGULAR_MARKET_START': config.get('REGULAR_MARKET_START', (9, 30)),
            'REGULAR_MARKET_END': config.get('REGULAR_MARKET_END', (16, 0)),
            'AFTER_MARKET_END': config.get('AFTER_MARKET_END', (20, 0)),
            'ENABLE_WEEKEND_SESSIONS': config.get('ENABLE_WEEKEND_SESSIONS', False)
        }
    
    def determine_session(self, check_time: Optional[datetime] = None) -> MarketSession:
        """
        Determine market session based on time.
        """
        if check_time is None:
            check_time = get_eastern_time()
        
        # Check if weekend (unless weekend sessions enabled)
        if not self.config['ENABLE_WEEKEND_SESSIONS']:
            weekday = check_time.weekday()
            if weekday >= 5:  # Saturday = 5, Sunday = 6
                return MarketSession.CLOSED
        
        hour, minute = check_time.hour, check_time.minute
        
        # Pre-market: 4:00 AM - 9:30 AM ET
        pre_start_hour, pre_start_min = self.config['PRE_MARKET_START']
        reg_start_hour, reg_start_min = self.config['REGULAR_MARKET_START']
        
        if (hour > pre_start_hour or (hour == pre_start_hour and minute >= pre_start_min)) and \
           (hour < reg_start_hour or (hour == reg_start_hour and minute < reg_start_min)):
            return MarketSession.PRE
        
        # Regular market: 9:30 AM - 4:00 PM ET
        reg_end_hour, reg_end_min = self.config['REGULAR_MARKET_END']
        
        if (hour > reg_start_hour or (hour == reg_start_hour and minute >= reg_start_min)) and \
           (hour < reg_end_hour or (hour == reg_end_hour and minute < reg_end_min)):
            return MarketSession.REGULAR
        
        # After-market: 4:00 PM - 8:00 PM ET
        after_end_hour, after_end_min = self.config['AFTER_MARKET_END']
        
        if (hour >= reg_end_hour) and (hour < after_end_hour or (hour == after_end_hour and minute < after_end_min)):
            return MarketSession.AFTER
        
        # Otherwise closed
        return MarketSession.CLOSED
    
    def check_session_transition(self) -> Optional[SessionTransition]:
        """
        Check if a session transition has occurred.
        Returns SessionTransition if transition detected, None otherwise.
        """
        current_time = time.time()
        
        # Rate limit session checks
        if current_time - self.last_session_check < self.config['SESSION_CHECK_INTERVAL']:
            return None
        
        self.last_session_check = current_time
        
        # Determine current session
        eastern_time = get_eastern_time()
        new_session = self.determine_session(eastern_time)
        
        # Check if session changed
        if new_session != self.current_session:
            old_session = self.current_session
            self.current_session = new_session
            
            transition = SessionTransition(
                from_session=old_session.value,
                to_session=new_session.value,
                transition_time=current_time,
                eastern_time=eastern_time,
                affected_components=[]
            )
            
            logger.info(f"🔄 SESSION TRANSITION: {old_session.value} → {new_session.value}")
            
            # Execute callbacks
            self._execute_session_callbacks(transition)
            
            # Add to history
            self.session_history.append(transition)
            if len(self.session_history) > 100:
                self.session_history.pop(0)
            
            return transition
        
        return None
    
    def register_session_callback(self, component_name: str, callback: Callable):
        """
        Register a callback to be executed on session changes.
        Callback should accept (old_session, new_session, transition_time).
        """
        self.session_change_callbacks[component_name] = callback
        logger.info(f"📥 Registered session callback: {component_name}")
    '''
    def unregister_session_callback(self, component_name: str):
        """Unregister a session callback."""
        if component_name in self.session_change_callbacks:
            del self.session_change_callbacks[component_name]
    '''
    def _execute_session_callbacks(self, transition: SessionTransition):
        """Execute all registered session callbacks."""
        for component_name, callback in self.session_change_callbacks.items():
            try:
                callback(
                    transition.from_session,
                    transition.to_session,
                    transition.transition_time
                )
                transition.affected_components.append(component_name)
                
            except Exception as e:
                error_msg = f"Session callback failed for {component_name}: {str(e)}"
                logger.error(f"❌ {error_msg}")
                transition.errors.append(error_msg)
                transition.success = False
        
        if transition.affected_components:
            logger.info(f"✅ Session callbacks executed: {len(transition.affected_components)} components")
    
    def _update_current_session(self):
        """Update the current session on initialization."""
        self.current_session = self.determine_session()
        self.last_session_check = time.time()
    
    '''
    def get_session_info(self) -> Dict[str, Any]:
        """Get comprehensive session information."""
        eastern_time = get_eastern_time()
        current_session = self.determine_session(eastern_time)
        
        # Calculate time to next session
        time_to_next = self._calculate_time_to_next_session(eastern_time, current_session)
        
        return {
            'current_session': current_session.value,
            'eastern_time': eastern_time.isoformat(),
            'session_start_time': self._get_session_start_time(current_session, eastern_time),
            'session_end_time': self._get_session_end_time(current_session, eastern_time),
            'time_to_next_session': time_to_next,
            'is_trading_day': eastern_time.weekday() < 5,
            'registered_callbacks': list(self.session_change_callbacks.keys()),
            'last_transition': self.session_history[-1] if self.session_history else None,
            'timestamp': time.time()
        }
    '''
    def _calculate_time_to_next_session(self, current_time: datetime, 
                                      current_session: MarketSession) -> Dict[str, Any]:
        """Calculate time until next session transition."""
        if current_session == MarketSession.PRE:
            target_hour, target_min = self.config['REGULAR_MARKET_START']
            next_session = "REGULAR"
        elif current_session == MarketSession.REGULAR:
            target_hour, target_min = self.config['REGULAR_MARKET_END']
            next_session = "AFTER"
        elif current_session == MarketSession.AFTER:
            target_hour, target_min = self.config['AFTER_MARKET_END']
            next_session = "CLOSED"
        else:  # CLOSED
            target_hour, target_min = self.config['PRE_MARKET_START']
            next_session = "PRE"
        
        # Calculate target time
        target_time = current_time.replace(
            hour=target_hour, minute=target_min, second=0, microsecond=0
        )
        
        # If target is in the past, add a day
        if target_time <= current_time:
            from datetime import timedelta
            target_time += timedelta(days=1)
        
        # Calculate difference
        time_diff = target_time - current_time
        seconds_until = int(time_diff.total_seconds())
        
        return {
            'next_session': next_session,
            'seconds_until': seconds_until,
            'minutes_until': round(seconds_until / 60, 1),
            'target_time': target_time.isoformat()
        }
    def _get_session_start_time(self, session: MarketSession, 
                                reference_time: datetime) -> Optional[str]:
        """Get the start time of the current session."""
        if session == MarketSession.PRE:
            hour, minute = self.config['PRE_MARKET_START']
        elif session == MarketSession.REGULAR:
            hour, minute = self.config['REGULAR_MARKET_START']
        elif session == MarketSession.AFTER:
            hour, minute = self.config['REGULAR_MARKET_END']
        else:
            return None
        
        start_time = reference_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
        return start_time.isoformat()
    
    def _get_session_end_time(self, session: MarketSession, 
                            reference_time: datetime) -> Optional[str]:
        """Get the end time of the current session."""
        if session == MarketSession.PRE:
            hour, minute = self.config['REGULAR_MARKET_START']
        elif session == MarketSession.REGULAR:
            hour, minute = self.config['REGULAR_MARKET_END']
        elif session == MarketSession.AFTER:
            hour, minute = self.config['AFTER_MARKET_END']
        else:
            return None
        
        end_time = reference_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
        return end_time.isoformat()
    
    '''
    def get_trading_day_info(self, check_date: Optional[date] = None) -> Dict[str, Any]:
        """Get trading day information."""
        if check_date is None:
            check_date = datetime.now(self.eastern_tz).date()
        
        # Check if weekend
        weekday = check_date.weekday()
        is_weekend = weekday >= 5
        
        # TODO: Add holiday calendar integration
        is_holiday = False
        
        return {
            'date': check_date.isoformat(),
            'weekday': check_date.strftime('%A'),
            'is_trading_day': not is_weekend and not is_holiday,
            'is_weekend': is_weekend,
            'is_holiday': is_holiday,
            'trading_sessions_enabled': not is_weekend or self.config['ENABLE_WEEKEND_SESSIONS']
        }
    '''
    '''
    def force_session_transition(self, new_session: str) -> SessionTransition:
        """Force a session transition (for testing/debugging)."""
        old_session = self.current_session
        
        try:
            self.current_session = MarketSession(new_session)
        except ValueError:
            self.current_session = MarketSession.UNKNOWN
        
        transition = SessionTransition(
            from_session=old_session.value,
            to_session=self.current_session.value,
            transition_time=time.time(),
            eastern_time=get_eastern_time(),
            affected_components=[]
        )
        
        logger.warning(f"⚠️ FORCED session transition: {old_session.value} → {self.current_session.value}")
        
        # Execute callbacks
        self._execute_session_callbacks(transition)
        
        return transition
    '''
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get performance report for session management."""
        transitions = len(self.session_history)
        successful = sum(1 for t in self.session_history if t.success)
        
        success_rate = (successful / transitions * 100) if transitions > 0 else 100.0
        
        return {
            'session_stats': {
                'current_session': self.current_session.value,
                'total_transitions': transitions,
                'successful_transitions': successful,
                'failed_transitions': transitions - successful,
                'registered_callbacks': len(self.session_change_callbacks)
            },
            'success_rate_percent': round(success_rate, 2),
            'session_history_count': len(self.session_history),
            'configuration': self.config.copy(),
            'timestamp': time.time()
        }