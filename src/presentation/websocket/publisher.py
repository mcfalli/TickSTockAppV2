import threading
import time
import json
import traceback
from datetime import datetime
from typing import Dict, List, Any, Optional, Set, Tuple
import pytz
import logging
from config.logging_config import get_domain_logger, LogDomain
from collections import defaultdict
from functools import lru_cache
import hashlib

from src.presentation.websocket.filter_cache import WebSocketFilterCache
from src.presentation.websocket.data_filter import WebSocketDataFilter
from src.presentation.websocket.analytics import WebSocketAnalytics
from src.presentation.websocket.display_converter import WebSocketDisplayConverter
from src.core.services.user_filters_service import UserFiltersService
from src.core.services.user_settings_service import UserSettingsService
from src.presentation.websocket.universe_cache import WebSocketUniverseCache
from src.core.domain.events.base import BaseEvent
from src.core.domain.events.trend import TrendEvent
from src.core.domain.events.surge import SurgeEvent
from src.presentation.converters.transport_models import StockData

try:
    from src.monitoring.system_monitor import system_monitor
    HAS_MONITORING = True
except ImportError:
    HAS_MONITORING = False
    system_monitor = None

from src.monitoring.tracer import tracer, TraceLevel, normalize_event_type, ensure_int

logger = get_domain_logger(LogDomain.CORE, 'websocket_publisher')

class EmissionMetrics:
    """SPRINT 27: Track filtering performance at emission point"""
    def __init__(self):
        self.events_before_filter = 0
        self.events_after_filter = 0
        self.filter_time_ms = 0
        self.users_processed = 0
        self.reset_time = time.time()

    '''
    def log_summary(self):
        if self.events_before_filter == 0:
            return
            
        efficiency = (self.events_after_filter / self.events_before_filter) * 100
        avg_time = self.filter_time_ms / max(self.users_processed, 1)
        
        logger.info(
            f"📊 SPRINT27 Emission Metrics - "
            f"Efficiency: {efficiency:.1f}%, "
            f"Avg filter time: {avg_time:.1f}ms/user, "
            f"Total filtered: {self.events_before_filter - self.events_after_filter}"
        )
    '''    

    def reset(self):
        self.__init__()

class WebSocketPublisher:
    """
    Enhanced WebSocket publisher with comprehensive universe filtering logging.
    Handles preparing and sending data to WebSocket clients with detailed
    tracking of what gets filtered vs what reaches the frontend.
    """
    
    def __init__(self, websocket_mgr, config, cache_control=None):
        """
        Initialize the WebSocket publisher with comprehensive diagnostics.
        
        Args:
            websocket_mgr: WebSocketManager instance for sending messages
            config: Application configuration dictionary
            cache_control: CacheControl instance for universe validation
        """
        init_start_time = time.time()
        
        self.websocket_mgr = websocket_mgr
        self.config = config
        self.cache_control = cache_control
        
        # Sprint 17: Store market_service reference if available
        self.market_service = getattr(websocket_mgr, 'market_service', None)

        # SPRINT 29: Add data_publisher reference and emission control
        self.data_publisher = None  # Will be set by market_service
        self.emission_lock = threading.Lock()
        self.emission_interval = config.get('EMISSION_INTERVAL', 1.0)  # seconds
        self.emission_timer = None
        self.emission_in_progress = False
        self.last_emission_time = 0

        # Initialize statistics component
        from src.presentation.websocket.statistics import WebSocketStatistics
        self.statistics = WebSocketStatistics()
        
        # Add universe tracking logger
        from config.logging_config import get_domain_logger, LogDomain
        self.universe_logger = get_domain_logger(LogDomain.UNIVERSE_TRACKING, 'websocket_publisher')
        
        self.last_non_empty_emission = time.time() 
        
        # Initialize user settings service FIRST (needed by universe cache)
        try:
            from flask import current_app
            app = None
            try:
                app = current_app._get_current_object()
            except RuntimeError:
                # No app context during initialization, will be set later
                pass
            
            self.user_settings_service = UserSettingsService(cache_control=cache_control, app=app)
        except ImportError as e:
            logger.warning(f"WEBSOCKET-PUB: UserSettingsService not available: {e}")
            self.user_settings_service = None
        except Exception as e:
            logger.error(f"WEBSOCKET-PUB: Error initializing UserSettingsService: {e}")
            self.user_settings_service = None
        
   
        
        # NOW initialize universe cache component (AFTER user_settings_service)
        self.universe_cache = WebSocketUniverseCache(
            user_settings_service=self.user_settings_service,
            cache_control=cache_control
        )
        self.data_filter = WebSocketDataFilter(cache_control=cache_control)
        
        # Initialize analytics with debug logger now that it exists
        self.analytics = WebSocketAnalytics(
            cache_control=cache_control,
            config=config
        )

        # Initialize display converter
        self.display_converter = WebSocketDisplayConverter(config)

        self.user_filters_service = None
        self.user_filters_service = UserFiltersService()

        self.filter_cache = WebSocketFilterCache(
            user_filters_service=self.user_filters_service,
            app=app
        )


        # WebSocket emission tracking
        self.heartbeat_interval = config.get('HEARTBEAT_INTERVAL', 2.0)
        self.last_stock_emit_time = time.time()
        self.heartbeat_thread = None
        self.is_running = False
        self.eastern_tz = pytz.timezone(config.get('MARKET_TIMEZONE', 'US/Eastern'))
        

        # SPRINT 27: Performance cache for filtered data
        self.filtered_data_cache = {}
        self.cache_ttl = config.get('WEBSOCKET_FILTER_CACHE_TTL', 0.5)  # 500ms default
        self.cache_hits = 0
        self.cache_misses = 0
        self.last_cache_cleanup = time.time()
        self.cache_cleanup_interval = 5.0  # Clean old entries every 5 seconds


        # SPRINT 27: Add emission metrics
        self.emission_metrics = EmissionMetrics()

        # Log startup with multi-user status
        logger.info(f"🚀WEBSOCKET-PUB: WebSocketPublisher initialized - Multi-user: {hasattr(websocket_mgr, 'user_connections') if websocket_mgr else False}")
        
        # Enhanced universe logging
        self.universe_logger.info("🚀 WebSocketPublisher initialized with per-user universe caching")
        
        # TRACE: Initialization complete
        if tracer.should_trace('SYSTEM'):
            tracer.trace(
                ticker='SYSTEM',
                component='WebSocketPublisher',
                action='initialization_complete',
                data={
                    'timestamp': time.time(),
                    'input_count': ensure_int(0),
                    'output_count': ensure_int(0),
                    'duration_ms': (time.time() - init_start_time) * 1000,
                    'details': {
                        'heartbeat_interval': self.heartbeat_interval,
                        'cache_ttl': self.cache_ttl,
                        'cache_cleanup_interval': self.cache_cleanup_interval,
                        'has_websocket_mgr': self.websocket_mgr is not None,
                        'has_market_service': self.market_service is not None,
                        'multi_user_enabled': hasattr(websocket_mgr, 'user_connections') if websocket_mgr else False
                    }
                }
            )
    #----------------------------------------------------------------
    # WebSocket Publisher Setup
    #----------------------------------------------------------------
    def set_data_publisher(self, data_publisher):
        """Set reference to data publisher and start emission timer."""
        self.data_publisher = data_publisher
        logger.info("📊 WebSocketPublisher: Data publisher reference set")
        self.start_emission_timer()

    def start_emission_timer(self):
        """Start the pull-based emission cycle timer."""
        if self.emission_timer:
            logger.warning("Emission timer already running")
            return
            
        self.is_running = True
        
        def emission_loop():
            logger.info("🚀 WebSocketPublisher: Starting emission timer loop")
            while self.is_running:
                try:
                    current_time = time.time()
                    if current_time - self.last_emission_time >= self.emission_interval:
                        self.run_emission_cycle()
                        self.last_emission_time = current_time
                except Exception as e:
                    logger.error(f"❌ Emission cycle error: {e}", exc_info=True)
                
                time.sleep(0.1)  # Prevent CPU spinning
        
        self.emission_timer = threading.Thread(
            target=emission_loop, 
            daemon=True,
            name="websocket-emission-timer"
        )
        self.emission_timer.start()
        logger.info("✅ WebSocketPublisher: Emission timer started")

    #----------------------------------------------------------------
    # Emission Cycle Methods
    #----------------------------------------------------------------
    def run_emission_cycle(self):
        """Main emission cycle - pulls events and emits to users."""
        
        # TRACE: Cycle attempt (before any checks)
        if tracer.should_trace('SYSTEM'):
            tracer.trace(
                ticker='SYSTEM',
                component='WebSocketPublisher',
                action='emission_cycle_attempt',
                data={
                    'timestamp': time.time(),
                    'details': {
                        'in_progress': self.emission_in_progress
                    }
                }
            )


        # Prevent overlapping cycles
        if self.emission_in_progress:
            logger.debug("Emission already in progress, skipping")
            return
            
        with self.emission_lock:
            try:
                self.emission_in_progress = True
                cycle_start_time = time.time()
                
                # TRACE: Start emission cycle
                if tracer.should_trace('SYSTEM'):
                    tracer.trace(
                        ticker='SYSTEM',
                        component='WebSocketPublisher',
                        action='emission_cycle_start',
                        data={
                            'timestamp': time.time(),
                            'input_count': 0,
                            'output_count': 0,
                            'duration_ms': 0,
                            'details': {
                                'stage': 'starting',
                                'last_emission_time': self.last_emission_time
                            }
                        }
                    )
                
                # Check if we have connected users first
                connected_users = []
                if self.websocket_mgr:
                    connected_users = self.websocket_mgr.get_connected_user_ids()
                
                if not connected_users:
                    # Notify monitor about skip due to no users
                    if HAS_MONITORING and system_monitor and hasattr(system_monitor, 'track_emission_skip'):
                        system_monitor.track_emission_skip('no_users_connected')
                    return
                
                # Pull events from DataPublisher with performance monitoring
                if not self.data_publisher:
                    return
                    
                buffer_pull_start = time.time()
                stock_data = self.data_publisher.get_buffered_events(clear_buffer=True)
                buffer_pull_duration = (time.time() - buffer_pull_start) * 1000
                
                # TRACE: Slow buffer pull
                if tracer.should_trace('SYSTEM') and buffer_pull_duration > 10:
                    tracer.trace(
                        ticker='SYSTEM',
                        component='WebSocketPublisher',
                        action='slow_buffer_pull',
                        data={
                            'timestamp': time.time(),
                            'input_count': self._count_total_events(stock_data),
                            'output_count': self._count_total_events(stock_data),
                            'duration_ms': buffer_pull_duration,
                            'details': {
                                'threshold_ms': 10,
                                'event_breakdown': {
                                    'highs': len(stock_data.get('highs', [])),
                                    'lows': len(stock_data.get('lows', [])),
                                    'trends': sum(len(stock_data.get('trending', {}).get(d, [])) for d in ['up', 'down']),
                                    'surges': sum(len(stock_data.get('surging', {}).get(d, [])) for d in ['up', 'down'])
                                }
                            }
                        }
                    )
                
                #analytics_data = self.data_publisher.market_service.get_analytics_for_websocket()
                analytics_data = None
                if hasattr(self.data_publisher, 'market_service') and self.data_publisher.market_service:
                    # Try to get full analytics data
                    if hasattr(self.data_publisher.market_service, 'get_analytics_for_websocket'):
                        analytics_data = self.data_publisher.market_service.get_analytics_for_websocket()
                        logger.debug(f"📊 Got analytics data with keys: {list(analytics_data.keys()) if analytics_data else 'None'}")
                    else:
                        # Fallback: just get session totals
                        analytics_data = {}
                        if hasattr(self.data_publisher.market_service, 'get_session_accumulation_totals'):
                            session_totals = self.data_publisher.market_service.get_session_accumulation_totals()
                            analytics_data['session_totals'] = session_totals
                            logger.debug(f"📊 Got session totals directly: {session_totals}")
                        elif hasattr(self.data_publisher.market_service, 'session_accumulation_manager'):
                            # Try direct access to accumulation manager
                            session_totals = self.data_publisher.market_service.session_accumulation_manager.get_session_totals()
                            analytics_data['session_totals'] = session_totals
                            logger.debug(f"📊 Got session totals from accumulation manager: {session_totals}")
                        elif hasattr(self.data_publisher.market_service, 'market_analytics_manager'):
                            # Try alternative method
                            analytics_data = getattr(self.data_publisher.market_service.market_analytics_manager, 'get_current_analytics', lambda: None)()
                             
                
                # Count total events
                total_events = self._count_total_events(stock_data)
                
                # Determine skip reason if applicable
                skip_reason = None
                if total_events == 0 and len(connected_users) == 0:
                    skip_reason = 'no_events_no_users'
                elif total_events == 0 and len(connected_users) > 0:
                    skip_reason = 'no_events_with_users'
                elif total_events > 0 and len(connected_users) == 0:
                    skip_reason = 'events_but_no_users'
                
                # Handle skip cases
                if skip_reason:
                    # Notify monitor
                    if HAS_MONITORING and system_monitor and hasattr(system_monitor, 'track_emission_skip'):
                        system_monitor.track_emission_skip(skip_reason)
                    
                    # Check for emission drought only when no events
                    if 'no_events' in skip_reason:
                        if hasattr(self, 'last_non_empty_emission') and self.last_non_empty_emission:
                            time_since_last = time.time() - self.last_non_empty_emission
                            if tracer.should_trace('SYSTEM') and time_since_last > 5.0:
                                tracer.trace(
                                    ticker='SYSTEM',
                                    component='WebSocketPublisher',
                                    action='emission_drought',
                                    data={
                                        'timestamp': time.time(),
                                        'input_count': 0,
                                        'output_count': 0,
                                        'details': {
                                            'seconds_since_last_event': time_since_last,
                                            'connected_users': len(connected_users),
                                            'skip_reason': skip_reason
                                        }
                                    }
                                )
                    
                    return  # Exit early for any skip reason
                
                # We have events and users - update last non-empty emission time
                self.last_non_empty_emission = time.time()
                
                # Mark events as ready for emission (moved from DataPublisher)
                self._mark_events_ready(stock_data)
                
                # Emit to each user with filtering
                events_emitted = 0
                users_reached = 0
                
                for user_id in connected_users:
                    user_events = self._process_user_data(user_id, stock_data, analytics_data)
                    if user_events and self._has_events(user_events):
                        self.websocket_mgr.emit_to_user(user_events, user_id, 'stock_data')
                        events_emitted += self._count_user_events(user_events)
                        users_reached += 1
                        
                        # Trace emissions
                        self._trace_user_emissions(user_id, user_events)
                
                # TRACE: Complete emission cycle with performance metrics
                elapsed_ms = (time.time() - cycle_start_time) * 1000
                if tracer.should_trace('SYSTEM'):
                    tracer.trace(
                        ticker='SYSTEM',
                        component='WebSocketPublisher',
                        action='emission_cycle_complete',
                        data={
                            'timestamp': time.time(),
                            'input_count': total_events,
                            'output_count': events_emitted,
                            'duration_ms': elapsed_ms,
                            'details': {
                                'users_count': len(connected_users),
                                'users_reached': users_reached,
                                'events_emitted': events_emitted,
                                'buffer_pull_ms': buffer_pull_duration,
                                'processing_time_ms': elapsed_ms - buffer_pull_duration,
                                'events_per_second': (events_emitted / elapsed_ms * 1000) if elapsed_ms > 0 else 0,
                                'efficiency': (events_emitted / total_events * 100) if total_events > 0 else 0
                            }
                        }
                    )
                    
            except Exception as e:
                logger.error(f"Emission cycle failed: {e}", exc_info=True)
                if tracer.should_trace('SYSTEM'):
                    tracer.trace(
                        ticker='SYSTEM',
                        component='WebSocketPublisher',
                        action='emission_cycle_error',
                        data={
                            'timestamp': time.time(),
                            'error': str(e),
                            'details': {
                                'error_type': type(e).__name__
                            }
                        }
                    )
            finally:
                self.emission_in_progress = False

    #---------------------------------------------------------------------
    #---------------------------------------------------------------------
    # Apply user filtering to data, process user data
    #---------------------------------------------------------------------
    #---------------------------------------------------------------------
    def _process_user_data(self, user_id: int, stock_data: Dict, analytics_data=None) -> Dict:
        """
        Purpose
        This method is the central filtering hub that applies both universe filtering and user-specific filters to stock data 
        before it's emitted to individual users via WebSocket. 
        It's part of Sprint 27's architecture where ALL filtering happens at emission time only.        
        """

        filter_start_time = time.time()
        
        try:

            # ADD TRACE: User filtering start
            if tracer.should_trace('SYSTEM'):
                tracer.trace(
                    ticker='SYSTEM',
                    component="WebSocketPublisher",
                    action="user_filtering_start",
                    data={
                        'timestamp': time.time(),
                        'input_count': ensure_int(self._count_all_events(stock_data)),
                        'output_count': ensure_int(0),  # Not yet filtered
                        'duration_ms': 0,   # Just starting
                        'details': {
                            "user_id": user_id
                        }
                    }
                )

            # Get user's universe selections
            user_universes = self.universe_cache.get_or_load_user_universes(user_id)
            
            # SPRINT 27: Resolve universe names to actual tickers
            all_user_tickers = self._resolve_user_universes_to_tickers(user_universes)
            
            if tracer.should_trace('NVDA'):
                # Count NVDA events before filtering
                nvda_highs_before = sum(1 for e in stock_data.get('highs', []) 
                                    if (e.ticker if hasattr(e, 'ticker') else e.get('ticker')) == 'NVDA')
                nvda_lows_before = sum(1 for e in stock_data.get('lows', []) 
                                    if (e.ticker if hasattr(e, 'ticker') else e.get('ticker')) == 'NVDA')
                
                if nvda_highs_before > 0 or nvda_lows_before > 0:
                    tracer.trace(
                        ticker='NVDA',
                        component="WebSocketPublisher",
                        action="filtering_nvda_events",
                        data={
                            'timestamp': time.time(),
                            'input_count': ensure_int(nvda_highs_before + nvda_lows_before),
                            'output_count': ensure_int(0),  # Not yet known
                            'duration_ms': 0,
                            'details': {
                                "user_id": user_id,
                                "nvda_in_universe": 'NVDA' in all_user_tickers,
                                "highs_before": nvda_highs_before,
                                "lows_before": nvda_lows_before,
                                "universe_size": len(all_user_tickers)
                            }
                        }
                    )

            if tracer.should_trace('SYSTEM'):
                tracer.trace(
                    ticker='SYSTEM',
                    component="WebSocketPublisher",
                    action="universe_resolved",
                    data={
                        'timestamp': time.time(),
                        'input_count': ensure_int(len(user_universes.get('market', [])) + len(user_universes.get('highlow', []))),  # Universe names
                        'output_count': ensure_int(len(all_user_tickers)),  # Resolved tickers
                        'duration_ms': (time.time() - filter_start_time) * 1000,
                        'details': {
                            "user_id": user_id,
                            "universe_names": list(user_universes.get('market', [])) + list(user_universes.get('highlow', [])),
                            "sample_tickers": list(all_user_tickers)[:10]
                        }
                    }
                )

            if len(all_user_tickers) == 0:
                # For now, return unfiltered data so they see something
                return self.analytics.prepare_enhanced_dual_universe_data(
                    stock_data, 
                    analytics_data, 
                    user_id
                )
            
            # Rest of the filtering logic remains the same...
            # Filter events to user's universe
            filtered_data = {
                'highs': [],
                'lows': [],
                'trending': {'up': [], 'down': []},
                'surging': {'up': [], 'down': []}
            }
            
            # Filter high/low events
            for event in stock_data.get('highs', []):
                ticker = event.ticker if hasattr(event, 'ticker') else event.get('ticker')
                if ticker in all_user_tickers:
                    filtered_data['highs'].append(event)
            
            for event in stock_data.get('lows', []):
                ticker = event.ticker if hasattr(event, 'ticker') else event.get('ticker')
                if ticker in all_user_tickers:
                    filtered_data['lows'].append(event)
            
            # Filter trending events
            for direction in ['up', 'down']:
                for event in stock_data.get('trending', {}).get(direction, []):
                    ticker = event.get('ticker') if isinstance(event, dict) else getattr(event, 'ticker', None)
                    if ticker in all_user_tickers:
                        filtered_data['trending'][direction].append(event)
            
            # Filter surging events
            for direction in ['up', 'down']:
                for event in stock_data.get('surging', {}).get(direction, []):
                    ticker = event.get('ticker') if isinstance(event, dict) else getattr(event, 'ticker', None)
                    if ticker in all_user_tickers:
                        filtered_data['surging'][direction].append(event)
            
            # Apply user-specific filters (like low count filtering)
            user_filters = self.filter_cache.get_or_load_user_filters(user_id)
            if user_filters and user_filters.get('low_event_filtering', {}).get('enabled', False):
                min_low_count = user_filters['low_event_filtering'].get('min_low_count', 2)
                
                # Track low counts per ticker
                ticker_low_counts = {}
                for event in filtered_data['lows']:
                    ticker = event.ticker if hasattr(event, 'ticker') else event.get('ticker')
                    count = event.count if hasattr(event, 'count') else event.get('count', 1)
                    ticker_low_counts[ticker] = count
                
                # Filter out tickers below threshold
                filtered_data['lows'] = [
                    event for event in filtered_data['lows']
                    if ticker_low_counts.get(
                        event.ticker if hasattr(event, 'ticker') else event.get('ticker'), 0
                    ) >= min_low_count
                ]
            
            # Log filtering results
            original_counts = {
                'highs': len(stock_data.get('highs', [])),
                'lows': len(stock_data.get('lows', [])),
                'trends': sum(len(stock_data.get('trending', {}).get(d, [])) for d in ['up', 'down']),
                'surges': sum(len(stock_data.get('surging', {}).get(d, [])) for d in ['up', 'down'])
            }
            
            filtered_counts = {
                'highs': len(filtered_data['highs']),
                'lows': len(filtered_data['lows']),
                'trends': sum(len(filtered_data['trending'].get(d, [])) for d in ['up', 'down']),
                'surges': sum(len(filtered_data['surging'].get(d, [])) for d in ['up', 'down'])
            }
            
            
            # After filtering is complete
            if tracer.should_trace('NVDA'):
                # Count NVDA events after filtering
                nvda_highs_after = sum(1 for e in filtered_data.get('highs', []) 
                                    if (e.ticker if hasattr(e, 'ticker') else e.get('ticker')) == 'NVDA')
                nvda_lows_after = sum(1 for e in filtered_data.get('lows', []) 
                                    if (e.ticker if hasattr(e, 'ticker') else e.get('ticker')) == 'NVDA')
                
                if nvda_highs_before > 0 or nvda_lows_before > 0 or nvda_highs_after > 0 or nvda_lows_after > 0:
                    tracer.trace(
                        ticker='NVDA',
                        component="WebSocketPublisher",
                        action="nvda_filter_result",
                        data={
                            'timestamp': time.time(),
                            'input_count': ensure_int(nvda_highs_before + nvda_lows_before),
                            'output_count': ensure_int(nvda_highs_after + nvda_lows_after),
                            'duration_ms': (time.time() - filter_start_time) * 1000,
                            'details': {
                                "user_id": user_id,
                                "highs_filtered": nvda_highs_before - nvda_highs_after,
                                "lows_filtered": nvda_lows_before - nvda_lows_after,
                                "filter_reason": "universe" if 'NVDA' not in all_user_tickers else "other"
                            }
                        }
                    )
            # TRACE: User filtering complete
            if tracer.should_trace('SYSTEM'):
                total_original = sum(original_counts.values())
                total_filtered = sum(filtered_counts.values())
                
                tracer.trace(
                    ticker='SYSTEM',
                    component="WebSocketPublisher",
                    action="user_filtering_complete",
                    data={
                        'timestamp': time.time(),
                        'input_count': ensure_int(total_original),
                        'output_count': ensure_int(total_filtered),
                        'duration_ms': (time.time() - filter_start_time) * 1000,
                        'details': {
                            "user_id": user_id,
                            "original_counts": original_counts,
                            "filtered_counts": filtered_counts,
                            "filter_efficiency": (total_filtered / total_original * 100) if total_original > 0 else 0,
                            "universe_size": len(all_user_tickers)
                        }
                    }
                )
            

            # S32 - Converting processed data to display format
            # Prepare final data package with analytics
            #return self.analytics.prepare_enhanced_dual_universe_data(
            #    filtered_data, 
            #    analytics_data, 
            #    user_id
            #)
            # S32 - Converting processed data to display format
            # Prepare final data package with analytics
            full_data = self.analytics.prepare_enhanced_dual_universe_data(
                filtered_data, 
                analytics_data, 
                user_id
            )
            # S32 - Converting processed data to display format
            # Convert to display format - Convert full internal data to display-ready format
            display_data = self._convert_to_display_data(full_data)
            
            return display_data
        

                
        except Exception as e:
            logger.error(f"❌ Error filtering data for user {user_id}: {e}", exc_info=True)
            
            # TRACE: Error
            if tracer.should_trace('SYSTEM'):
                tracer.trace(
                    ticker='SYSTEM',
                    component="WebSocketPublisher",
                    action="user_filtering_error",
                    data={
                        'timestamp': time.time(),
                        'input_count': ensure_int(self._count_all_events(stock_data)),
                        'output_count': ensure_int(0),
                        'duration_ms': (time.time() - filter_start_time) * 1000,
                        'error': str(e),
                        'details': {
                            "user_id": user_id,
                            "error_type": type(e).__name__
                        }
                    }
                )
            
            # Return original data on error
            return self.analytics.prepare_enhanced_dual_universe_data(
                stock_data, 
                analytics_data, 
                user_id
            )


    #---------------------------------------------------------------------
    #---------------------------------------------------------------------
    #---------------------------------------------------------------------
    #---------------------------------------------------------------------



    #----------------------------------------------------------------
    # Per-User Emission Logic
    #----------------------------------------------------------------
    def _mark_events_ready(self, stock_data: Dict):
        """
        SPRINT 29: Marks events as ready for emission within the emission cycle.
        This replaces the traces that were previously in DataPublisher.
        """
        # Mark high events
        for event in stock_data.get('highs', []):
            ticker = event.get('ticker') if isinstance(event, dict) else getattr(event, 'ticker', 'UNKNOWN')
            if tracer.should_trace(ticker):
                tracer.trace(
                    ticker=ticker,
                    component='WebSocketPublisher',
                    action='event_ready_for_emission',
                    data={
                        'timestamp': time.time(),
                        'input_count': 1,
                        'output_count': 1,
                        'details': {
                            'event_type': 'high',
                            'event_id': getattr(event, 'event_id', None) if hasattr(event, 'event_id') else event.get('event_id'),
                            'price': getattr(event, 'price', None) if hasattr(event, 'price') else event.get('price'),
                            'in_emission_cycle': True,
                            'stage': 'emission_cycle'
                        }
                    }
                )
        
        # Mark low events
        for event in stock_data.get('lows', []):
            ticker = event.get('ticker') if isinstance(event, dict) else getattr(event, 'ticker', 'UNKNOWN')
            if tracer.should_trace(ticker):
                tracer.trace(
                    ticker=ticker,
                    component='WebSocketPublisher',
                    action='event_ready_for_emission',
                    data={
                        'timestamp': time.time(),
                        'input_count': 1,
                        'output_count': 1,
                        'details': {
                            'event_type': 'low',
                            'event_id': getattr(event, 'event_id', None) if hasattr(event, 'event_id') else event.get('event_id'),
                            'price': getattr(event, 'price', None) if hasattr(event, 'price') else event.get('price'),
                            'in_emission_cycle': True,
                            'stage': 'emission_cycle'
                        }
                    }
                )
        
        # Mark trend events
        for direction in ['up', 'down']:
            for event in stock_data.get('trending', {}).get(direction, []):
                ticker = event.get('ticker') if isinstance(event, dict) else getattr(event, 'ticker', 'UNKNOWN')
                if tracer.should_trace(ticker):
                    tracer.trace(
                        ticker=ticker,
                        component='WebSocketPublisher',
                        action='event_ready_for_emission',
                        data={
                            'timestamp': time.time(),
                            'input_count': 1,
                            'output_count': 1,
                            'details': {
                                'event_type': f'trend',
                                'direction': direction,
                                'event_id': event.get('event_id') if isinstance(event, dict) else getattr(event, 'event_id', None),
                                'in_emission_cycle': True,
                                'stage': 'emission_cycle'
                            }
                        }
                    )
        
        # Mark surge events
        for direction in ['up', 'down']:
            for event in stock_data.get('surging', {}).get(direction, []):
                ticker = event.get('ticker') if isinstance(event, dict) else getattr(event, 'ticker', 'UNKNOWN')
                if tracer.should_trace(ticker):
                    tracer.trace(
                        ticker=ticker,
                        component='WebSocketPublisher',
                        action='event_ready_for_emission',
                        data={
                            'timestamp': time.time(),
                            'input_count': 1,
                            'output_count': 1,
                            'details': {
                                'event_type': f'surge',
                                'direction': direction,
                                'event_id': event.get('event_id') if isinstance(event, dict) else getattr(event, 'event_id', None),
                                'in_emission_cycle': True,
                                'stage': 'emission_cycle'
                            }
                        }
                    )

    
    def send_status_update(self, status, extra_info=None, user_id=None):
        """
        Send a status update to connected clients with per-user universe context.
        
        Args:
            status: Status string describing the current state
            extra_info: Optional dictionary with additional information
            user_id: Optional user ID for per-user context. If None, sends to all users with their own context
        """
        start_time = time.time()
        
        if not self.websocket_mgr:
            logger.warning("WEBSOCKET-PUB: No websocket_mgr available to send status update")
            return
        
        try:
            # Validate input parameters
            if not status:
                logger.warning("WEBSOCKET-PUB: send_status_update called with empty status")
                status = "unknown"
            
           
            # TRACE: Status update start
            if tracer.should_trace('SYSTEM'):
                tracer.trace(
                    ticker='SYSTEM',
                    component='WebSocketPublisher',
                    action='status_update_start',
                    data={
                        'timestamp': time.time(),
                        'input_count': ensure_int(1),
                        'output_count': ensure_int(0),
                        'duration_ms': 0,
                        'details': {
                            'status': status,
                            'user_specific': user_id is not None
                        }
                    }
                )
            
            # 🆕 SPRINT 1D.5 FIX: Handle per-user vs global status updates
            if user_id is not None:
                # Send to specific user with their universe context
                self._send_status_to_user(status, extra_info, None, user_id)
            else:
                # Send to all connected users with their individual universe contexts
                self._send_status_to_all_users(status, extra_info, None)
            
            # TRACE: Status update complete
            if tracer.should_trace('SYSTEM'):
                tracer.trace(
                    ticker='SYSTEM',
                    component='WebSocketPublisher',
                    action='status_update_complete',
                    data={
                        'timestamp': time.time(),
                        'input_count': ensure_int(1),
                        'output_count': ensure_int(1),
                        'duration_ms': (time.time() - start_time) * 1000,
                        'details': {
                            'status': status,
                            'user_specific': user_id is not None
                        }
                    }
                )
                
        except Exception as e:
            logger.error(f"Exception in send_status_update: {e}", exc_info=True)
            
            # TRACE: Error
            if tracer.should_trace('SYSTEM'):
                tracer.trace(
                    ticker='SYSTEM',
                    component='WebSocketPublisher',
                    action='status_update_error',
                    data={
                        'timestamp': time.time(),
                        'input_count': ensure_int(1),
                        'output_count': ensure_int(0),
                        'duration_ms': (time.time() - start_time) * 1000,
                        'error': str(e),
                        'details': {
                            'error_type': type(e).__name__
                        }
                    }
                )
            
            # Send emergency fallback status with minimal data
            try:
                fallback_status = {
                    'status': 'error',
                    'connected': False,
                    'provider': 'Unknown',
                    'timestamp': datetime.now().isoformat(),
                    'market_status': 'UNKNOWN',
                    'error': f'Status update failed: {str(e)}'
                }
                logger.info(f"WEBSOCKET-PUB: Sending fallback status: {fallback_status}")
                self.websocket_mgr.emit_update(fallback_status, event_name='status_update')
                logger.info("WEBSOCKET-PUB: Fallback status sent successfully")
            except Exception as fallback_error:
                logger.error(f"Even fallback status update failed: {fallback_error}", exc_info=True)

    def _send_status_to_user(self, status, extra_info, provider, user_id):
        """
        Send simplified status update to a specific user.
        
        Args:
            status: Status string
            extra_info: Additional status information
            provider: DEPRECATED - will be determined from market_metrics
            user_id: User ID to send to
        """
        try:
            # Get status data from market_metrics if available
            if hasattr(self, 'market_metrics') or (self.market_service and hasattr(self.market_service, 'market_metrics')):
                market_metrics = self.market_service.market_metrics if self.market_service else self.market_metrics
                
                # Build api_health dict for market_metrics
                api_health = {
                    'status': str(status),
                    'connected': True,
                    'response_times': []  # Could be populated from extra_info if available
                }
                
                # Get standardized status data
                status_data = market_metrics.get_status_metrics(api_health)
                
            else:
                # Fallback if market_metrics not available
                status_data = {
                    'status': str(status),
                    'connected': True,
                    'provider': 'Test',  # Default fallback
                    'timestamp': datetime.now().isoformat(),
                    'market_status': 'UNKNOWN',
                    'avg_response': 0
                }
            
            # Add any extra_info that's not already in status_data
            if extra_info and isinstance(extra_info, dict):
                processed_info = {}
                for k, v in extra_info.items():
                    if k not in status_data:  # Don't override market_metrics data
                        if isinstance(v, datetime):
                            processed_info[k] = v.isoformat()
                        elif v is not None:
                            processed_info[k] = v
                status_data.update(processed_info)
            
            # Send to specific user
            if hasattr(self.websocket_mgr, 'emit_to_user'):
                self.websocket_mgr.emit_to_user(status_data, user_id, 'status_update')
                logger.debug(f"WEBSOCKET-PUB: STATUS_UPDATE_USER_{user_id}: Sent simplified status")
            else:
                self.websocket_mgr.emit_update(status_data, event_name='status_update')
                
        except Exception as e:
            logger.error(f"Error sending status to user {user_id}: {e}")


    def _send_status_to_all_users(self, status, extra_info, provider):
        """
        Send simplified status update to all connected users.
        
        Args:
            status: Status string
            extra_info: Additional status information
            provider: DEPRECATED - will be determined from market_metrics
        """
        try:
            # Get connected users
            if hasattr(self.websocket_mgr, 'get_connected_user_ids'):
                connected_users = self.websocket_mgr.get_connected_user_ids()
            else:
                connected_users = []
            
            if not connected_users:
                # No users connected - send global status
                if hasattr(self, 'market_metrics') or (self.market_service and hasattr(self.market_service, 'market_metrics')):
                    market_metrics = self.market_service.market_metrics if self.market_service else self.market_metrics
                    
                    api_health = {
                        'status': str(status),
                        'connected': True,
                        'response_times': []
                    }
                    
                    status_data = market_metrics.get_status_metrics(api_health)
                else:
                    # Fallback
                    status_data = {
                        'status': str(status),
                        'connected': True,
                        'provider': 'Test',
                        'timestamp': datetime.now().isoformat(),
                        'market_status': 'UNKNOWN',
                        'avg_response': 0
                    }
                
                if extra_info and isinstance(extra_info, dict):
                    processed_info = {}
                    for k, v in extra_info.items():
                        if k not in status_data:
                            if isinstance(v, datetime):
                                processed_info[k] = v.isoformat()
                            elif v is not None:
                                processed_info[k] = v
                    status_data.update(processed_info)
                
                self.websocket_mgr.emit_update(status_data, event_name='status_update')
                logger.debug("WEBSOCKET-PUB: STATUS_UPDATE_GLOBAL: Sent to all (no users connected)")
                return
            
            # Send to each connected user
            for user_id in connected_users:
                try:
                    self._send_status_to_user(status, extra_info, None, user_id)
                except Exception as user_error:
                    logger.error(f"WEBSOCKET-PUB: Failed to send status to user {user_id}: {user_error}")
                    continue
            
            logger.debug(f"WEBSOCKET-PUB: STATUS_UPDATE_ALL_USERS: Sent to {len(connected_users)} users")
            
        except Exception as e:
            logger.error(f"Error sending status to all users: {e}")
            # Fallback to simple global emission
            status_data = {
                'status': str(status),
                'connected': True,
                'provider': 'Test',  # Simple fallback
                'timestamp': datetime.now().isoformat(),
                'market_status': 'UNKNOWN',
                'avg_response': 0
            }
            self.websocket_mgr.emit_update(status_data, event_name='status_update')
    
    def prepare_heartbeat(self, api_health, market_status, user_id=None):
        """Prepare simplified heartbeat data."""
        try:
            # Get metrics from centralized location
            if hasattr(self, 'market_metrics') or (self.market_service and hasattr(self.market_service, 'market_metrics')):
                market_metrics = self.market_service.market_metrics if self.market_service else self.market_metrics
                return market_metrics.get_status_metrics(api_health)
            else:
                # Fallback if market_metrics not available
                return {
                    "status": api_health.get("status", "unknown"),
                    "connected": api_health.get("connected", False),
                    "provider": "Test",
                    "market_status": str(market_status) if market_status else "UNKNOWN",
                    "timestamp": datetime.now().isoformat(),
                    "avg_response": 0
                }
        except Exception as e:
            logger.error(f"Error in prepare_heartbeat: {e}", exc_info=True)
            return {
                "status": "error",
                "connected": False,
                "provider": "Test",
                "market_status": "UNKNOWN",
                "timestamp": datetime.now().isoformat(),
                "avg_response": 0
            }
        
    
    
    
    def schedule_heartbeat(self, api_health, market_status):
        """
        Schedule a single heartbeat to be sent after the interval.
        
        Args:
            api_health: Dictionary with API health information
            market_status: Current market status string
        """
        if self.is_running:
            logger.debug("WEBSOCKET-PUB: Scheduling heartbeat")
            self.websocket_mgr.emit_heartbeat(self.prepare_heartbeat(api_health, market_status))
            threading.Timer(self.heartbeat_interval, 
                           lambda: self.schedule_heartbeat(api_health, market_status)).start()
        else:
            logger.debug("Heartbeat not scheduled: publisher not running")
    
    def start_heartbeat_loop(self, api_health, market_status):
        """Start heartbeat loop with enhanced connection monitoring"""
        start_time = time.time()
        self.is_running = True
        logger.info("💓WEBSOCKET-PUB: Starting heartbeat loop with connection monitoring")
        
        # TRACE: Heartbeat loop start
        if tracer.should_trace('SYSTEM'):
            tracer.trace(
                ticker='SYSTEM',
                component='WebSocketPublisher',
                action='heartbeat_loop_start',
                data={
                    'timestamp': time.time(),
                    'input_count': ensure_int(0),
                    'output_count': ensure_int(0),
                    'duration_ms': (time.time() - start_time) * 1000,
                    'details': {
                        'heartbeat_interval': self.heartbeat_interval
                    }
                }
            )
        
        def heartbeat_loop():
            heartbeat_count = 0
            last_user_check = 0
            connection_warnings = 0
            
            while self.is_running:
                try:
                    heartbeat_count += 1
                    
                    # Check connections more frequently - every 5 heartbeats (10 seconds)
                    if heartbeat_count % 5 == 0:
                        if hasattr(self.websocket_mgr, 'get_connected_user_ids'):
                            try:
                                users = self.websocket_mgr.get_connected_user_ids()
                                user_count = len(users)
                                
                                # Log user count changes
                                if user_count != last_user_check:
                                    if user_count > last_user_check:
                                        logger.info(f"📈 WEBSOCKET-PUB: User connections increased: {last_user_check} → {user_count}")
                                    elif user_count < last_user_check:
                                        logger.info(f"📉 WEBSOCKET-PUB: User connections decreased: {last_user_check} → {user_count}")
                                    last_user_check = user_count
                                
                                # Warn if no users
                                if user_count == 0:
                                    connection_warnings += 1
                                    if connection_warnings <= 3:  # Only warn first 3 times
                                        logger.warning(f"⚠️ WEBSOCKET-PUB: NO USERS CONNECTED! (warning {connection_warnings}/3)")
                                    elif connection_warnings == 10:  # Then every 10th time
                                        logger.warning("⚠️ WEBSOCKET-PUB: Still no users connected after 100 seconds")
                                        connection_warnings = 0
                                else:
                                    connection_warnings = 0  # Reset warnings when users connect
                                    if heartbeat_count % 15 == 0:  # Log every 30 seconds
                                        logger.info(f"💓 WEBSOCKET-PUB: HEARTBEAT: {user_count} users connected, emissions: {self.statistics.emission_stats.emissions_attempted}")
                                
                            except Exception as e:
                                logger.error(f"❌ Error checking user connections: {e}")
                        else:
                            if heartbeat_count == 1:  # Only warn once
                                logger.warning("⚠️ WEBSOCKET-PUB: Cannot check connected users - method not available")
                    
                    # Send heartbeat
                    try:
                        heartbeat_data = self.prepare_heartbeat(api_health, market_status)
                        self.websocket_mgr.emit_heartbeat(heartbeat_data)
                    except Exception as hb_error:
                        logger.error(f"❌ Error sending heartbeat: {hb_error}")
                    
                    # Log emission stats periodically (every 30 seconds)
                    if heartbeat_count % 15 == 0 and self.statistics.emission_stats.emissions_attempted > 0:
                        self.statistics.emission_stats.log_stats()
                        
                except Exception as e:
                    logger.error(f"❌ Heartbeat loop error: {e}", exc_info=True)
                    
                time.sleep(self.heartbeat_interval)
        
        self.heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()
        logger.info("💓 WEBSOCKET-PUB: Heartbeat thread started successfully")
    
    '''
    
    def handle_new_user_connection(self, user_id: int):
        """Handle when a new user connects - enhanced for pull model visibility."""
        start_time = time.time()
        
        try:
            logger.info(f"🔌 WEBSOCKET-PUB: New user {user_id} connected")
            
            # Track if this is our first user
            was_first_user = False
            if hasattr(self.websocket_mgr, 'get_authenticated_users'):
                current_users = self.websocket_mgr.get_authenticated_users()
                was_first_user = len(current_users) == 1  # Just this user
            
            # Check buffer status if we have a data publisher
            buffer_info = {}
            if self.data_publisher:
                buffer_info = self.data_publisher.get_buffer_status()
            
            # TRACE: New user connection with enhanced info
            if tracer.should_trace('SYSTEM'):
                tracer.trace(
                    ticker='SYSTEM',
                    component='WebSocketPublisher',
                    action='new_user_connection',
                    data={
                        'timestamp': time.time(),
                        'input_count': 1,
                        'output_count': 0,
                        'duration_ms': (time.time() - start_time) * 1000,
                        'details': {
                            'user_id': user_id,
                            'is_first_user': was_first_user,
                            'buffer_events_waiting': buffer_info.get('total', 0),
                            'buffer_breakdown': {
                                'highs': buffer_info.get('highs', 0),
                                'lows': buffer_info.get('lows', 0),
                                'trends': buffer_info.get('trends_up', 0) + buffer_info.get('trends_down', 0),
                                'surges': buffer_info.get('surges_up', 0) + buffer_info.get('surges_down', 0)
                            }
                        }
                    }
                )
            
            # If first user and we have buffered events, trace readiness
            if was_first_user and buffer_info.get('total', 0) > 0:
                if tracer.should_trace('SYSTEM'):
                    tracer.trace(
                        ticker='SYSTEM',
                        component='WebSocketPublisher',
                        action='user_ready_for_events',
                        data={
                            'timestamp': time.time(),
                            'input_count': buffer_info.get('total', 0),
                            'output_count': 0,  # Not emitted yet
                            'details': {
                                'user_id': user_id,
                                'buffered_events': buffer_info.get('total', 0),
                                'next_emission_in_seconds': max(0, self.emission_interval - (time.time() - self.last_emission_time))
                            }
                        }
                    )
            
            logger.info(f"📤 WEBSOCKET-PUB: User {user_id} ready for events on next cycle")
            
        except Exception as e:
            logger.error(f"❌ Error handling new user connection: {e}", exc_info=True)

    '''

    def stop_heartbeat_loop(self):
        """Stop the heartbeat loop and emission timer."""
        self.is_running = False
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            logger.debug("WEBSOCKET-PUB: Stopping heartbeat loop")
        
        # SPRINT 29: Also stop emission timer
        if self.emission_timer and self.emission_timer.is_alive():
            logger.debug("WEBSOCKET-PUB: Stopping emission timer")
            # Final emission cycle to clear any buffered events
            try:
                self.run_emission_cycle()
            except Exception as e:
                logger.error(f"Error in final emission cycle: {e}")

    
   
    def _log_enhanced_emission_results(self, cleaned_data: Dict, payload_size: int, 
                                    filter_start_time: float, analytics_data: Optional[Dict]):
        """
        🆕 SPRINT 2: Log emission results with enhanced analytics context.
        
        Args:
            cleaned_data: The cleaned data sent to frontend
            payload_size: Size of payload in bytes
            filter_start_time: When filtering started
            analytics_data: Analytics data that was included
        """
        try:
            filter_processing_time = (time.time() - filter_start_time) * 1000
            
            # Extract analytics status
            core_analytics_present = bool(cleaned_data.get('core_universe_analytics', {}).get('gauge_analytics'))
            user_analytics_present = bool(cleaned_data.get('user_universe_analytics', {}).get('gauge_analytics'))
            
            # Event counts
            highs_count = len(cleaned_data.get('highs', []))
            lows_count = len(cleaned_data.get('lows', []))
            
            self.universe_logger.info(
                f"WEBSOCKET-PUB: ENHANCED_DUAL_UNIVERSE_EMISSION: "
                f"Core analytics: {core_analytics_present}, User analytics: {user_analytics_present}, "
                f"Events: {highs_count}H/{lows_count}L "
                f"(payload: {payload_size:,} bytes, processing: {filter_processing_time:.1f}ms)"
            )
            
            # Log analytics integration details
            if analytics_data:
                self.universe_logger.debug(
                    f"WEBSOCKET-PUB: ANALYTICS_INTEGRATION: "
                    f"Source: {analytics_data.get('source', 'unknown')}, "
                    f"Timestamp: {analytics_data.get('timestamp', 'N/A')}"
                )
            
            # Update performance metrics using statistics component
            self.statistics.update_average_filter_time(filter_processing_time)
            
        except Exception as e:
            self.universe_logger.error(f"Error logging enhanced emission results: {e}")



    '''
    def integrate_trending_surging_into_emission(self, stock_data):
        """
        Sprint 21B: Integration now happens at collection time in data_publisher.
        This method is a pass-through for backward compatibility.
        """
        # Trends and surges are already in stock_data from collection
        return stock_data
    '''
    def _count_all_events(self, stock_data: dict) -> int:
        """Count total events in stock data for tracing"""
        try:
            count = 0
            
            # Count highs and lows
            count += len(stock_data.get('highs', []))
            count += len(stock_data.get('lows', []))
            
            # Count trending events
            trending = stock_data.get('trending', {})
            if isinstance(trending, dict):
                count += len(trending.get('up', []))
                count += len(trending.get('down', []))
            
            # Count surging events
            surging = stock_data.get('surging', {})
            if isinstance(surging, dict):
                count += len(surging.get('up', []))
                count += len(surging.get('down', []))
            
            return count
        except Exception as e:
            logger.error(f"Error counting events: {e}")
            return 0

    
    #---------------------------------------------------------------------
    # Display Format Conversion
    #---------------------------------------------------------------------
    def _convert_to_display_data(self, events_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert full events collection to display format.
        Delegates to WebSocketDisplayConverter for centralized logic.
        """
        # Convert using display converter
        display_data = self.display_converter.convert_to_display_data(events_data)
        
        # Track metrics for monitoring
        if(tracer.should_trace('SYSTEM')): 
            self._track_display_conversion_metrics(events_data, display_data)
        
        return display_data
    
    def _track_display_conversion_metrics(self, original_data: Dict, display_data: Dict):
        """Track metrics about display conversion for monitoring system."""
        try:
            start_time = time.time()
            
            # Initialize metrics tracking if needed
            if not hasattr(self, '_display_conversion_metrics'):
                self._display_conversion_metrics = {
                    'total_conversions': 0,
                    'total_bytes_saved': 0,
                    'total_reduction_percent': 0,
                    'avg_reduction_percent': 0,
                    'avg_conversion_time_ms': 0,
                    'last_conversion_time': 0
                }
            
            # Calculate sizes
            original_size = len(json.dumps(original_data, default=str))
            display_size = len(json.dumps(display_data, default=str))
            bytes_saved = original_size - display_size
            reduction_percent = ((original_size - display_size) / original_size) * 100
            conversion_time_ms = (time.time() - start_time) * 1000
            
            # Update rolling averages
            metrics = self._display_conversion_metrics
            metrics['total_conversions'] += 1
            metrics['total_bytes_saved'] += bytes_saved
            metrics['last_conversion_time'] = time.time()
            
            # Calculate rolling averages
            n = metrics['total_conversions']
            metrics['avg_reduction_percent'] = (
                (metrics['avg_reduction_percent'] * (n - 1) + reduction_percent) / n
            )
            metrics['avg_conversion_time_ms'] = (
                (metrics['avg_conversion_time_ms'] * (n - 1) + conversion_time_ms) / n
            )
            
        except Exception as e:
            logger.debug(f"Error tracking display conversion metrics: {e}")
    #---------------------------------------------------------------------





    #---------------------------------------------------------------------
    # Tracing User Emissions    
    #---------------------------------------------------------------------
    def _trace_user_emissions(self, user_id: int, user_events: Dict[str, Any]):
        """Trace events actually emitted to users."""
        if not tracer.should_trace('SYSTEM'):
            return
            
        # Trace high events emitted
        for event in user_events.get('highs', []):
            ticker = event.get('ticker', 'UNKNOWN')
            if tracer.should_trace(ticker):
                tracer.trace(
                    ticker=ticker,
                    component='WebSocketPublisher',
                    action='event_emitted',
                    data={
                        'timestamp': time.time(),
                        'input_count': 1,
                        'output_count': 1,
                        'details': {
                            'event_type': 'high',
                            'event_id': event.get('event_id'),
                            'user_id': user_id,
                            'price': event.get('price'),
                            'count_up': event.get('count_up', 0)
                        }
                    }
                )
        
        # Trace low events emitted
        for event in user_events.get('lows', []):
            ticker = event.get('ticker', 'UNKNOWN')
            if tracer.should_trace(ticker):
                tracer.trace(
                    ticker=ticker,
                    component='WebSocketPublisher',
                    action='event_emitted',
                    data={
                        'timestamp': time.time(),
                        'input_count': 1,
                        'output_count': 1,
                        'details': {
                            'event_type': 'low',
                            'event_id': event.get('event_id'),
                            'user_id': user_id,
                            'price': event.get('price'),
                            'count_down': event.get('count_down', 0)
                        }
                    }
                )
        
        # Trace trend events emitted
        trending = user_events.get('trending', {})
        if isinstance(trending, dict):
            for direction in ['up', 'down']:
                for event in trending.get(direction, []):
                    ticker = event.get('ticker', 'UNKNOWN')
                    if tracer.should_trace(ticker):
                        tracer.trace(
                            ticker=ticker,
                            component='WebSocketPublisher',
                            action='event_emitted',
                            data={
                                'timestamp': time.time(),
                                'input_count': 1,
                                'output_count': 1,
                                'details': {
                                    'event_type': 'trend',
                                    'direction': direction,
                                    'event_id': event.get('event_id'),
                                    'user_id': user_id,
                                    'price': event.get('price'),
                                    'count_up': event.get('count_up', 0),
                                    'count_down': event.get('count_down', 0)
                                }
                            }
                        )
        
        # Trace surge events emitted
        surging = user_events.get('surging', {})
        if isinstance(surging, dict):
            for direction in ['up', 'down']:
                for event in surging.get(direction, []):
                    ticker = event.get('ticker', 'UNKNOWN')
                    if tracer.should_trace(ticker):
                        tracer.trace(
                            ticker=ticker,
                            component='WebSocketPublisher',
                            action='event_emitted',
                            data={
                                'timestamp': time.time(),
                                'input_count': 1,
                                'output_count': 1,
                                'details': {
                                    'event_type': 'surge',
                                    'direction': direction,
                                    'event_id': event.get('event_id'),
                                    'user_id': user_id,
                                    'price': event.get('price'),
                                    'count_up': event.get('count_up', 0),
                                    'count_down': event.get('count_down', 0)
                                }
                            }
                        )

    def _count_total_events(self, stock_data: Dict[str, Any]) -> int:
        """Count total events in stock_data."""
        if not stock_data:
            return 0
            
        total = 0
        
        # Count highs and lows
        total += len(stock_data.get('highs', []))
        total += len(stock_data.get('lows', []))
        
        # Count trending events (up and down)
        trending = stock_data.get('trending', {})
        if isinstance(trending, dict):
            total += len(trending.get('up', []))
            total += len(trending.get('down', []))
        
        # Count surging events (up and down)
        surging = stock_data.get('surging', {})
        if isinstance(surging, dict):
            total += len(surging.get('up', []))
            total += len(surging.get('down', []))
        
        return total
    def _has_events(self, user_events: Dict[str, Any]) -> bool:
        """Check if user_events contains any actual events."""
        if not user_events:
            return False
            
        # Check for any non-empty event lists
        if len(user_events.get('highs', [])) > 0:
            return True
        if len(user_events.get('lows', [])) > 0:
            return True
            
        # Check trending
        trending = user_events.get('trending', {})
        if isinstance(trending, dict):
            if len(trending.get('up', [])) > 0 or len(trending.get('down', [])) > 0:
                return True
        
        # Check surging
        surging = user_events.get('surging', {})
        if isinstance(surging, dict):
            if len(surging.get('up', [])) > 0 or len(surging.get('down', [])) > 0:
                return True
                
        return False

    def _count_user_events(self, user_events: Dict[str, Any]) -> int:
        """Count events in user_events dict."""
        if not user_events:
            return 0
            
        count = 0
        count += len(user_events.get('highs', []))
        count += len(user_events.get('lows', []))
        
        # Count trending
        trending = user_events.get('trending', {})
        if isinstance(trending, dict):
            count += len(trending.get('up', []))
            count += len(trending.get('down', []))
        
        # Count surging  
        surging = user_events.get('surging', {})
        if isinstance(surging, dict):
            count += len(surging.get('up', []))
            count += len(surging.get('down', []))
            
        return count

    def _resolve_user_universes_to_tickers(self, user_universes: Dict[str, List[str]]) -> Set[str]:
        """Resolve universe names to actual ticker symbols."""
        all_user_tickers = set()
        
        # ADD TRACE: Track universe resolution process
        if tracer.should_trace('SYSTEM'):
            tracer.trace(
                ticker='SYSTEM',
                component="WebSocketPublisher",
                action="universe_resolution_start",
                data={
                    'timestamp': time.time(),
                    'input_count': ensure_int(len(user_universes.get('market', [])) + len(user_universes.get('highlow', []))),
                    'output_count': ensure_int(0),
                    'duration_ms': 0,
                    'details': {
                        "market_universes": user_universes.get('market', []),
                        "highlow_universes": user_universes.get('highlow', [])
                    }
                }
            )
        
        try:
            # Process market universes
            for universe_name in user_universes.get('market', []):
                if self.cache_control:
                    universe_tickers = self.cache_control.get_universe_tickers(universe_name)
                    if universe_tickers:
                        all_user_tickers.update(universe_tickers)
                        
                        # ADD TRACE: Check if NVDA is in resolved universe
                        if tracer.should_trace('NVDA') and 'NVDA' in universe_tickers:
                            tracer.trace(
                                ticker='NVDA',
                                component="WebSocketPublisher",
                                action="found_in_universe",
                                data={
                                    'timestamp': time.time(),
                                    'input_count': ensure_int(1),
                                    'output_count': ensure_int(1),
                                    'duration_ms': 0,
                                    'details': {
                                        "universe_name": universe_name,
                                        "universe_type": "market",
                                        "universe_size": len(universe_tickers)
                                    }
                                }
                            )
                    else:
                        logger.warning(f"Could not resolve universe {universe_name}")
            
            # Process highlow universes (similar trace for NVDA)
            for universe_name in user_universes.get('highlow', []):
                if self.cache_control:
                    universe_tickers = self.cache_control.get_universe_tickers(universe_name)
                    if universe_tickers:
                        all_user_tickers.update(universe_tickers)
                        
                        # ADD TRACE: Check if NVDA is in highlow universe
                        if tracer.should_trace('NVDA') and 'NVDA' in universe_tickers:
                            tracer.trace(
                                ticker='NVDA',
                                component="WebSocketPublisher",
                                action="found_in_universe",
                                data={
                                    'timestamp': time.time(),
                                    'input_count': ensure_int(1),
                                    'output_count': ensure_int(1),
                                    'duration_ms': 0,
                                    'details': {
                                        "universe_name": universe_name,
                                        "universe_type": "highlow",
                                        "universe_size": len(universe_tickers)
                                    }
                                }
                            )
                    else:
                        logger.warning(f"Could not resolve universe {universe_name}")
        
        except Exception as e:
            logger.error(f"Error resolving universes: {e}", exc_info=True)
        
        # ADD FINAL TRACE: Is NVDA in final ticker set?
        if tracer.should_trace('NVDA'):
            tracer.trace(
                ticker='NVDA',
                component="WebSocketPublisher",
                action="universe_resolution_complete",
                data={
                    'timestamp': time.time(),
                    'input_count': ensure_int(len(user_universes.get('market', [])) + len(user_universes.get('highlow', []))),
                    'output_count': ensure_int(len(all_user_tickers)),
                    'duration_ms': 0,
                    'details': {
                        "nvda_included": 'NVDA' in all_user_tickers,
                        "total_tickers": len(all_user_tickers),
                        "sample_tickers": list(all_user_tickers)[:10]
                    }
                }
            )
        
        return all_user_tickers
    

    def _should_track_statistics(self):
        """Check if statistics tracking is enabled"""
        # Check multiple possible config flags
        return (
            self.config.get('TRACK_FILTER_STATISTICS', True) or  # Specific flag
            self.config.get('DEBUG_MODE', False) or              # Debug mode
            self.config.get('ENABLE_DETAILED_LOGGING', False) or # Detailed logging
            logger.isEnabledFor(logging.DEBUG)                   # Logger debug level
        )

   

    def get_per_user_emission_stats(self) -> dict:
        """
        🆕 SPRINT 1D.2: Get statistics about per-user emissions.
        
        Returns:
            dict: Per-user emission statistics
        """
        try:
            if not hasattr(self.websocket_mgr, 'get_user_connection_stats'):
                return {'error': 'WebSocket manager not configured for per-user stats'}
            
            ws_stats = self.websocket_mgr.get_user_connection_stats()
            
            return {
                'connected_users': ws_stats.get('total_authenticated_users', 0),
                'total_user_connections': ws_stats.get('total_user_connections', 0),
                'avg_connections_per_user': ws_stats.get('avg_connections_per_user', 0),
                'total_emissions': self.statistics.get_filter_stats().get('emissions_count', 0),
                'per_user_filtering_enabled': True,
                'connections_per_user': ws_stats.get('connections_per_user', {}),
                'last_emission_time': self.last_stock_emit_time
            }
            
        except Exception as e:
            logger.error(f"Error getting per-user emission stats: {e}")
            return {'error': str(e)}

    '''
    def emit_to_specific_users(self, data: dict, user_ids: list, event_name: str = 'dual_universe_stock_data'):
        """
        🆕 SPRINT 1D.2: Emit data to specific list of users.
        Useful for targeted notifications or admin broadcasts.
        
        Args:
            data: Data to emit
            user_ids: List of user IDs to target
            event_name: WebSocket event name
            
        Returns:
            dict: Results of emission attempts
        """
        try:
            if not self.websocket_mgr or not hasattr(self.websocket_mgr, 'emit_to_user'):
                return {'error': 'WebSocket manager not configured for per-user emission'}
            
            results = {'successful': [], 'failed': []}
            cleaned_data = self.data_filter.sanitize_for_json(data)
            
            for user_id in user_ids:
                try:
                    success = self.websocket_mgr.emit_to_user(cleaned_data, user_id, event_name)
                    if success:
                        results['successful'].append(user_id)
                        logger.debug(f"WEBSOCKET-PUB: TARGETED_EMIT_SUCCESS: Data sent to user {user_id}")
                    else:
                        results['failed'].append(user_id)
                        logger.warning(f"WEBSOCKET-PUB: TARGETED_EMIT_FAILED: User {user_id} not connected")
                        
                except Exception as user_error:
                    results['failed'].append(user_id)
                    logger.error(f"WEBSOCKET-PUB: TARGETED_EMIT_ERROR: Error emitting to user {user_id}: {user_error}")
            
            logger.info(f"WEBSOCKET-PUB: TARGETED_EMIT_COMPLETE: {len(results['successful'])}/{len(user_ids)} users reached")
            return results
            
        except Exception as e:
            logger.error(f"Error in targeted user emission: {e}")
            return {'error': str(e), 'successful': [], 'failed': user_ids}
    '''

    '''
    def validate_per_user_setup(self) -> dict:
        """
        🆕 SPRINT 1D.2: Validate that per-user emission is properly configured.
        
        Returns:
            dict: Validation results
        """
        validation_results = {
            'websocket_manager_configured': False,
            'user_connection_tracking': False,
            'per_user_emission_ready': False,
            'issues': []
        }
        
        try:
            # Check WebSocket manager configuration
            if not self.websocket_mgr:
                validation_results['issues'].append('WebSocket manager not available')
                return validation_results
            
            validation_results['websocket_manager_configured'] = True
            
            # Check user connection tracking
            if not hasattr(self.websocket_mgr, 'user_connections'):
                validation_results['issues'].append('WebSocket manager missing user_connections attribute')
            elif not hasattr(self.websocket_mgr, 'emit_to_user'):
                validation_results['issues'].append('WebSocket manager missing emit_to_user method')
            else:
                validation_results['user_connection_tracking'] = True
            
            # Check if we can get connected users
            try:
                connected_users = self.websocket_mgr.get_connected_user_ids()
                validation_results['connected_users_count'] = len(connected_users)
                validation_results['per_user_emission_ready'] = True
            except Exception as e:
                validation_results['issues'].append(f'Cannot get connected users: {e}')
            
            # Overall status
            validation_results['overall_status'] = (
                'ready' if validation_results['per_user_emission_ready'] 
                else 'not_ready'
            )
            
            return validation_results
            
        except Exception as e:
            validation_results['issues'].append(f'Validation error: {e}')
            return validation_results
    '''
   
    def _replace_global_universe_calls(self):
        """
        🆕 SPRINT 1D.5 CHUNK 2: Helper method to identify remaining global universe calls.
        This method helps identify any remaining references to self.current_user_universes.
        """
        # Note: All methods that previously used self.current_user_universes should now:
        # 1. Accept a user_id parameter
        # 2. Call self.universe_cache.get_or_load_user_universes(user_id)
        # 3. Use the returned per-user selections
        
        # Methods that need updating in other chunks:
        # - send_status_update() - universe_context should be per-user
        # - prepare_heartbeat() - universe filtering stats should be aggregated
        
        pass

    