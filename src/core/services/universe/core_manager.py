"""
Core Universe Management - Sprint 6B
Handles TickStock Core Universe operations and health monitoring.
Extracted from src.core.services.universe_coordinator.py
"""

import logging
import time
from typing import Dict, List, Any, Set, Optional

from config.logging_config import get_domain_logger, LogDomain

logger = get_domain_logger(LogDomain.CORE, 'core_universe_manager')

class DataFlowStats:
    """Track core universe data flow."""
    def __init__(self):
        self.refresh_count = 0
        self.refresh_failures = 0
        self.membership_checks = 0
        self.last_log_time = time.time()
        self.log_interval = 300  # 5 minutes for core universe
    
    def should_log(self):
        return time.time() - self.last_log_time >= self.log_interval
    
    def log_stats(self, logger, universe_size):
        logger.info(
            f"📊 CORE-UNV: CORE UNIVERSE: Size:{universe_size} → "
            f"Refreshes:{self.refresh_count} → Failures:{self.refresh_failures} → "
            f"Checks:{self.membership_checks}"
        )
        self.last_log_time = time.time()

class CoreUniverseManager:
    """
    Manages TickStock Core Universe operations.
    
    Responsibilities:
    - Core universe refresh and validation
    - Core universe health monitoring
    - Integration with TickStockUniverseManager
    - Core universe statistics
    """
    
    def __init__(self, config, tickstock_universe_manager, cache_control):
        """Initialize core universe manager."""
        self.config = config
        self.tickstock_universe_manager = tickstock_universe_manager
        self.cache_control = cache_control
        
        # Data flow tracking
        self.stats = DataFlowStats()
        
        # Core universe cache
        self.core_universe_cache = {
            'tickers': set(),
            'last_refresh': 0,
            'health_status': {}
        }
        
        # Configuration
        self.refresh_interval = config.get('CORE_UNIVERSE_REFRESH_INTERVAL', 86400)  # 24 hours
        self.health_check_interval = config.get('CORE_UNIVERSE_HEALTH_CHECK_INTERVAL', 3600)  # 1 hour
        
        # Initialize core universe
        self._initialize_core_universe()
    
    def _initialize_core_universe(self):
        """Initialize core universe on startup."""
        try:
            if self.tickstock_universe_manager.get_universe_size() == 0:
                logger.info("🔨CORE-UNV: Building initial TickStock Core Universe...")
                if not self.tickstock_universe_manager.build_core_universe():
                    raise RuntimeError("CORE-UNV: Failed to build initial core universe")
            
            # Cache the core universe
            self.core_universe_cache['tickers'] = set(self.tickstock_universe_manager.get_core_universe())
            self.core_universe_cache['last_refresh'] = time.time()
            
            logger.info(f"✅CORE-UNV: Core universe initialized: {len(self.core_universe_cache['tickers'])} stocks")
            
        except Exception as e:
            logger.error(f"❌ CRITICAL: Failed to initialize core universe: {e}")
            raise
    
    def get_core_universe_info(self) -> Dict[str, Any]:
        """
        Get comprehensive information about the TickStock Core Universe.
        
        Returns:
            dict: Core universe information and statistics
        """
        try:
            universe_size = len(self.core_universe_cache['tickers'])
            time_since_refresh = time.time() - self.core_universe_cache['last_refresh']
            
            # Get health status
            health_status = self.perform_health_check()
            
            # Periodic stats logging
            if self.stats.should_log():
                self.stats.log_stats(logger, universe_size)
            
            return {
                'universe_size': universe_size,
                'last_refresh': self.core_universe_cache['last_refresh'],
                'time_since_refresh_hours': time_since_refresh / 3600,
                'health_status': health_status,
                'refresh_stats': {
                    'total_refreshes': self.stats.refresh_count,
                    'failed_refreshes': self.stats.refresh_failures
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get core universe info: {e}")
            return {'error': str(e)}
    
    def refresh_core_universe(self) -> bool:
        """
        Refresh the TickStock Core Universe.
        
        Returns:
            bool: True if refresh successful
        """
        try:
            old_size = len(self.core_universe_cache['tickers'])
            
            # Refresh through TickStockUniverseManager
            if self.tickstock_universe_manager.refresh_core_universe():
                # Update local cache
                new_tickers = set(self.tickstock_universe_manager.get_core_universe())
                self.core_universe_cache['tickers'] = new_tickers
                self.core_universe_cache['last_refresh'] = time.time()
                self.stats.refresh_count += 1
                
                new_size = len(new_tickers)
                
                # Refresh cache control if available
                if self.cache_control:
                    self.cache_control.refresh_core_universe_cache()
                
                # Log changes
                added_count = len(new_tickers - self.core_universe_cache['tickers'])
                removed_count = len(self.core_universe_cache['tickers'] - new_tickers)
                
                return True
            else:
                logger.error("❌ Core universe refresh failed")
                self.stats.refresh_failures += 1
                return False
                
        except Exception as e:
            logger.error(f"❌ Critical error during core universe refresh: {e}")
            self.stats.refresh_failures += 1
            return False
    
    def check_core_universe_membership(self, ticker: str) -> bool:
        """
        Fast check if ticker is in TickStock Core Universe.
        
        Args:
            ticker: Stock symbol to check
            
        Returns:
            bool: True if ticker is in core universe
        """
        self.stats.membership_checks += 1
        
        # Log first few checks
        if self.stats.membership_checks <= 5:
            result = ticker in self.core_universe_cache['tickers']
            return result
        
        # Use cached set for fast lookup
        return ticker in self.core_universe_cache['tickers']
    
    def perform_health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check on core universe.
        
        Returns:
            dict: Health check results
        """
        try:
            # Get health check from manager
            health_results = self.tickstock_universe_manager.validate_universe_health()
            
            # Add local health metrics
            time_since_refresh = time.time() - self.core_universe_cache['last_refresh']
            refresh_overdue = time_since_refresh >= self.refresh_interval
            
            health_results['local_metrics'] = {
                'cache_age_hours': time_since_refresh / 3600,
                'cached_ticker_count': len(self.core_universe_cache['tickers']),
                'refresh_overdue': refresh_overdue
            }
            
            # Update cached health status
            self.core_universe_cache['health_status'] = health_results
            
            # Log health issues
            if not health_results.get('is_healthy', True):
                issues = health_results.get('issues', [])
                logger.error(f"🚨CORE-UNV: CORE UNIVERSE HEALTH ISSUES: {', '.join(issues)}")
            elif refresh_overdue:
                logger.warning(f"⚠️CORE-UNV: Core universe refresh overdue by {(time_since_refresh - self.refresh_interval) / 3600:.1f} hours")
            
            return health_results
            
        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")
            return {
                'is_healthy': False,
                'error': str(e),
                'timestamp': time.time()
            }
    
    def check_data_flow_health(self):
        """Diagnose where data flow is breaking."""
        if len(self.core_universe_cache['tickers']) == 0:
            logger.error("🚨CORE-UNV: NO CORE UNIVERSE - System cannot function")
        elif self.stats.refresh_failures > 2:
            logger.error(f"🚨CORE-UNV: Multiple refresh failures ({self.stats.refresh_failures}) - Check data source")
        elif self.stats.membership_checks == 0:
            logger.warning("⚠️CORE-UNV: No membership checks performed - Check if data is being processed")
        else:
            universe_size = len(self.core_universe_cache['tickers'])
            logger.info(f"✅CORE-UNV: Core universe healthy: {universe_size} stocks, {self.stats.membership_checks} checks")