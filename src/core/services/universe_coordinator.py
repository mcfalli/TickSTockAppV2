"""
Universe Management Coordination - Phase 3 Refactoring
Thin coordination layer delegating to 4 specialized managers.
"""

import logging
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from config.logging_config import get_domain_logger, LogDomain

from src.core.services.universe import (
    UserUniverseManager,
    CoreUniverseManager, 
    SubscriptionManager,
    UniverseAnalytics
)

logger = get_domain_logger(LogDomain.UNIVERSE_TRACKING, 'universe_coordinator')


class DataFlowStats:
    """Track data flow through universe operations."""
    def __init__(self):
        self.universe_updates = 0
        self.membership_checks = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.tickers_processed = 0
        self.tickers_filtered = 0
        self.last_log_time = time.time()
        self.log_interval = 30  # seconds
    
    def should_log(self):
        return time.time() - self.last_log_time >= self.log_interval
    
    def log_stats(self):
        cache_hit_rate = (self.cache_hits / (self.cache_hits + self.cache_misses) * 100) if (self.cache_hits + self.cache_misses) > 0 else 0
        filter_rate = (self.tickers_filtered / self.tickers_processed * 100) if self.tickers_processed > 0 else 0
        logger.debug(f"📊 DIAG-UNIVERSE: STATS: Updates:{self.universe_updates} → Checks:{self.membership_checks} → Cache:{cache_hit_rate:.1f}% → Filtered:{filter_rate:.1f}%")
        self.last_log_time = time.time()


@dataclass
class UniverseOperationResult:
    """Result object for universe operations."""
    success: bool = True
    user_id: Optional[int] = None
    operation_type: str = "unknown"
    universe_updates: Optional[Dict] = None
    errors: Optional[List[str]] = None
    warnings: Optional[List[str]] = None
    timestamp: float = None
    processing_time_ms: float = 0
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.universe_updates is None:
            self.universe_updates = {}


class UniverseCoordinator:
    """
    Thin coordination layer for universe operations.
    Delegates all functionality to 4 specialized managers.
    """
    
    def __init__(self, config, market_service, cache_control=None, 
             tickstock_universe_manager=None, websocket_publisher=None,
             buysell_market_tracker=None, user_settings_service=None):  
        """Initialize universe coordinator as thin orchestration layer."""
        
        # Core dependencies
        self.market_service = market_service
        self.cache_control = cache_control or market_service.cache_control
        self.tickstock_universe_manager = tickstock_universe_manager or market_service.tickstock_universe_manager
        self.websocket_publisher = websocket_publisher or market_service.websocket_publisher
        self.buysell_market_tracker = buysell_market_tracker or market_service.buysell_market_tracker
        
        # Add this line to store user_settings_service
        self.user_settings_service = user_settings_service or getattr(market_service, 'user_settings_service', None)
  
        # Config
        self.config = config
        
        # Initialize logging
        self.logger = get_domain_logger(LogDomain.UNIVERSE_TRACKING, 'universe_coordinator')
        
        # Data flow tracking
        self.stats = DataFlowStats()
        
        # Initialize specialized managers
        self._initialize_specialized_managers()
        
   
    def _initialize_specialized_managers(self):
        """Initialize the 4 specialized universe managers."""
        try:
            # 1. User Universe Manager
            self.user_universe_manager = UserUniverseManager(
                config=self.config,
                cache_control=self.cache_control,
                user_settings_service=self.user_settings_service  # Use the stored service
            )
            
            # 2. Core Universe Manager
            self.core_universe_manager = CoreUniverseManager(
                config=self.config,
                tickstock_universe_manager=self.tickstock_universe_manager,
                cache_control=self.cache_control
            )
            
            # 3. Subscription Manager
            self.subscription_manager = SubscriptionManager(
                config=self.config,
                cache_control=self.cache_control
            )
            
            # 4. Universe Analytics
            self.universe_analytics = UniverseAnalytics(
                config=self.config,
                cache_control=self.cache_control
            )
            
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize universe managers: {e}", exc_info=True)
            raise
    
    # ===============================================================================
    # USER UNIVERSE OPERATIONS
    # ===============================================================================
    
    def update_user_universe_selections(self, user_id: int, tracker_type: str, universes: List[str]) -> UniverseOperationResult:
        """Update user universe selections."""
        start_time = time.time()
        result = UniverseOperationResult(
            user_id=user_id,
            operation_type=f"update_{tracker_type}_universe",
            universe_updates={tracker_type: universes}
        )
        
        try:
            self.stats.universe_updates += 1
            
            
            # Step 1: Save to user universe manager (this will update the cache)
            save_success = self.user_universe_manager.save_user_universe_selections(
                user_id, tracker_type, universes
            )
            
            if not save_success:
                result.errors.append(f"Failed to save universe selections")
                result.success = False
                return result

            # Step 2: Update tracker with new tickers
            all_tickers = self.user_universe_manager.get_all_user_universe_tickers(user_id)
            tracker_update_success = self._update_tracker_with_tickers(tracker_type, all_tickers, user_id)
            
            if not tracker_update_success:
                result.errors.append(f"Failed to update {tracker_type} tracker")
                result.success = False
                return result
            
            # Step 3: Update analytics
            self.universe_analytics.analyze_subscription_coverage(
                self.subscription_manager.get_subscription_tickers(),
                universes,
                user_id
            )
            
            # Step 4: Send status update
            self._send_universe_status_update('universe_updated', {
                'user_id': user_id,
                'tracker': tracker_type,
                'universes': universes,
                'ticker_count': len(all_tickers)
            })
            
            result.universe_updates['ticker_count'] = len(all_tickers)

            return result
            
        except Exception as e:
            error_msg = f"Universe update error for user {user_id}: {e}"
            logger.error(f"❌ {error_msg}", exc_info=True)
            result.success = False
            result.errors.append(error_msg)
            return result
        finally:
            result.processing_time_ms = (time.time() - start_time) * 1000
            if result.processing_time_ms > 100:
                logger.warning(f"⚠️DIAG-UNIVERSE: Slow universe update: {result.processing_time_ms:.1f}ms")
    
            
    '''
    def check_universe_membership(self, ticker: str, user_id: int = None) -> Dict[str, Any]:
        """Check ticker universe membership."""
        try:
            self.stats.membership_checks += 1
            self.stats.tickers_processed += 1
            
            # For user-specific check
            if user_id:
                user_universes = self.user_universe_manager.get_or_load_user_universes(user_id)
                all_user_universes = set()
                all_user_universes.update(user_universes.get('market', []))
                all_user_universes = list(all_user_universes)
                
                # Track cache performance
                if hasattr(self.user_universe_manager, '_cache_hit'):
                    if self.user_universe_manager._cache_hit:
                        self.stats.cache_hits += 1
                    else:
                        self.stats.cache_misses += 1
            else:
                # Fallback to default
                all_user_universes = ['DEFAULT_UNIVERSE']
            
            # Check membership
            membership_info = self.cache_control.log_universe_membership(ticker, all_user_universes)
            should_process = membership_info['is_in_any_user_universe']
            

            # Track filtering
            if not should_process:
                self.stats.tickers_filtered += 1
                
                # Log first few filtered tickers
                if self.stats.tickers_filtered <= 5:
                    logger.debug(f"🔍DIAG-UNIVERSE: FILTERED OUT #{self.stats.tickers_filtered}: {ticker} (not in user universes)")
            
            # Update analytics
            self.universe_analytics.update_processing_stats(ticker, should_process)
            
            # Log periodic stats
            if self.stats.should_log():
                self.stats.log_stats()
                self.check_data_flow_health()
            
            return {
                'ticker': ticker,
                'user_id': user_id,
                'should_process': should_process,
                'universe_matches': membership_info['universe_matches'],
                'membership_results': membership_info['membership_results'],
                'universe_selections_used': all_user_universes
            }
            
        except Exception as e:
            logger.error(f"❌ Error checking membership for {ticker}: {e}")
            return {
                'ticker': ticker, 
                'user_id': user_id,
                'should_process': True,
                'error': str(e)
            }
    '''
    def get_user_universe_info(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive universe information for a specific user."""
        try:
            # Get user selections
            user_selections = self.user_universe_manager.get_or_load_user_universes(user_id)
            
            # Get analytics report
            analytics_report = self.universe_analytics.generate_universe_report(user_id)
            
            # Get cache status
            cache_status = self.user_universe_manager.get_universe_cache_status()
            
            return {
                'user_id': user_id,
                'universe_selections': user_selections,
                'analytics': analytics_report,
                'cache_status': cache_status,
                'core_universe_info': self.core_universe_manager.get_core_universe_info(),
                'timestamp': time.time()
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting universe info for user {user_id}: {e}")
            return {
                'user_id': user_id,
                'error': str(e),
                'timestamp': time.time()
            }
    
    def invalidate_user_universe_cache(self, user_id: int) -> bool:
        """Invalidate universe cache for a specific user."""
        try:
            success = self.user_universe_manager.invalidate_user_universe_cache(user_id)
            
            if success:
                self._send_universe_status_update('universe_cache_invalidated', {
                    'user_id': user_id,
                    'timestamp': time.time()
                })

            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error invalidating cache for user {user_id}: {e}")
            return False
    
    # ===============================================================================
    # CORE UNIVERSE OPERATIONS
    # ===============================================================================
    
    def get_core_universe_info(self) -> Dict[str, Any]:
        """Get information about the TickStock Core Universe."""
        return self.core_universe_manager.get_core_universe_info()
    
    def refresh_core_universe(self) -> bool:
        """Refresh the TickStock Core Universe and update market tracker."""
        try:
            if self.core_universe_manager.refresh_core_universe():
                # Update market tracker
                core_tickers = self.core_universe_manager.get_core_universe_tickers()
                self.buysell_market_tracker.tracked_stocks = core_tickers
                self.buysell_market_tracker.reset_tracking()
                
                # Send status update
                self._send_universe_status_update('core_universe_refreshed', {
                    'universe_size': len(core_tickers),
                    'timestamp': time.time()
                })
                
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"❌ Error refreshing core universe: {e}", exc_info=True)
            return False
    
    def check_core_universe_membership(self, ticker: str) -> bool:
        """Check if ticker should be processed for TickStock Core Universe."""
        return self.core_universe_manager.check_core_universe_membership(ticker)
    
    # ===============================================================================
    # SUBSCRIPTION OPERATIONS
    # ===============================================================================
    
    def log_subscription_universe_analysis(self, subscribed_tickers: List[str], user_id: int = None):
        """Log analysis of subscription vs user universe selection."""
        try:
            # Get user universe selections
            if user_id:
                user_selections = self.user_universe_manager.get_or_load_user_universes(user_id)
                all_universes = set()
                all_universes.update(user_selections.get('market', []))
                all_universes = list(all_universes)
            else:
                all_universes = ['DEFAULT_UNIVERSE']
            
            # Perform analysis
            coverage_stats = self.universe_analytics.analyze_subscription_coverage(
                subscribed_tickers, all_universes, user_id
            )
            
            # Log coverage
            logger.debug(f"📊DIAG-UNIVERSE: SUBSCRIPTION COVERAGE: {coverage_stats['overlap_count']} overlap, {coverage_stats['coverage_percentage']}% covered, {coverage_stats['subscription_efficiency']}% efficient")
            
            return coverage_stats
            
        except Exception as e:
            logger.error(f"❌ Error analyzing subscription coverage: {e}")
            return {}
    
    # ===============================================================================
    # INTERNAL HELPER METHODS
    # ===============================================================================
    
    def _update_tracker_with_tickers(self, tracker_type: str, all_tickers: set, user_id: int = None) -> bool:
        """Update the appropriate tracker with ticker set."""
        try:
            if tracker_type == 'market':
                self.buysell_market_tracker.tracked_stocks = all_tickers
                self.buysell_market_tracker.reset_tracking()
                logger.debug(f"📤DIAG-UNIVERSE: Updated market tracker: {len(all_tickers)} stocks")
            else:
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating {tracker_type} tracker: {e}")
            return False
    
    def _send_universe_status_update(self, status: str, extra_info: Dict = None):
        """Send universe-related status updates."""
        try:
            if self.market_service and hasattr(self.market_service, '_send_status_update'):
                self.market_service._send_status_update(status, extra_info or {})
        except Exception as e:
            logger.error(f"❌ Error sending status update: {e}")
    
    def check_data_flow_health(self):
        """Diagnose where data flow is breaking."""
        if self.stats.membership_checks == 0:
            logger.error("🚨DIAG-UNIVERSE: NO MEMBERSHIP CHECKS - Universe filtering not running")
        elif self.stats.tickers_processed == 0:
            logger.error("🚨DIAG-UNIVERSE: NO TICKERS PROCESSED - Check data source")
        elif self.stats.tickers_filtered == self.stats.tickers_processed:
            logger.warning("⚠️DIAG-UNIVERSE: ALL TICKERS FILTERED - Check universe configuration")
        
        filter_rate = (self.stats.tickers_filtered / self.stats.tickers_processed * 100) if self.stats.tickers_processed > 0 else 0
        if filter_rate > 90:
            logger.warning(f"⚠️ High filter rate: {filter_rate:.1f}% - Most tickers being filtered out")
    
    # ===============================================================================
    # PERFORMANCE AND REPORTING
    # ===============================================================================
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report from all managers."""
        try:
            return {
                'coordinator_stats': {
                    'universe_updates': self.stats.universe_updates,
                    'membership_checks': self.stats.membership_checks,
                    'cache_hits': self.stats.cache_hits,
                    'cache_misses': self.stats.cache_misses,
                    'tickers_processed': self.stats.tickers_processed,
                    'tickers_filtered': self.stats.tickers_filtered
                },
                'manager_reports': {
                    'user_universe': {
                        'cache_status': self.user_universe_manager.get_universe_cache_status(),
                        'cache_size': len(self.user_universe_manager.user_universe_cache)
                    },
                    'core_universe': {
                        'info': self.core_universe_manager.get_core_universe_info(),
                        'health': self.core_universe_manager.perform_health_check()
                    }
                },
                'timestamp': time.time()
            }
            
        except Exception as e:
            logger.error(f"❌ Error generating performance report: {e}")
            return {'error': str(e)}
    
    '''
    def reset_performance_stats(self):
        """Reset performance statistics across all managers."""
        self.stats = DataFlowStats()
        self.user_universe_manager.reset_cache_stats()
        self.universe_analytics.reset_processing_stats()
    '''


            
