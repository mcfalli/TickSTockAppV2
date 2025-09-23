"""
Admin Historical Data Management Routes - Redis Job Queue Version
Provides web interface for managing historical data loads via TickStockPL.

This version submits jobs to TickStockPL via Redis instead of direct loading.

Features:
- Submit historical data load jobs to TickStockPL
- Monitor job progress via Redis status updates
- View job history
- Manage data quality and cleanup
"""

import os
import json
import uuid
import redis
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from src.utils.auth_decorators import admin_required

# Initialize Redis client
def get_redis_client():
    """Get Redis client instance"""
    return redis.Redis(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        db=int(os.getenv('REDIS_DB', 0)),
        decode_responses=True
    )

def register_admin_historical_routes(app):
    """Register admin historical data routes with the Flask app"""

    # In-memory storage for job tracking (consider using database for persistence)
    job_history = []
    redis_client = get_redis_client()

    @app.route('/admin/historical-data')
    @login_required
    @admin_required
    def admin_historical_dashboard():
        """Main admin dashboard for historical data management"""
        try:
            # Get recent jobs from Redis
            recent_jobs = []
            for job in job_history[-10:]:  # Last 10 jobs
                job_id = job.get('job_id')
                if job_id:
                    status_data = redis_client.get(f'job:status:{job_id}')
                    if status_data:
                        status = json.loads(status_data)
                        job['current_status'] = status
                recent_jobs.append(job)

            # Get available symbols (simplified - you may want to query database)
            available_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'SPY', 'QQQ', 'DIA']

            # Get available universes
            available_universes = {
                'SP500': 'S&P 500 Components',
                'NASDAQ100': 'NASDAQ 100 Components',
                'ETF': 'Major ETFs',
                'CUSTOM': 'Custom Symbol List'
            }

            # Add empty summaries that template expects
            daily_summary = {}
            minute_summary = {}

            return render_template('admin/historical_data_dashboard.html',
                                 symbols=available_symbols,
                                 available_universes=available_universes,
                                 recent_jobs=recent_jobs,
                                 daily_summary=daily_summary,
                                 minute_summary=minute_summary)
        except Exception as e:
            app.logger.error(f"Error loading historical data dashboard: {str(e)}")
            flash(f'Error loading dashboard: {str(e)}', 'danger')
            return render_template('admin/historical_data_dashboard.html',
                                 symbols=[],
                                 available_universes={},
                                 recent_jobs=[],
                                 daily_summary={},
                                 minute_summary={})

    @app.route('/admin/historical-data/trigger-load', methods=['POST'])
    @login_required
    @admin_required
    def admin_trigger_historical_load():
        """Submit a historical data load job to TickStockPL via Redis"""
        try:
            # Test Redis connection
            try:
                redis_client.ping()
            except redis.ConnectionError:
                flash('Redis service unavailable. Please contact administrator.', 'danger')
                return redirect(url_for('admin_historical_dashboard'))

            # Get form data
            load_type = request.form.get('load_type', 'symbols')

            # Prepare job data based on load type
            job_id = str(uuid.uuid4())
            base_job = {
                'job_id': job_id,
                'requested_by': current_user.username if current_user.is_authenticated else 'admin',
                'timestamp': datetime.now().isoformat()
            }

            if load_type == 'symbols':
                # Individual symbols load
                symbols_input = request.form.get('symbols', '').strip()
                if not symbols_input:
                    flash('No symbols provided', 'warning')
                    return redirect(url_for('admin_historical_dashboard'))

                symbols = [s.strip().upper() for s in symbols_input.split(',') if s.strip()]
                years = int(request.form.get('years', 1))
                timespan = request.form.get('timespan', 'day')

                job_data = {
                    **base_job,
                    'job_type': 'historical_load',
                    'symbols': symbols,
                    'years': years,
                    'timespan': timespan
                }

                job_description = f"Loading {len(symbols)} symbols for {years} year(s) ({timespan})"

            elif load_type == 'universe':
                # Universe load
                universe_type = request.form.get('universe_type', 'SP500')
                years = int(request.form.get('universe_years', 1))

                job_data = {
                    **base_job,
                    'job_type': 'universe_seed',
                    'universe_type': universe_type,
                    'years': years
                }

                job_description = f"Loading {universe_type} universe for {years} year(s)"

            elif load_type == 'multi_timeframe':
                # Multi-timeframe load
                symbols_input = request.form.get('multi_symbols', '').strip()
                if not symbols_input:
                    flash('No symbols provided for multi-timeframe load', 'warning')
                    return redirect(url_for('admin_historical_dashboard'))

                symbols = [s.strip().upper() for s in symbols_input.split(',') if s.strip()]
                timeframes = request.form.getlist('timeframes')
                years = int(request.form.get('multi_years', 1))

                if not timeframes:
                    timeframes = ['hour', 'day']  # Default timeframes

                job_data = {
                    **base_job,
                    'job_type': 'multi_timeframe_load',
                    'symbols': symbols,
                    'timeframes': timeframes,
                    'years': years
                }

                job_description = f"Multi-timeframe load for {len(symbols)} symbols ({', '.join(timeframes)})"

            else:
                flash(f'Unknown load type: {load_type}', 'danger')
                return redirect(url_for('admin_historical_dashboard'))

            # Submit job to TickStockPL via Redis
            try:
                redis_client.publish('tickstock.jobs.data_load', json.dumps(job_data))

                # Store initial status
                initial_status = {
                    'status': 'submitted',
                    'progress': 0,
                    'message': 'Job submitted to processing queue',
                    'description': job_description,
                    'submitted_at': datetime.now().isoformat()
                }

                redis_client.setex(
                    f'job:status:{job_id}',
                    7200,  # 2 hour TTL
                    json.dumps(initial_status)
                )

                # Add to job history
                job_history.append({
                    'job_id': job_id,
                    'type': job_data['job_type'],
                    'description': job_description,
                    'submitted_at': datetime.now(),
                    'submitted_by': current_user.username if current_user.is_authenticated else 'admin'
                })

                # Keep only last 100 jobs in memory
                if len(job_history) > 100:
                    job_history.pop(0)

                flash(f'Job submitted successfully! Job ID: {job_id[:8]}...', 'success')
                app.logger.info(f"Submitted job {job_id}: {job_description}")

            except Exception as e:
                app.logger.error(f"Error submitting job to Redis: {str(e)}")
                flash(f'Error submitting job: {str(e)}', 'danger')

            return redirect(url_for('admin_historical_dashboard'))

        except Exception as e:
            app.logger.error(f"Error in trigger_load: {str(e)}")
            flash(f'Error triggering load: {str(e)}', 'danger')
            return redirect(url_for('admin_historical_dashboard'))

    @app.route('/admin/historical-data/job/<job_id>/status')
    @login_required
    def admin_job_status(job_id):
        """Get job status from Redis"""
        try:
            status_data = redis_client.get(f'job:status:{job_id}')

            if status_data:
                status = json.loads(status_data)
                return jsonify({
                    'success': True,
                    'job_id': job_id,
                    **status
                })
            else:
                # Check if job exists in history
                for job in job_history:
                    if job.get('job_id') == job_id:
                        return jsonify({
                            'success': True,
                            'job_id': job_id,
                            'status': 'expired',
                            'message': 'Job status expired from cache',
                            'progress': 100
                        })

                return jsonify({
                    'success': False,
                    'message': 'Job not found'
                }), 404

        except Exception as e:
            app.logger.error(f"Error getting job status: {str(e)}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/admin/historical-data/job/<job_id>/cancel', methods=['POST'])
    @login_required
    @admin_required
    def admin_cancel_job(job_id):
        """Request job cancellation via Redis"""
        try:
            # Publish cancellation request
            cancel_request = {
                'job_id': job_id,
                'action': 'cancel',
                'requested_by': current_user.username if current_user.is_authenticated else 'admin',
                'timestamp': datetime.now().isoformat()
            }

            redis_client.publish('tickstock.jobs.control', json.dumps(cancel_request))

            # Update status to indicate cancellation requested
            status_data = redis_client.get(f'job:status:{job_id}')
            if status_data:
                status = json.loads(status_data)
                status['status'] = 'cancelling'
                status['message'] = 'Cancellation requested'
                redis_client.setex(
                    f'job:status:{job_id}',
                    3600,  # 1 hour TTL
                    json.dumps(status)
                )

            flash(f'Cancellation requested for job {job_id[:8]}...', 'info')
            return jsonify({'success': True, 'message': 'Cancellation requested'})

        except Exception as e:
            app.logger.error(f"Error cancelling job: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/admin/historical-data/bulk-operations', methods=['POST'])
    @login_required
    @admin_required
    def admin_bulk_operations():
        """Submit bulk operations to TickStockPL"""
        try:
            operation = request.form.get('operation')

            if operation == 'refresh_all_etfs':
                job_id = str(uuid.uuid4())
                job_data = {
                    'job_id': job_id,
                    'job_type': 'universe_seed',
                    'universe_type': 'ETF',
                    'years': 1,
                    'refresh': True,
                    'requested_by': current_user.username if current_user.is_authenticated else 'admin',
                    'timestamp': datetime.now().isoformat()
                }

                redis_client.publish('tickstock.jobs.data_load', json.dumps(job_data))
                flash('ETF refresh job submitted', 'success')

            elif operation == 'load_sp500':
                job_id = str(uuid.uuid4())
                job_data = {
                    'job_id': job_id,
                    'job_type': 'universe_seed',
                    'universe_type': 'SP500',
                    'years': 2,
                    'requested_by': current_user.username if current_user.is_authenticated else 'admin',
                    'timestamp': datetime.now().isoformat()
                }

                redis_client.publish('tickstock.jobs.data_load', json.dumps(job_data))
                flash('S&P 500 load job submitted', 'success')

            elif operation == 'load_nasdaq100':
                job_id = str(uuid.uuid4())
                job_data = {
                    'job_id': job_id,
                    'job_type': 'universe_seed',
                    'universe_type': 'NASDAQ100',
                    'years': 2,
                    'requested_by': current_user.username if current_user.is_authenticated else 'admin',
                    'timestamp': datetime.now().isoformat()
                }

                redis_client.publish('tickstock.jobs.data_load', json.dumps(job_data))
                flash('NASDAQ 100 load job submitted', 'success')

            else:
                flash(f'Unknown operation: {operation}', 'danger')

            return redirect(url_for('admin_historical_dashboard'))

        except Exception as e:
            app.logger.error(f"Error in bulk operations: {str(e)}")
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('admin_historical_dashboard'))

    @app.route('/admin/historical-data/test-redis')
    @login_required
    @admin_required
    def test_redis_connection():
        """Test Redis connection and TickStockPL availability"""
        try:
            # Test Redis connection
            redis_client.ping()

            # Check for TickStockPL heartbeat
            heartbeat = redis_client.get('tickstockpl:heartbeat')
            tickstockpl_status = 'Connected' if heartbeat else 'Not detected'

            # Get queue depth
            # Note: This would need to be implemented in TickStockPL
            queue_depth = redis_client.llen('tickstock:job_queue') or 0

            return jsonify({
                'success': True,
                'redis': 'Connected',
                'tickstockpl': tickstockpl_status,
                'queue_depth': queue_depth,
                'timestamp': datetime.now().isoformat()
            })

        except redis.ConnectionError as e:
            return jsonify({
                'success': False,
                'redis': 'Failed',
                'error': str(e)
            }), 503
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    # API endpoints for AJAX/JavaScript integration

    @app.route('/api/admin/historical-data/load', methods=['POST'])
    @login_required
    @admin_required
    def api_load_historical_data():
        """API endpoint for submitting data load jobs"""
        try:
            data = request.json

            # Validate input
            if not data:
                return jsonify({'success': False, 'message': 'No data provided'}), 400

            job_id = str(uuid.uuid4())
            job_data = {
                'job_id': job_id,
                'job_type': data.get('job_type', 'historical_load'),
                'symbols': data.get('symbols', []),
                'years': data.get('years', 1),
                'timespan': data.get('timespan', 'day'),
                'requested_by': current_user.username if current_user.is_authenticated else 'api',
                'timestamp': datetime.now().isoformat()
            }

            # Submit to Redis
            redis_client.publish('tickstock.jobs.data_load', json.dumps(job_data))

            # Store initial status
            redis_client.setex(
                f'job:status:{job_id}',
                3600,
                json.dumps({
                    'status': 'submitted',
                    'progress': 0,
                    'message': 'Job submitted'
                })
            )

            return jsonify({
                'success': True,
                'job_id': job_id,
                'message': f'Job submitted for {len(job_data["symbols"])} symbols'
            })

        except Exception as e:
            app.logger.error(f"API error: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/admin/job-status/<job_id>')
    @login_required
    def api_job_status(job_id):
        """API endpoint for getting job status"""
        try:
            status_data = redis_client.get(f'job:status:{job_id}')

            if status_data:
                status = json.loads(status_data)
                return jsonify({
                    'success': True,
                    'job_id': job_id,
                    **status
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Job not found'
                }), 404

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    return app