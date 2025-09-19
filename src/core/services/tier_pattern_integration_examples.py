"""
Sprint 25+ Integration Pattern Examples
Comprehensive integration patterns for using the 4-layer WebSocket architecture.

This file provides complete examples for Sprint 25+ features to integrate
with the TierPatternWebSocketIntegration and 4-layer architecture.
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

# Core imports
from src.core.services.websocket_subscription_manager import UniversalWebSocketManager
from src.core.services.tier_pattern_websocket_integration import (
    TierPatternWebSocketIntegration,
    TierSubscriptionPreferences,
    create_tier_pattern_integration,
    create_daily_pattern_subscription,
    create_high_confidence_subscription,
    create_intraday_scalping_subscription,
    create_swing_trading_subscription,
    create_risk_monitoring_subscription
)
from src.core.domain.events.tier_events import (
    TierPatternEvent, PatternTier, EventPriority,
    MarketStateEvent, PatternAlertEvent, MarketRegime
)

logger = logging.getLogger(__name__)

@dataclass
class IntegrationConfig:
    """Configuration for tier pattern integration."""
    performance_mode: bool = True
    real_time_alerts: bool = True  
    market_insights: bool = True
    max_concurrent_users: int = 500
    enable_logging: bool = True

class TierPatternIntegrationPatterns:
    """
    Complete integration patterns for Sprint 25+ features.
    
    Provides real-world examples of how to integrate with the
    4-layer WebSocket architecture for maximum performance.
    """
    
    def __init__(self, universal_ws_manager: UniversalWebSocketManager, 
                 config: IntegrationConfig = None):
        """Initialize integration patterns with WebSocket manager."""
        self.universal_ws_manager = universal_ws_manager
        self.config = config or IntegrationConfig()
        
        # Create tier pattern integration with optimizations
        self.tier_integration = create_tier_pattern_integration(
            websocket_manager=universal_ws_manager,
            performance_mode=self.config.performance_mode,
            real_time_alerts=self.config.real_time_alerts,
            market_insights=self.config.market_insights
        )
        
        # Integration statistics
        self.integration_stats = {
            'patterns_processed': 0,
            'users_subscribed': 0,
            'alerts_sent': 0,
            'performance_violations': 0,
            'start_time': time.time()
        }
        
        logger.info("INTEGRATION-PATTERNS: Sprint 25+ integration patterns initialized")
    
    # Pattern 1: Basic User Subscription Management
    
    def subscribe_user_to_daily_patterns(self, user_id: str, symbols: List[str], 
                                       confidence_threshold: float = 0.7) -> bool:
        """
        Pattern 1: Subscribe user to daily patterns only.
        
        Use Case: Conservative traders who want daily-level pattern insights
        Performance: <5ms filtering + <125ms total delivery
        
        Args:
            user_id: User identifier
            symbols: Stock symbols to monitor
            confidence_threshold: Minimum pattern confidence
            
        Returns:
            True if subscription successful
            
        Example:
            # Subscribe conservative trader to daily patterns
            success = patterns.subscribe_user_to_daily_patterns(
                user_id='trader_001',
                symbols=['AAPL', 'MSFT', 'GOOGL'],
                confidence_threshold=0.75
            )
        """
        try:
            # Create daily pattern subscription preferences
            preferences = create_daily_pattern_subscription(
                symbols=symbols,
                confidence_min=confidence_threshold
            )
            
            # Subscribe via tier pattern integration
            success = self.tier_integration.subscribe_user_to_tier_patterns(user_id, preferences)
            
            if success:
                self.integration_stats['users_subscribed'] += 1
                logger.info(f"INTEGRATION-PATTERNS: User {user_id} subscribed to daily patterns "
                           f"for {len(symbols)} symbols (confidence >= {confidence_threshold})")
            
            return success
            
        except Exception as e:
            logger.error(f"INTEGRATION-PATTERNS: Error subscribing user to daily patterns: {e}")
            return False
    
    # Pattern 2: High-Performance Scalping Integration
    
    def setup_scalping_trader(self, user_id: str, symbols: List[str]) -> bool:
        """
        Pattern 2: High-frequency scalping trader setup.
        
        Use Case: Active day traders requiring sub-second pattern notifications
        Performance: Priority routing + batching bypass for critical patterns
        
        Args:
            user_id: Scalping trader identifier
            symbols: High-volume symbols to monitor
            
        Returns:
            True if setup successful
            
        Example:
            # Setup high-frequency scalper
            success = patterns.setup_scalping_trader(
                user_id='scalper_pro',
                symbols=['SPY', 'QQQ', 'TSLA', 'NVDA']
            )
        """
        try:
            # Create high-frequency scalping subscription
            preferences = create_intraday_scalping_subscription(symbols=symbols)
            
            # Subscribe with performance monitoring
            start_time = time.time()
            success = self.tier_integration.subscribe_user_to_tier_patterns(user_id, preferences)
            subscription_latency = (time.time() - start_time) * 1000
            
            if success:
                self.integration_stats['users_subscribed'] += 1
                
                # Log performance metrics
                if subscription_latency > 10:  # Target <10ms for scalping setup
                    self.integration_stats['performance_violations'] += 1
                    logger.warning(f"INTEGRATION-PATTERNS: Scalping setup latency {subscription_latency:.1f}ms exceeds 10ms target")
                
                logger.info(f"INTEGRATION-PATTERNS: Scalping trader {user_id} configured "
                           f"for {len(symbols)} symbols in {subscription_latency:.1f}ms")
            
            return success
            
        except Exception as e:
            logger.error(f"INTEGRATION-PATTERNS: Error setting up scalping trader: {e}")
            return False
    
    # Pattern 3: Multi-User Portfolio Monitoring
    
    def setup_portfolio_monitoring(self, portfolio_users: Dict[str, List[str]], 
                                 monitoring_type: str = 'swing_trading') -> Dict[str, bool]:
        """
        Pattern 3: Bulk portfolio monitoring setup.
        
        Use Case: Portfolio managers monitoring multiple user watchlists
        Performance: Batch subscription processing with <1s total setup time
        
        Args:
            portfolio_users: Dict mapping user_id to their symbol list
            monitoring_type: Type of monitoring ('swing_trading', 'risk_monitoring', etc.)
            
        Returns:
            Dict mapping user_id to subscription success status
            
        Example:
            # Setup portfolio monitoring for multiple users
            portfolio = {
                'fund_manager_1': ['AAPL', 'MSFT', 'GOOGL'],
                'fund_manager_2': ['TSLA', 'NVDA', 'AMD'],
                'risk_analyst': ['SPY', 'VIX', 'TLT']
            }
            results = patterns.setup_portfolio_monitoring(portfolio, 'risk_monitoring')
        """
        try:
            results = {}
            start_time = time.time()
            
            # Determine subscription type
            if monitoring_type == 'swing_trading':
                subscription_creator = create_swing_trading_subscription
            elif monitoring_type == 'risk_monitoring':
                subscription_creator = create_risk_monitoring_subscription
            else:
                subscription_creator = create_high_confidence_subscription
            
            # Process subscriptions in batch
            for user_id, symbols in portfolio_users.items():
                try:
                    preferences = subscription_creator(symbols=symbols)
                    success = self.tier_integration.subscribe_user_to_tier_patterns(user_id, preferences)
                    results[user_id] = success
                    
                    if success:
                        self.integration_stats['users_subscribed'] += 1
                        
                except Exception as e:
                    logger.error(f"INTEGRATION-PATTERNS: Error subscribing user {user_id}: {e}")
                    results[user_id] = False
            
            # Performance validation
            total_time = (time.time() - start_time) * 1000
            users_count = len(portfolio_users)
            avg_time_per_user = total_time / max(users_count, 1)
            
            if total_time > 1000:  # Target <1s for batch setup
                self.integration_stats['performance_violations'] += 1
                logger.warning(f"INTEGRATION-PATTERNS: Portfolio setup took {total_time:.1f}ms (target: <1000ms)")
            
            successful_subs = sum(results.values())
            logger.info(f"INTEGRATION-PATTERNS: Portfolio monitoring setup completed: "
                       f"{successful_subs}/{users_count} users in {total_time:.1f}ms "
                       f"({avg_time_per_user:.1f}ms per user)")
            
            return results
            
        except Exception as e:
            logger.error(f"INTEGRATION-PATTERNS: Error in portfolio monitoring setup: {e}")
            return {}
    
    # Pattern 4: Real-Time Pattern Broadcasting
    
    def broadcast_pattern_with_performance_tracking(self, pattern_event: TierPatternEvent) -> Dict[str, Any]:
        """
        Pattern 4: High-performance pattern broadcasting with metrics.
        
        Use Case: Real-time pattern detection with performance validation
        Performance: <125ms end-to-end delivery with component breakdown
        
        Args:
            pattern_event: TierPatternEvent to broadcast
            
        Returns:
            Performance metrics and delivery results
            
        Example:
            # Broadcast high-confidence breakout pattern
            pattern = TierPatternEvent(
                event_id='breakout_001',
                pattern_type='BreakoutBO',
                symbol='AAPL',
                tier=PatternTier.DAILY,
                confidence=0.92,
                priority=EventPriority.HIGH,
                timestamp=time.time()
            )
            metrics = patterns.broadcast_pattern_with_performance_tracking(pattern)
        """
        try:
            start_time = time.time()
            
            # Broadcast via tier integration with performance tracking
            delivery_count = self.tier_integration.broadcast_tier_pattern_event(pattern_event)
            
            # Calculate performance metrics
            total_latency = (time.time() - start_time) * 1000
            
            # Get component performance breakdowns
            index_stats = self.universal_ws_manager.index_manager.get_performance_stats() \
                if hasattr(self.universal_ws_manager.index_manager, 'get_performance_stats') else {}
            router_stats = self.universal_ws_manager.event_router.get_performance_stats() \
                if hasattr(self.universal_ws_manager.event_router, 'get_performance_stats') else {}
            broadcaster_stats = self.universal_ws_manager.broadcaster.get_performance_stats() \
                if hasattr(self.universal_ws_manager.broadcaster, 'get_performance_stats') else {}
            
            # Update integration statistics
            self.integration_stats['patterns_processed'] += 1
            
            # Performance validation
            performance_compliant = total_latency <= 125  # Target <125ms
            if not performance_compliant:
                self.integration_stats['performance_violations'] += 1
            
            # Comprehensive performance metrics
            metrics = {
                'pattern_info': {
                    'event_id': pattern_event.event_id,
                    'pattern_type': pattern_event.pattern_type,
                    'symbol': pattern_event.symbol,
                    'tier': pattern_event.tier.value,
                    'confidence': pattern_event.confidence,
                    'priority': pattern_event.priority.value
                },
                'delivery_results': {
                    'users_reached': delivery_count,
                    'total_latency_ms': round(total_latency, 2),
                    'performance_compliant': performance_compliant,
                    'target_latency_ms': 125
                },
                'component_performance': {
                    'index_manager': index_stats,
                    'event_router': router_stats, 
                    'broadcaster': broadcaster_stats
                },
                'timestamp': time.time()
            }
            
            logger.info(f"INTEGRATION-PATTERNS: Pattern {pattern_event.pattern_type} on {pattern_event.symbol} "
                       f"delivered to {delivery_count} users in {total_latency:.1f}ms "
                       f"({'[OK] COMPLIANT' if performance_compliant else '⚠ SLOW'})")
            
            return metrics
            
        except Exception as e:
            logger.error(f"INTEGRATION-PATTERNS: Error broadcasting pattern: {e}")
            return {'error': str(e), 'timestamp': time.time()}
    
    # Pattern 5: Alert System Integration
    
    def create_and_send_pattern_alert(self, user_id: str, pattern_event: TierPatternEvent,
                                    alert_priority: EventPriority = None) -> bool:
        """
        Pattern 5: Pattern alert generation and delivery.
        
        Use Case: User-specific pattern alerts with priority escalation
        Performance: <50ms delivery for critical alerts
        
        Args:
            user_id: Target user for alert
            pattern_event: Pattern that triggered the alert
            alert_priority: Override alert priority (optional)
            
        Returns:
            True if alert sent successfully
            
        Example:
            # Send critical alert for high-confidence pattern
            alert_sent = patterns.create_and_send_pattern_alert(
                user_id='vip_trader',
                pattern_event=high_confidence_pattern,
                alert_priority=EventPriority.CRITICAL
            )
        """
        try:
            start_time = time.time()
            
            # Get user's subscription filters
            user_subscriptions = self.tier_integration.get_user_tier_subscriptions(user_id)
            user_filters = user_subscriptions.get('filters', {}) if user_subscriptions else {}
            
            # Generate pattern alert
            alert_event = self.tier_integration.generate_pattern_alert(
                user_id=user_id,
                pattern_event=pattern_event,
                user_filters=user_filters
            )
            
            if not alert_event:
                logger.warning(f"INTEGRATION-PATTERNS: Failed to generate alert for user {user_id}")
                return False
            
            # Override alert priority if specified
            if alert_priority:
                alert_event.alert_priority = alert_priority
            
            # Send alert via tier integration
            success = self.tier_integration.broadcast_pattern_alert(alert_event)
            
            # Performance tracking
            alert_latency = (time.time() - start_time) * 1000
            
            if success:
                self.integration_stats['alerts_sent'] += 1
                
                # Critical alert performance validation
                if alert_event.alert_priority == EventPriority.CRITICAL and alert_latency > 50:
                    self.integration_stats['performance_violations'] += 1
                    logger.warning(f"INTEGRATION-PATTERNS: Critical alert latency {alert_latency:.1f}ms exceeds 50ms target")
                
                logger.info(f"INTEGRATION-PATTERNS: Alert {alert_event.alert_id} sent to user {user_id} "
                           f"in {alert_latency:.1f}ms ({alert_event.alert_priority.value} priority)")
            
            return success
            
        except Exception as e:
            logger.error(f"INTEGRATION-PATTERNS: Error creating/sending pattern alert: {e}")
            return False
    
    # Pattern 6: Health Monitoring and Statistics
    
    def get_comprehensive_health_report(self) -> Dict[str, Any]:
        """
        Pattern 6: Complete system health monitoring.
        
        Use Case: System monitoring and performance validation for Sprint 25+ features
        Performance: Real-time health metrics with component breakdown
        
        Returns:
            Comprehensive health and performance report
            
        Example:
            # Get complete system health status
            health_report = patterns.get_comprehensive_health_report()
            if health_report['overall_status'] != 'healthy':
                alert_ops_team(health_report)
        """
        try:
            # Get component health statuses
            tier_integration_health = self.tier_integration.get_health_status()
            ws_manager_health = self.universal_ws_manager.get_health_status()
            
            # Calculate integration-specific metrics
            runtime_seconds = time.time() - self.integration_stats['start_time']
            patterns_per_minute = (self.integration_stats['patterns_processed'] / max(runtime_seconds / 60, 1))
            performance_compliance_ratio = 1.0 - (self.integration_stats['performance_violations'] / 
                                                max(self.integration_stats['patterns_processed'], 1))
            
            # Determine overall health status
            component_statuses = [tier_integration_health['status'], ws_manager_health['status']]
            if 'error' in component_statuses:
                overall_status = 'error'
            elif 'warning' in component_statuses:
                overall_status = 'warning'
            elif performance_compliance_ratio < 0.95:  # <95% compliance
                overall_status = 'warning'
            else:
                overall_status = 'healthy'
            
            # Comprehensive health report
            health_report = {
                'overall_status': overall_status,
                'timestamp': time.time(),
                'integration_statistics': {
                    'patterns_processed': self.integration_stats['patterns_processed'],
                    'users_subscribed': self.integration_stats['users_subscribed'],
                    'alerts_sent': self.integration_stats['alerts_sent'],
                    'performance_violations': self.integration_stats['performance_violations'],
                    'patterns_per_minute': round(patterns_per_minute, 2),
                    'performance_compliance_percent': round(performance_compliance_ratio * 100, 1),
                    'uptime_hours': round(runtime_seconds / 3600, 1)
                },
                'component_health': {
                    'tier_pattern_integration': tier_integration_health,
                    'websocket_manager': ws_manager_health
                },
                'performance_targets': {
                    'user_filtering_ms': 5,
                    'intelligent_routing_ms': 20,
                    'batched_delivery_ms': 100,
                    'total_delivery_ms': 125,
                    'critical_alert_ms': 50,
                    'concurrent_users': 500,
                    'compliance_target_percent': 95
                }
            }
            
            logger.info(f"INTEGRATION-PATTERNS: Health report generated - Status: {overall_status}, "
                       f"Patterns: {self.integration_stats['patterns_processed']}, "
                       f"Users: {self.integration_stats['users_subscribed']}, "
                       f"Compliance: {performance_compliance_ratio*100:.1f}%")
            
            return health_report
            
        except Exception as e:
            logger.error(f"INTEGRATION-PATTERNS: Error generating health report: {e}")
            return {
                'overall_status': 'error',
                'error': str(e),
                'timestamp': time.time()
            }

# Usage Examples and Integration Templates

def example_sprint_25_feature_integration():
    """
    Complete example showing how Sprint 25+ features should integrate
    with the 4-layer WebSocket architecture.
    
    This example demonstrates all major integration patterns.
    """
    
    # Step 1: Initialize integration (normally done during app startup)
    # universal_ws_manager = UniversalWebSocketManager(...)  # From app initialization
    # integration_patterns = TierPatternIntegrationPatterns(universal_ws_manager)
    
    # Step 2: User subscription management
    # Basic daily pattern subscription
    # integration_patterns.subscribe_user_to_daily_patterns(
    #     user_id='conservative_trader',
    #     symbols=['AAPL', 'MSFT', 'GOOGL'],
    #     confidence_threshold=0.8
    # )
    
    # High-frequency scalping setup
    # integration_patterns.setup_scalping_trader(
    #     user_id='day_trader_pro',
    #     symbols=['SPY', 'QQQ', 'TSLA']
    # )
    
    # Step 3: Portfolio monitoring
    # portfolio = {
    #     'fund_manager_1': ['AAPL', 'MSFT'],
    #     'risk_analyst': ['SPY', 'VIX']
    # }
    # integration_patterns.setup_portfolio_monitoring(portfolio, 'risk_monitoring')
    
    # Step 4: Real-time pattern broadcasting
    # pattern_event = TierPatternEvent(...)
    # metrics = integration_patterns.broadcast_pattern_with_performance_tracking(pattern_event)
    
    # Step 5: Alert system
    # integration_patterns.create_and_send_pattern_alert(
    #     user_id='vip_trader',
    #     pattern_event=pattern_event,
    #     alert_priority=EventPriority.CRITICAL
    # )
    
    # Step 6: Health monitoring
    # health_report = integration_patterns.get_comprehensive_health_report()
    
    logger.info("INTEGRATION-PATTERNS: Example Sprint 25+ feature integration template provided")

if __name__ == "__main__":
    example_sprint_25_feature_integration()