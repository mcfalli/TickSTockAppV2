"""
Simplified API Routes - Post-Cleanup
Essential API endpoints for the simplified TickStock architecture.
"""
import logging
from datetime import datetime, timezone

from flask import current_app, jsonify, request, session
from flask_login import login_required, current_user

from src.infrastructure.database import User, db, Subscription, UserSettings
from src.core.services.user_settings_service import UserSettingsService
from src.infrastructure.database.tickstock_db import TickStockDatabase

from src.presentation.websocket.publisher import WebSocketPublisher


logger = logging.getLogger(__name__)
api_logger = logging.getLogger(__name__)

def generate_realistic_mock_data(symbol, timeframe, num_bars=50):
    """Generate realistic mock OHLCV data for fallback scenarios."""
    from datetime import datetime, timedelta
    import random
    
    chart_data = []
    
    # Realistic base prices for different symbols
    base_prices = {
        'AAPL': 150.0, 'GOOGL': 2500.0, 'MSFT': 300.0, 'TSLA': 200.0,
        'AMZN': 3000.0, 'NVDA': 400.0, 'META': 250.0, 'NFLX': 400.0
    }
    base_price = base_prices.get(symbol, 100.0)
    current_time = datetime.utcnow()
    
    for i in range(num_bars):
        # More realistic price movement with volatility clustering
        volatility = random.uniform(0.5, 2.0) if random.random() < 0.3 else random.uniform(0.1, 0.8)
        price_change = random.gauss(0, volatility)
        
        open_price = max(0.01, base_price + price_change)
        high_price = open_price + abs(random.gauss(0, 0.5)) 
        low_price = max(0.01, open_price - abs(random.gauss(0, 0.5)))
        close_price = random.uniform(low_price, high_price)
        
        # Volume with realistic patterns
        base_volume = 500000 if base_price < 50 else 200000
        volume_multiplier = random.uniform(0.3, 3.0)
        volume = int(base_volume * volume_multiplier)
        
        # Time calculation based on timeframe
        if timeframe == '1d':
            timestamp = current_time - timedelta(days=num_bars-i)
        elif timeframe == '1w':
            timestamp = current_time - timedelta(weeks=num_bars-i)  
        elif timeframe == '1m':
            timestamp = current_time - timedelta(days=(num_bars-i)*30)
        else:
            timestamp = current_time - timedelta(hours=num_bars-i)
        
        chart_data.append({
            "timestamp": timestamp.isoformat() + "Z",
            "open": round(open_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "close": round(close_price, 2),
            "volume": volume
        })
        
        base_price = close_price  # Use close as next base price
    
    return chart_data


def register_api_routes(app, extensions, cache_control, config):
    """Register simplified API routes for essential functionality."""
    
    # Get instances from extensions
    mail = extensions.get('mail')
    
    # Initialize the user settings service
    user_settings_service = UserSettingsService(cache_control)
    
    # Initialize TickStock database connection for read-only queries
    tickstock_db = TickStockDatabase(config)
        
    @app.route('/api/cache', methods=['GET'])
    def get_cache_contents():
        """Debug endpoint to view cache contents."""
        if not config.get('APP_DEBUG', False):
            return jsonify({"error": "Debug endpoint disabled in non-debug mode"}), 403
        return jsonify(cache_control.get_cache_contents())

    @app.route('/api/cache/reset', methods=['POST'])
    def reset_cache():
        """Debug endpoint to reset cache."""
        try:
            cache_control.reset_cache()
            return jsonify({"status": "Cache reset successfully"})
        except Exception as e:
            logger.error("Error resetting cache: %s", str(e))
            return jsonify({"error": "Failed to reset cache"}), 500

    @app.route('/api/health')
    @login_required
    def api_health():
        """API health check endpoint with OHLCV persistence monitoring."""
        try:
            # Basic health checks
            db_healthy = True
            try:
                db.session.execute('SELECT 1')
            except Exception as e:
                logger.error("Database health check failed: %s", str(e))
                db_healthy = False

            # Market data service health check
            market_data_healthy = True
            market_service_stats = {}

            try:
                # Import market_service from global scope
                from src.app import market_service

                if market_service:
                    market_health = market_service.get_health_status()
                    market_data_healthy = market_health.get('service_running', False)

                    # Get market service stats
                    market_service_stats = {
                        'ticks_processed': market_health.get('ticks_processed', 0),
                        'last_tick_age_seconds': market_health.get('last_tick_age_seconds'),
                        'data_adapter_connected': market_health.get('data_adapter_connected', False)
                    }
                else:
                    market_data_healthy = False
                    
            except Exception as e:
                logger.error("Market data service health check failed: %s", str(e))
                market_data_healthy = False

            # Overall system health (Sprint 42: persistence removed, now handled by TickStockPL)
            overall_healthy = db_healthy and market_data_healthy

            return jsonify({
                "status": "healthy" if overall_healthy else "unhealthy",
                "components": {
                    "database": "healthy" if db_healthy else "unhealthy",
                    "api": "healthy",
                    "market_data_service": "healthy" if market_data_healthy else "unhealthy"
                },
                "stats": {
                    "market_service": market_service_stats
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        except Exception as e:
            logger.error("Health check failed: %s", str(e))
            return jsonify({
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }), 500

    # User Settings Endpoints
    @app.route('/api/user/settings', methods=['GET'])
    @login_required
    def get_user_settings():
        """Get user settings."""
        try:
            settings = user_settings_service.get_user_settings(current_user.id)
            return jsonify({
                "success": True,
                "settings": settings,
                "user_id": current_user.id
            })
        except Exception as e:
            logger.error("Error getting user settings: %s", str(e))
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/api/user/settings', methods=['POST']) 
    @login_required
    def save_user_settings():
        """Save user settings."""
        try:
            settings_data = request.get_json()
            if not settings_data:
                return jsonify({
                    "success": False,
                    "error": "No settings data provided"
                }), 400

            success = True
            for key, value in settings_data.items():
                if not user_settings_service.set_user_setting(current_user.id, key, value):
                    success = False
                    break
            
            if success:
                return jsonify({
                    "success": True,
                    "message": "Settings saved successfully",
                    "user_id": current_user.id
                })
            else:
                return jsonify({
                    "success": False,
                    "error": "Failed to save settings"
                }), 500
                
        except Exception as e:
            logger.error("Error saving user settings: %s", str(e))
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    # Removed: User Filters endpoints (post-button cleanup)


    # Removed: Universe Management endpoints (post-button cleanup)

    # Sprint 12 Dashboard API Endpoints
    @app.route('/api/symbols/search', methods=['GET'])
    @login_required
    def api_symbols_search():
        """Get available symbols for dropdown/search with optional query filtering."""
        try:
            # Get optional search query parameter
            query = request.args.get('query', '').strip().upper()
            
            # Get all symbols from TickStock database
            symbols = tickstock_db.get_symbols_for_dropdown()
            
            # Filter by query if provided
            if query:
                filtered_symbols = []
                for symbol in symbols:
                    if (query in symbol['symbol'] or 
                        query in symbol.get('name', '').upper()):
                        filtered_symbols.append({
                            'symbol': symbol['symbol'],
                            'name': symbol['name']
                        })
                symbols = filtered_symbols
            else:
                # Return simplified format for dropdown
                symbols = [{
                    'symbol': s['symbol'],
                    'name': s['name']
                } for s in symbols]
            
            # Limit results to reasonable number for UI performance
            symbols = symbols[:100]
            
            return jsonify({
                "success": True,
                "symbols": symbols
            })
            
        except Exception as e:
            logger.error("Error searching symbols: %s", str(e))
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/api/watchlist', methods=['GET'])
    @login_required
    def api_get_watchlist():
        """Get user's watchlist symbols with current prices."""
        try:
            # Get watchlist from user settings
            settings = user_settings_service.get_user_settings(current_user.id)
            watchlist_symbols = settings.get('watchlist', [])
            
            # If watchlist is empty, return empty list
            if not watchlist_symbols:
                return jsonify({
                    "success": True,
                    "symbols": []
                })
            
            # Get symbol details for watchlist items
            watchlist_data = []
            for symbol_code in watchlist_symbols:
                # Get basic symbol info from TickStock DB
                symbol_details = tickstock_db.get_symbol_details(symbol_code)
                if symbol_details:
                    watchlist_data.append({
                        'symbol': symbol_details['symbol'],
                        'name': symbol_details['name'] or '',
                        'last_price': 0.00  # Mock price for now - will integrate with TickStockPL later
                    })
                else:
                    # Symbol not found in database, still include it
                    watchlist_data.append({
                        'symbol': symbol_code,
                        'name': 'Unknown',
                        'last_price': 0.00
                    })
            
            return jsonify({
                "success": True,
                "symbols": watchlist_data
            })
            
        except Exception as e:
            logger.error("Error getting watchlist: %s", str(e))
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/api/watchlist/add', methods=['POST'])
    @login_required
    def api_add_to_watchlist():
        """Add symbol to user's watchlist."""
        try:
            data = request.get_json()
            if not data or 'symbol' not in data:
                return jsonify({
                    "success": False,
                    "error": "Symbol is required"
                }), 400
                
            symbol = data['symbol'].strip().upper()
            
            # Validate symbol exists in database
            symbol_details = tickstock_db.get_symbol_details(symbol)
            if not symbol_details:
                return jsonify({
                    "success": False,
                    "error": f"Symbol {symbol} not found"
                }), 404
            
            # Get current watchlist
            settings = user_settings_service.get_user_settings(current_user.id)
            watchlist = settings.get('watchlist', [])
            
            # Add symbol if not already present
            if symbol not in watchlist:
                watchlist.append(symbol)
                
                # Update watchlist setting
                success = user_settings_service.set_user_setting(
                    current_user.id, 
                    'watchlist',
                    watchlist
                )
                
                if success:
                    return jsonify({
                        "success": True,
                        "message": f"Added {symbol} to watchlist"
                    })
                else:
                    return jsonify({
                        "success": False,
                        "error": "Failed to save watchlist"
                    }), 500
            else:
                return jsonify({
                    "success": True,
                    "message": f"{symbol} is already in watchlist"
                })
                
        except Exception as e:
            logger.error("Error adding to watchlist: %s", str(e))
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/api/watchlist/remove', methods=['POST'])
    @login_required
    def api_remove_from_watchlist():
        """Remove symbol from user's watchlist."""
        try:
            data = request.get_json()
            if not data or 'symbol' not in data:
                return jsonify({
                    "success": False,
                    "error": "Symbol is required"
                }), 400
                
            symbol = data['symbol'].strip().upper()
            
            # Get current watchlist
            settings = user_settings_service.get_user_settings(current_user.id)
            watchlist = settings.get('watchlist', [])
            
            # Remove symbol if present
            if symbol in watchlist:
                watchlist.remove(symbol)
                
                # Update watchlist setting
                success = user_settings_service.set_user_setting(
                    current_user.id, 
                    'watchlist',
                    watchlist
                )
                
                if success:
                    return jsonify({
                        "success": True,
                        "message": f"Removed {symbol} from watchlist"
                    })
                else:
                    return jsonify({
                        "success": False,
                        "error": "Failed to save watchlist"
                    }), 500
            else:
                return jsonify({
                    "success": True,
                    "message": f"{symbol} was not in watchlist"
                })
                
        except Exception as e:
            logger.error("Error removing from watchlist: %s", str(e))
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/api/chart-data/<symbol>', methods=['GET'])
    @login_required
    def api_get_chart_data(symbol):
        """Get OHLCV chart data for a specific symbol."""
        try:
            # Get optional timeframe parameter
            timeframe = request.args.get('timeframe', '1d')
            
            # Validate symbol exists
            symbol = symbol.upper()
            symbol_details = tickstock_db.get_symbol_details(symbol)
            if not symbol_details:
                return jsonify({
                    "success": False,
                    "error": f"Symbol {symbol} not found"
                }), 404
            
            # Phase 2: For now, use enhanced mock data (TickStockPL integration ready)
            # TODO: Replace with real TickStockPL integration when service is available
            try:
                # Check if TickStockPL service is available
                # For now, always use enhanced mock data
                chart_data = generate_realistic_mock_data(symbol, timeframe)
                logger.info("Using enhanced mock data for %s (%s): %d bars", 
                          symbol, timeframe, len(chart_data))
                    
            except Exception as error:
                logger.error("Error generating chart data for %s: %s", symbol, error)
                return jsonify({
                    "success": False,
                    "error": f"Failed to generate chart data for {symbol}"
                }), 500
            
            return jsonify({
                "success": True,
                "chart_data": chart_data,
                "symbol": symbol,
                "timeframe": timeframe
            })
            
        except Exception as e:
            logger.error("Error getting chart data for %s: %s", symbol, str(e))
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    # TickStockPL Integration - Pattern Alerts API Endpoints
    @app.route('/api/tickstockpl/alerts/subscriptions', methods=['GET'])
    @login_required
    def get_pattern_subscriptions():
        """Get user pattern subscriptions."""
        try:
            # For now, return empty subscriptions - this will be connected to Redis later
            return jsonify({
                "success": True,
                "subscriptions": []
            })
        except Exception as e:
            logger.error("Error getting pattern subscriptions: %s", str(e))
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/api/tickstockpl/alerts/preferences', methods=['GET'])
    @login_required
    def get_pattern_preferences():
        """Get user pattern alert preferences."""
        try:
            # Default preferences for now
            return jsonify({
                "success": True,
                "preferences": {
                    "notifications_enabled": True,
                    "email_alerts": False,
                    "sound_alerts": True,
                    "min_confidence": 0.7
                }
            })
        except Exception as e:
            logger.error("Error getting pattern preferences: %s", str(e))
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/api/tickstockpl/alerts/preferences', methods=['POST', 'PUT'])
    @login_required
    def save_pattern_preferences():
        """Save user pattern alert preferences."""
        try:
            preferences_data = request.get_json()
            if not preferences_data:
                return jsonify({
                    "success": False,
                    "error": "No preferences data provided"
                }), 400

            # For now, just acknowledge the save - will implement Redis storage later
            return jsonify({
                "success": True,
                "message": "Preferences saved successfully"
            })
        except Exception as e:
            logger.error("Error saving pattern preferences: %s", str(e))
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/api/tickstockpl/alerts/performance', methods=['GET'])
    @login_required
    def get_pattern_performance():
        """Get pattern performance data."""
        try:
            timeframe = request.args.get('timeframe', '1d')
            
            # Mock performance data for now - JavaScript expects 'performance' array
            return jsonify({
                "success": True,
                "performance": []  # Empty for now, will be populated with TickStockPL integration
            })
        except Exception as e:
            logger.error("Error getting pattern performance: %s", str(e))
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/api/tickstockpl/alerts/history', methods=['GET'])
    @login_required
    def get_pattern_history():
        """Get pattern alert history."""
        try:
            limit = int(request.args.get('limit', 50))
            offset = int(request.args.get('offset', 0))
            
            # Mock history data for now
            return jsonify({
                "success": True,
                "alerts": [],  # JavaScript expects 'alerts', not 'history'
                "total": 0,
                "limit": limit,
                "offset": offset
            })
        except Exception as e:
            logger.error("Error getting pattern history: %s", str(e))
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/api/tickstockpl/alerts/subscribe', methods=['POST'])
    @login_required
    def subscribe_to_patterns():
        """Subscribe to pattern alerts."""
        try:
            subscription_data = request.get_json()
            if not subscription_data:
                return jsonify({
                    "success": False,
                    "error": "No subscription data provided"
                }), 400

            # For now, just acknowledge the subscription - will implement Redis later
            return jsonify({
                "success": True,
                "message": "Subscribed successfully"
            })
        except Exception as e:
            logger.error("Error subscribing to patterns: %s", str(e))
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/api/tickstockpl/alerts/subscribe/<pattern_name>', methods=['PUT'])
    @login_required
    def update_pattern_subscription(pattern_name):
        """Update a pattern subscription (toggle active state)."""
        try:
            update_data = request.get_json()
            if not update_data:
                return jsonify({
                    "success": False,
                    "error": "No update data provided"
                }), 400

            # For now, just acknowledge the update - will implement Redis later
            return jsonify({
                "success": True,
                "message": f"Pattern {pattern_name} updated successfully"
            })
        except Exception as e:
            logger.error("Error updating pattern subscription %s: %s", pattern_name, str(e))
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/api/tickstockpl/alerts/subscribe/<pattern_name>', methods=['DELETE'])
    @login_required
    def unsubscribe_from_pattern(pattern_name):
        """Unsubscribe from a specific pattern."""
        try:
            # For now, just acknowledge the unsubscription - will implement Redis later
            return jsonify({
                "success": True,
                "message": f"Unsubscribed from {pattern_name}"
            })
        except Exception as e:
            logger.error("Error unsubscribing from pattern %s: %s", pattern_name, str(e))
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    # TickStockPL Integration - Backtest API Endpoints
    @app.route('/api/tickstockpl/backtest/config', methods=['GET'])
    @login_required
    def get_backtest_config():
        """Get backtest configuration options."""
        try:
            # Mock configuration data for now
            return jsonify({
                "success": True,
                "symbols": ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "NFLX"],
                "patterns": ["bullish_engulfing", "bearish_engulfing", "hammer", "doji", "morning_star", "evening_star"]
            })
        except Exception as e:
            logger.error("Error getting backtest config: %s", str(e))
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/api/tickstockpl/backtest/submit', methods=['POST'])
    @login_required
    def submit_backtest():
        """Submit a new backtest job."""
        try:
            backtest_data = request.get_json()
            if not backtest_data:
                return jsonify({
                    "success": False,
                    "error": "No backtest data provided"
                }), 400

            # For now, just acknowledge the submission - will implement TickStockPL integration later
            return jsonify({
                "success": True,
                "message": "Backtest submitted successfully",
                "job_id": "mock_job_123"
            })
        except Exception as e:
            logger.error("Error submitting backtest: %s", str(e))
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/api/tickstockpl/backtest/jobs', methods=['GET'])
    @login_required
    def get_backtest_jobs():
        """Get user's backtest jobs."""
        try:
            # Mock job data for now
            return jsonify({
                "success": True,
                "jobs": []  # Empty for now, will be populated with TickStockPL integration
            })
        except Exception as e:
            logger.error("Error getting backtest jobs: %s", str(e))
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/api/tickstockpl/backtest/job/<job_id>', methods=['GET'])
    @login_required
    def get_backtest_job(job_id):
        """Get specific backtest job details."""
        try:
            # Mock job data for now
            return jsonify({
                "success": True,
                "job": {
                    "job_id": job_id,
                    "status": "completed",
                    "results": None  # No results for mock data
                }
            })
        except Exception as e:
            logger.error("Error getting backtest job %s: %s", job_id, str(e))
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/api/tickstockpl/backtest/job/<job_id>/cancel', methods=['POST'])
    @login_required
    def cancel_backtest_job(job_id):
        """Cancel a running backtest job."""
        try:
            # For now, just acknowledge the cancellation - will implement TickStockPL integration later
            return jsonify({
                "success": True,
                "message": f"Backtest job {job_id} cancelled"
            })
        except Exception as e:
            logger.error("Error cancelling backtest job %s: %s", job_id, str(e))
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    # Market Movers API Endpoint - TickStockApp Consumer Pattern
    @app.route('/api/market-movers', methods=['GET'])
    @login_required
    def api_get_market_movers():
        """
        Get market movers data following TickStockApp consumer pattern.
        
        Consumer Pattern Implementation:
        1. Check cache for existing market movers data
        2. If cache miss or stale data, return cached data but trigger TickStockPL refresh job via Redis
        3. TickStockPL will process and publish updated data back via Redis events
        4. Real-time updates delivered to frontend via WebSocket
        
        Performance Target: <50ms query response time
        """
        try:
            start_time = datetime.now(timezone.utc)
            
            # Phase 1: Mock implementation with consumer-ready structure
            # TODO Sprint 10 Phase 2: Replace with Redis cache lookup and TickStockPL job triggering
            
            # Generate realistic mock market movers data
            mock_market_movers = generate_market_movers_mock_data()
            
            # Track performance
            processing_time_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            if processing_time_ms > 50:
                logger.warning("Market movers query exceeded target: %.2fms", processing_time_ms)
            
            logger.debug("Market movers API: %d gainers, %d losers - %.2fms", 
                        len(mock_market_movers.get('gainers', [])),
                        len(mock_market_movers.get('losers', [])),
                        processing_time_ms)
            
            return jsonify({
                "success": True,
                "data": mock_market_movers,
                "cache_status": "mock",  # Will be "hit", "miss", or "stale" in Phase 2
                "last_updated": datetime.now(timezone.utc).isoformat() + "Z",
                "processing_time_ms": round(processing_time_ms, 2),
                "data_source": "mock"  # Will be "cache" or "realtime" in Phase 2
            })
            
        except Exception as e:
            logger.error("Error getting market movers: %s", str(e))
            return jsonify({
                "success": False,
                "error": str(e),
                "data": {"gainers": [], "losers": []},  # Empty data for graceful degradation
                "cache_status": "error"
            }), 500

def generate_market_movers_mock_data():
    """
    Generate realistic mock market movers data.
    
    Returns market movers in the format expected by frontend:
    - Top 10 gainers and losers
    - Realistic price movements and volume data
    - Consistent with existing symbols in database
    """
    import random
    from datetime import datetime, timezone
    
    # Common stock symbols with realistic base prices
    symbols_data = [
        {"symbol": "AAPL", "name": "Apple Inc.", "base_price": 150.00},
        {"symbol": "GOOGL", "name": "Alphabet Inc.", "base_price": 2500.00},
        {"symbol": "MSFT", "name": "Microsoft Corporation", "base_price": 300.00},
        {"symbol": "TSLA", "name": "Tesla Inc.", "base_price": 200.00},
        {"symbol": "AMZN", "name": "Amazon.com Inc.", "base_price": 3000.00},
        {"symbol": "NVDA", "name": "NVIDIA Corporation", "base_price": 400.00},
        {"symbol": "META", "name": "Meta Platforms Inc.", "base_price": 250.00},
        {"symbol": "NFLX", "name": "Netflix Inc.", "base_price": 400.00},
        {"symbol": "AMD", "name": "Advanced Micro Devices", "base_price": 80.00},
        {"symbol": "INTC", "name": "Intel Corporation", "base_price": 45.00},
        {"symbol": "CRM", "name": "Salesforce Inc.", "base_price": 180.00},
        {"symbol": "ADBE", "name": "Adobe Inc.", "base_price": 350.00},
        {"symbol": "PYPL", "name": "PayPal Holdings Inc.", "base_price": 90.00},
        {"symbol": "UBER", "name": "Uber Technologies Inc.", "base_price": 55.00},
        {"symbol": "SPOT", "name": "Spotify Technology SA", "base_price": 120.00},
        {"symbol": "ZM", "name": "Zoom Video Communications", "base_price": 75.00},
        {"symbol": "SQ", "name": "Block Inc.", "base_price": 65.00},
        {"symbol": "ROKU", "name": "Roku Inc.", "base_price": 40.00},
        {"symbol": "TWTR", "name": "Twitter Inc.", "base_price": 35.00},
        {"symbol": "SNAP", "name": "Snap Inc.", "base_price": 25.00}
    ]
    
    # Shuffle for randomness
    random.shuffle(symbols_data)
    
    # Generate gainers (positive changes)
    gainers = []
    for i in range(10):
        symbol_data = symbols_data[i]
        base_price = symbol_data["base_price"]
        
        # Generate positive change (1% to 15%)
        change_percent = random.uniform(1.0, 15.0)
        price_change = base_price * (change_percent / 100)
        current_price = base_price + price_change
        
        # Generate realistic volume
        volume = random.randint(100000, 5000000)
        
        gainers.append({
            "symbol": symbol_data["symbol"],
            "name": symbol_data["name"],
            "price": round(current_price, 2),
            "change": round(price_change, 2),
            "change_percent": round(change_percent, 2),
            "volume": volume,
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
        })
    
    # Generate losers (negative changes)
    losers = []
    for i in range(10, 20):  # Next 10 symbols
        symbol_data = symbols_data[i]
        base_price = symbol_data["base_price"]
        
        # Generate negative change (-1% to -12%)
        change_percent = random.uniform(-12.0, -1.0)
        price_change = base_price * (change_percent / 100)
        current_price = base_price + price_change
        
        # Generate realistic volume (often higher for losers)
        volume = random.randint(150000, 6000000)
        
        losers.append({
            "symbol": symbol_data["symbol"],
            "name": symbol_data["name"],
            "price": round(current_price, 2),
            "change": round(price_change, 2),
            "change_percent": round(change_percent, 2),
            "volume": volume,
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
        })
    
    # Sort gainers by change_percent descending, losers by change_percent ascending
    gainers.sort(key=lambda x: x["change_percent"], reverse=True)
    losers.sort(key=lambda x: x["change_percent"])
    
    return {
        "gainers": gainers,
        "losers": losers,
        "market_summary": {
            "total_gainers": len(gainers),
            "total_losers": len(losers),
            "avg_gain_percent": round(sum(g["change_percent"] for g in gainers) / len(gainers), 2),
            "avg_loss_percent": round(sum(l["change_percent"] for l in losers) / len(losers), 2),
            "total_volume": sum(s["volume"] for s in gainers + losers),
            "last_updated": datetime.now(timezone.utc).isoformat() + "Z"
        }
    }

