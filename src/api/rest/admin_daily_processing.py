"""
Admin Daily Processing Dashboard Routes
Sprint 33 - Phase 4 Integration with TickStockPL HTTP API
Manages daily processing schedules, status monitoring, and manual triggers using HTTP API client
"""

import os
import json
import redis
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from src.utils.auth_decorators import admin_required
from src.core.services.config_manager import get_config
from src.core.services.processing_event_subscriber import get_processing_subscriber
from src.core.services.tickstockpl_api_client import get_tickstockpl_client

logger = logging.getLogger(__name__)

def get_processing_redis():
    """Get Redis client for processing channels"""
    config = get_config()
    return redis.Redis(
        host=config.get('REDIS_HOST', 'localhost'),
        port=int(config.get('REDIS_PORT', 6379)),
        db=int(config.get('REDIS_DB', 0)),
        decode_responses=True
    )

def register_admin_daily_processing_routes(app):
    """Register admin daily processing dashboard routes with the Flask app"""

    redis_client = get_processing_redis()

    # Initialize services: Redis event subscriber + HTTP API client
    event_subscriber = get_processing_subscriber(redis_client, app.extensions.get('socketio'))
    api_client = get_tickstockpl_client()

    # Schedule data (only local config, processing status comes from subscriber)
    schedule_config = {
        'enabled': True,
        'trigger_time': '21:10',
        'market_check': True,
        'next_run': None
    }

    # Integration: Redis event subscriber for real-time updates + HTTP API client for commands

    @app.route('/admin/daily-processing')
    @login_required
    @admin_required
    def admin_daily_processing_dashboard():
        """Main dashboard for daily processing management"""
        try:
            # Test Redis connection
            try:
                redis_client.ping()
                redis_connected = True
            except redis.ConnectionError:
                redis_connected = False

            # Get latest status from TickStockPL API with Redis fallback
            api_status = api_client.get_status()
            if api_status['success']:
                status = api_status
            else:
                # Fallback to Redis subscriber status
                status = event_subscriber.get_current_status()

            # Get schedule from API
            schedule_result = api_client.get_schedule()
            if schedule_result['success']:
                schedule = {
                    'enabled': schedule_result['enabled'],
                    'trigger_time': schedule_result['trigger_time'],
                    'market_check': schedule_result['market_check'],
                    'next_run': schedule_result.get('next_run')
                }
            else:
                schedule = schedule_config

            # Get history from TickStockPL API
            history_result = api_client.get_history(days=7)
            if history_result['success']:
                history = history_result['history'][:10]  # Limit to 10 items
            else:
                # Fallback to Redis subscriber history
                history = event_subscriber.get_processing_history(days=7, limit=10)

            return render_template('admin/daily_processing_dashboard.html',
                                 redis_connected=redis_connected,
                                 processing_status=status,
                                 schedule=schedule,
                                 history=history,
                                 processing_channels=[
                                     'tickstock:processing:status',
                                     'tickstock:processing:schedule'
                                 ])
        except Exception as e:
            logger.error(f"Error loading daily processing dashboard: {str(e)}")
            flash(f'Error loading dashboard: {str(e)}', 'danger')
            return render_template('admin/daily_processing_dashboard.html',
                                 redis_connected=False,
                                 processing_status={},
                                 schedule={},
                                 history=[])

    @app.route('/api/processing/daily/status')
    @login_required
    def get_processing_status():
        """Get current processing status"""
        try:
            # Get status from TickStockPL API with Redis fallback
            api_status = api_client.get_status()
            if api_status['success']:
                status = api_status
            else:
                # Fallback to Redis subscriber status
                status = event_subscriber.get_current_status()

            return jsonify({
                'success': True,
                'status': status
            })
        except Exception as e:
            logger.error(f"Error fetching processing status: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/processing/daily/trigger', methods=['POST'])
    @login_required
    @admin_required
    def trigger_manual_processing():
        """Manually trigger daily processing run"""
        try:
            data = request.json or {}
            skip_market_check = data.get('skip_market_check', False)
            phases = data.get('phases', None)  # Allow phase selection

            # Check if processing is already running via API with Redis fallback
            api_status = api_client.get_status()
            if api_status['success']:
                current_status = api_status
            else:
                current_status = event_subscriber.get_current_status()

            if current_status.get('is_running', False):
                return jsonify({
                    'success': False,
                    'message': 'Processing is already running'
                }), 400

            # Use HTTP API client to trigger processing in TickStockPL
            result = api_client.trigger_processing(
                skip_market_check=skip_market_check,
                phases=phases
            )

            if result['success']:
                return jsonify({
                    'success': True,
                    'message': result['message'],
                    'run_id': result['run_id'],
                    'status': 'triggered'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': result['message']
                }), 400

        except Exception as e:
            logger.error(f"Error triggering processing: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/processing/daily/history')
    @login_required
    def get_processing_history():
        """Get processing run history"""
        try:
            days = int(request.args.get('days', 7))
            limit = int(request.args.get('limit', 20))

            # Get history from TickStockPL API with Redis fallback
            history_result = api_client.get_history(days=days)
            if history_result['success']:
                history = history_result['history'][:limit]  # Apply limit
            else:
                # Fallback to Redis subscriber history
                history = event_subscriber.get_processing_history(days=days, limit=limit)

            return jsonify({
                'success': True,
                'history': history
            })

        except Exception as e:
            logger.error(f"Error fetching history: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/processing/market/status')
    @login_required
    def get_market_status():
        """Get current market status"""
        try:
            # This would normally check actual market status
            # For now, return mock data
            now = datetime.now()
            is_weekday = now.weekday() < 5

            # Market hours: 9:30 AM - 4:00 PM ET
            market_open = now.replace(hour=9, minute=30, second=0)
            market_close = now.replace(hour=16, minute=0, second=0)
            is_market_hours = market_open <= now <= market_close

            return jsonify({
                'success': True,
                'market_status': {
                    'is_open': is_weekday and is_market_hours,
                    'is_weekday': is_weekday,
                    'current_time': now.strftime('%I:%M %p ET'),
                    'next_open': market_open.strftime('%I:%M %p ET') if not is_market_hours else None,
                    'next_close': market_close.strftime('%I:%M %p ET') if is_market_hours else None
                }
            })

        except Exception as e:
            logger.error(f"Error fetching market status: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/processing/daily/schedule', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def manage_schedule():
        """Get or update processing schedule"""
        try:
            if request.method == 'GET':
                # Get schedule from TickStockPL API
                result = api_client.get_schedule()
                if result['success']:
                    return jsonify({
                        'success': True,
                        'schedule': {
                            'enabled': result['enabled'],
                            'trigger_time': result['trigger_time'],
                            'market_check': result['market_check'],
                            'next_run': result.get('next_run')
                        }
                    })
                else:
                    # Fallback to local config if API unavailable
                    return jsonify({
                        'success': True,
                        'schedule': schedule_config
                    })

            else:  # POST
                data = request.json or {}

                # Update schedule via HTTP API client
                result = api_client.update_schedule(
                    enabled=data.get('enabled'),
                    trigger_time=data.get('trigger_time'),
                    market_check=data.get('market_check'),
                    universes=data.get('universes')
                )

                if result['success']:
                    # Update local config to match API
                    if 'enabled' in data:
                        schedule_config['enabled'] = data['enabled']
                    if 'trigger_time' in data:
                        schedule_config['trigger_time'] = data['trigger_time']
                    if 'market_check' in data:
                        schedule_config['market_check'] = data['market_check']

                return jsonify({
                    'success': result['success'],
                    'message': result['message'],
                    'schedule': result.get('schedule', schedule_config)
                })

        except Exception as e:
            logger.error(f"Error managing schedule: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/processing/daily/cancel', methods=['POST'])
    @login_required
    @admin_required
    def cancel_processing():
        """Cancel current processing run"""
        try:
            # Check if processing is running via API with Redis fallback
            api_status = api_client.get_status()
            if api_status['success']:
                current_status = api_status
            else:
                current_status = event_subscriber.get_current_status()

            if not current_status.get('is_running', False):
                return jsonify({
                    'success': False,
                    'message': 'No processing is currently running'
                }), 400

            # Use HTTP API client to cancel processing in TickStockPL
            result = api_client.cancel_processing()

            return jsonify({
                'success': result['success'],
                'message': result['message']
            })

        except Exception as e:
            logger.error(f"Error cancelling processing: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    # Phase 2 endpoints for data import management
    @app.route('/api/processing/import/trigger', methods=['POST'])
    @login_required
    @admin_required
    def trigger_import():
        """Trigger manual data import (Phase 2)"""
        try:
            data = request.json or {}

            # Use HTTP API client to trigger data import in TickStockPL
            result = api_client.trigger_data_import(
                universes=data.get('universes', ['sp500']),
                timeframes=data.get('timeframes', ['daily', 'weekly']),
                lookback_days=data.get('lookback_days', 30)
            )

            if result['success']:
                return jsonify({
                    'success': True,
                    'message': result['message'],
                    'run_id': result['run_id'],
                    'estimated_duration_minutes': 35
                })
            else:
                return jsonify({
                    'success': False,
                    'message': result['message']
                }), 400

        except Exception as e:
            logger.error(f"Error triggering import: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/processing/import/retry', methods=['POST'])
    @login_required
    @admin_required
    def retry_failed_imports():
        """Retry failed symbol imports (Phase 2)"""
        try:
            data = request.json or {}
            original_run_id = data.get('run_id')
            symbols = data.get('symbols')

            if not original_run_id:
                # Try to get from current status via API with Redis fallback
                api_status = api_client.get_status()
                if api_status['success']:
                    current_status = api_status
                else:
                    current_status = event_subscriber.get_current_status()
                original_run_id = current_status.get('run_id')

            if not original_run_id:
                return jsonify({
                    'success': False,
                    'message': 'No run ID specified for retry'
                }), 400

            # Use HTTP API client to retry failed imports in TickStockPL
            result = api_client.retry_failed_imports(
                run_id=original_run_id,
                symbols=symbols
            )

            if result['success']:
                symbol_count = len(symbols) if symbols else 0
                return jsonify({
                    'success': True,
                    'retry_count': symbol_count,
                    'run_id': result['run_id'],
                    'message': result['message']
                })
            else:
                return jsonify({
                    'success': False,
                    'message': result['message']
                }), 400

        except Exception as e:
            logger.error(f"Error retrying imports: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    # No longer needed - ProcessingEventSubscriber handles event storage automatically

    @app.route('/api/processing/indicators/latest/<symbol>')
    @login_required
    def get_latest_indicators(symbol: str):
        """Get latest calculated indicators for a symbol"""
        try:
            from sqlalchemy import create_engine, text

            # Database connection - use DATABASE_URI from config_manager
            config = get_config()
            db_url = config.get('DATABASE_URI', 'postgresql://app_readwrite:password@localhost:5432/tickstock')
            engine = create_engine(db_url)

            # Query latest indicators for symbol
            query = text("""
                SELECT DISTINCT ON (indicator_type)
                    indicator_type,
                    timeframe,
                    value_data,
                    metadata,
                    calculation_timestamp
                FROM daily_indicators
                WHERE symbol = :symbol
                AND calculation_timestamp >= CURRENT_DATE
                ORDER BY indicator_type, calculation_timestamp DESC
            """)

            with engine.connect() as conn:
                result = conn.execute(query, {"symbol": symbol.upper()})
                rows = result.fetchall()

            indicators = {}
            for row in rows:
                indicators[row.indicator_type] = {
                    'values': row.value_data,
                    'metadata': row.metadata,
                    'timeframe': row.timeframe,
                    'calculated_at': row.calculation_timestamp.isoformat() if row.calculation_timestamp else None
                }

            return jsonify({
                'success': True,
                'symbol': symbol.upper(),
                'indicators': indicators,
                'count': len(indicators)
            })

        except Exception as e:
            logger.error(f"Error fetching indicators for {symbol}: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/processing/indicators/stats')
    @login_required
    def get_indicator_stats():
        """Get indicator processing statistics"""
        try:
            from sqlalchemy import create_engine, text

            # Database connection - use DATABASE_URI from config_manager
            config = get_config()
            db_url = config.get('DATABASE_URI', 'postgresql://app_readwrite:password@localhost:5432/tickstock')
            engine = create_engine(db_url)

            # Get today's indicator statistics
            query = text("""
                SELECT
                    indicator_type,
                    COUNT(DISTINCT symbol) as symbol_count,
                    COUNT(*) as total_calculations,
                    MAX(calculation_timestamp) as last_calculated
                FROM daily_indicators
                WHERE calculation_timestamp >= CURRENT_DATE
                GROUP BY indicator_type
                ORDER BY indicator_type
            """)

            with engine.connect() as conn:
                result = conn.execute(query)
                rows = result.fetchall()

            stats = []
            total_calculations = 0
            unique_symbols = set()

            for row in rows:
                stats.append({
                    'indicator': row.indicator_type,
                    'symbol_count': row.symbol_count,
                    'calculations': row.total_calculations,
                    'last_calculated': row.last_calculated.isoformat() if row.last_calculated else None
                })
                total_calculations += row.total_calculations

            # Get unique symbol count
            symbol_query = text("""
                SELECT COUNT(DISTINCT symbol) as unique_symbols
                FROM daily_indicators
                WHERE calculation_timestamp >= CURRENT_DATE
            """)

            with engine.connect() as conn:
                result = conn.execute(symbol_query)
                row = result.fetchone()
                unique_symbols_count = row.unique_symbols if row else 0

            return jsonify({
                'success': True,
                'stats': stats,
                'summary': {
                    'total_indicators': len(stats),
                    'total_calculations': total_calculations,
                    'unique_symbols': unique_symbols_count
                },
                'current_status': event_subscriber.get_current_status().get('indicator_status', {})
            })

        except Exception as e:
            logger.error(f"Error fetching indicator stats: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/processing/indicators/trigger', methods=['POST'])
    @login_required
    @admin_required
    def trigger_indicator_processing():
        """Trigger manual indicator processing"""
        try:
            data = request.json or {}

            # Use HTTP API client to trigger indicator processing in TickStockPL
            result = api_client.trigger_indicator_processing(
                symbols=data.get('symbols', None),  # None = all symbols
                indicators=data.get('indicators', None),  # None = all indicators
                timeframe=data.get('timeframe', 'daily')
            )

            if result['success']:
                return jsonify({
                    'success': True,
                    'message': result['message'],
                    'run_id': result['run_id'],
                    'estimated_duration_minutes': 15
                })
            else:
                return jsonify({
                    'success': False,
                    'message': result['message']
                }), 400

        except Exception as e:
            logger.error(f"Error triggering indicator processing: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    return app