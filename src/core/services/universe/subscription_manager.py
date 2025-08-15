"""
Subscription Management - Sprint 6B
Handles WebSocket subscription coordination and optimization.
Extracted from src.core.services.universe_coordinator.py
"""

import logging
import time
from typing import Dict, List, Set, Any, Optional
from collections import defaultdict

from config.logging_config import get_domain_logger, LogDomain

logger = get_domain_logger(LogDomain.CORE, 'subscription_manager')

class DataFlowStats:
    """Track subscription data flow metrics."""
    def __init__(self):
        self.subscriptions_requested = 0
        self.subscriptions_active = 0
        self.subscriptions_failed = 0
        self.last_log_time = time.time()
        self.log_interval = 60  # seconds
    
    def should_log(self):
        return time.time() - self.last_log_time >= self.log_interval
    
    def log_stats(self, logger):
        logger.info(
            f"📊 SUBSCRIPTION STATS: Requested:{self.subscriptions_requested} → "
            f"Active:{self.subscriptions_active} → Failed:{self.subscriptions_failed}"
        )
        self.last_log_time = time.time()

class SubscriptionManager:
    """
    Manages WebSocket subscription operations and optimization.
    
    Responsibilities:
    - Coordinate WebSocket subscriptions
    - Optimize subscription lists
    - Track subscription health
    - Handle subscription updates
    
    Note: Subscriptions are based on TickStock Core Universe and do not
    change based on user universe selections.
    """
    
    def __init__(self, config, cache_control):
        """Initialize subscription manager."""
        self.config = config
        self.cache_control = cache_control
        
        # Data flow tracking
        self.stats = DataFlowStats()
        
        # Subscription state
        self.active_subscriptions = set()
        self.subscription_metadata = {}
        
        # Configuration
        self.max_subscriptions = config.get('MAX_WEBSOCKET_SUBSCRIPTIONS', 5000)
        self.subscription_batch_size = config.get('SUBSCRIPTION_BATCH_SIZE', 500)
        self.subscription_update_delay = config.get('SUBSCRIPTION_UPDATE_DELAY', 2.0)
        
        logger.info(f"✅ SubscriptionManager initialized (max: {self.max_subscriptions})")
    
    def get_subscription_tickers(self) -> List[str]:
        """
        Get the list of tickers to subscribe to via WebSocket.
        Based on TickStock Core Universe.
        
        Returns:
            List[str]: Tickers to subscribe to
        """
        try:
            # Get default universe (typically TickStock Core Universe)
            subscription_tickers = self.cache_control.get_default_universe()
            self.stats.subscriptions_requested = len(subscription_tickers)
            
            # Apply subscription limits
            if len(subscription_tickers) > self.max_subscriptions:
                logger.debug(f"⚠️ DIAG-SUBSCRIPTION-SERVICE: Truncating subscriptions: {len(subscription_tickers)} → {self.max_subscriptions}")
                subscription_tickers = subscription_tickers[:self.max_subscriptions]
            
            # Log first few on initial request
            if self.stats.subscriptions_active == 0 and subscription_tickers:
                logger.debug(f"📥 DIAG-SUBSCRIPTION-SERVICE: SUBSCRIPTION REQUEST: {len(subscription_tickers)} tickers First 5 tickers: {subscription_tickers[:5]}")
            
            return subscription_tickers
            
        except Exception as e:
            logger.error(f"❌ Failed to get subscription tickers: {e}")
            self.stats.subscriptions_failed += 1
            return []
    
    def update_subscriptions(self, tickers: List[str]) -> Dict[str, Any]:
        """
        Update WebSocket subscriptions.
        
        Args:
            tickers: List of tickers to subscribe to
            
        Returns:
            dict: Update results
        """
        try:
            start_time = time.time()
            old_count = len(self.active_subscriptions)
            
            # Convert to set for efficient operations
            new_subscriptions = set(tickers[:self.max_subscriptions])
            
            # Calculate changes
            added = new_subscriptions - self.active_subscriptions
            removed = self.active_subscriptions - new_subscriptions
            
            # Update active subscriptions
            self.active_subscriptions = new_subscriptions
            self.stats.subscriptions_active = len(new_subscriptions)
            
            # Create result
            result = {
                'success': True,
                'previous_count': old_count,
                'new_count': len(new_subscriptions),
                'added_count': len(added),
                'removed_count': len(removed),
                'processing_time_ms': (time.time() - start_time) * 1000
            }
            
            # Log significant changes
            if added or removed:
                logger.info(
                    f"📤 SUBSCRIPTION UPDATE: {old_count} → {len(new_subscriptions)} "
                    f"(+{len(added)}, -{len(removed)})"
                )
            
            # Periodic stats logging
            if self.stats.should_log():
                self.stats.log_stats(logger)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Subscription update failed: {e}")
            self.stats.subscriptions_failed += 1
            return {
                'success': False,
                'error': str(e)
            }
    
    def validate_subscription_coverage(self, required_tickers: Set[str]) -> Dict[str, Any]:
        """
        Validate that required tickers are covered by subscriptions.
        
        Args:
            required_tickers: Set of tickers that should be subscribed
            
        Returns:
            dict: Coverage validation results
        """
        try:
            # Calculate coverage
            covered_tickers = required_tickers & self.active_subscriptions
            missing_tickers = required_tickers - self.active_subscriptions
            
            coverage_percentage = 0
            if required_tickers:
                coverage_percentage = (len(covered_tickers) / len(required_tickers)) * 100
            
            # Log if coverage is poor
            if coverage_percentage < 90 and required_tickers:
                logger.warning(
                    f"⚠️ Poor subscription coverage: {coverage_percentage:.1f}% "
                    f"({len(missing_tickers)} tickers missing)"
                )
            
            return {
                'is_complete': len(missing_tickers) == 0,
                'coverage_percentage': round(coverage_percentage, 2),
                'covered_count': len(covered_tickers),
                'missing_count': len(missing_tickers),
                'missing_tickers': sorted(list(missing_tickers))[:100],  # Limit for logging
                'total_subscriptions': len(self.active_subscriptions),
                'total_required': len(required_tickers)
            }
            
        except Exception as e:
            logger.error(f"❌ Coverage validation failed: {e}")
            return {'error': str(e)}
    
    def get_subscription_health(self) -> Dict[str, Any]:
        """
        Get health metrics for subscription system.
        
        Returns:
            dict: Subscription health metrics
        """
        try:
            # Determine health status
            is_healthy = True
            issues = []
            
            if len(self.active_subscriptions) == 0:
                is_healthy = False
                issues.append("No active subscriptions")
            
            if self.stats.subscriptions_failed > 5:
                is_healthy = False
                issues.append(f"High failure count: {self.stats.subscriptions_failed}")
            
            # Log health issues
            if not is_healthy:
                logger.error(f"🚨 SUBSCRIPTION HEALTH ISSUES: {', '.join(issues)}")
            
            return {
                'is_healthy': is_healthy,
                'issues': issues,
                'active_count': len(self.active_subscriptions),
                'max_allowed': self.max_subscriptions,
                'utilization_percent': round((len(self.active_subscriptions) / self.max_subscriptions) * 100, 2)
            }
            
        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")
            return {
                'is_healthy': False,
                'error': str(e)
            }
    
    def check_data_flow_health(self):
        """Diagnose where data flow is breaking."""
        if self.stats.subscriptions_requested == 0:
            logger.error("🚨 NO SUBSCRIPTIONS REQUESTED - Check universe configuration")
        elif self.stats.subscriptions_active == 0:
            logger.error("🚨 Subscriptions requested but NOT ACTIVE - Check WebSocket connection")
        elif self.stats.subscriptions_failed > 0:
            logger.warning(f"⚠️ {self.stats.subscriptions_failed} subscription failures detected")
        else:
            logger.info(f"✅ Subscription flow healthy: {self.stats.subscriptions_active} active")