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

import json
import uuid
from datetime import datetime

import redis
from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from src.core.services.config_manager import get_config
from src.core.services.tickstockpl_api_client import get_tickstockpl_client
from src.utils.auth_decorators import admin_required


# Initialize Redis client
def get_redis_client():
    """Get Redis client instance"""
    config = get_config()
    return redis.Redis(
        host=config.get('REDIS_HOST', 'localhost'),
        port=config.get('REDIS_PORT', 6379),
        db=config.get('REDIS_DB', 0),
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
                job_with_status = dict(job)  # Make a copy

                # Set default values expected by template
                job_with_status['id'] = job_id if job_id else 'Unknown'
                job_with_status['status'] = 'pending'
                job_with_status['completed_at'] = None
                job_with_status['successful_symbols'] = []
                job_with_status['failed_symbols'] = []

                if job_id:
                    status_data = redis_client.get(f'job:status:{job_id}')
                    if status_data:
                        status = json.loads(status_data)
                        job_with_status['current_status'] = status
                        job_with_status['status'] = status.get('status', 'pending')

                recent_jobs.append(job_with_status)

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

            # Calculate job statistics
            job_stats = {
                'active_jobs': len([j for j in recent_jobs if j.get('current_status', {}).get('status') == 'running']),
                'completed_jobs': len([j for j in recent_jobs if j.get('current_status', {}).get('status') == 'completed']),
                'failed_jobs': len([j for j in recent_jobs if j.get('current_status', {}).get('status') == 'failed']),
                'queued_jobs': len([j for j in recent_jobs if j.get('current_status', {}).get('status') == 'queued'])
            }

            response = app.make_response(render_template('admin/historical_data_dashboard.html',
                                 symbols=available_symbols,
                                 available_universes=available_universes,
                                 recent_jobs=recent_jobs,
                                 daily_summary=daily_summary,
                                 minute_summary=minute_summary,
                                 job_stats=job_stats))
            # Prevent browser caching of job list
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response
        except Exception as e:
            app.logger.error(f"Error loading historical data dashboard: {str(e)}")
            flash(f'Error loading dashboard: {str(e)}', 'danger')
            return render_template('admin/historical_data_dashboard.html',
                                 symbols=[],
                                 available_universes={},
                                 recent_jobs=[],
                                 daily_summary={},
                                 minute_summary={},
                                 job_stats={'active_jobs': 0, 'completed_jobs': 0, 'failed_jobs': 0, 'queued_jobs': 0})

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
                years = float(request.form.get('years', 1.0))
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
                # CSV Universe load - TickStockPL format
                csv_file = request.form.get('csv_file', 'sp_500.csv')
                universe_type = request.form.get('universe_type', 'sp_500')
                years = float(request.form.get('universe_years', 1))
                include_ohlcv = request.form.get('include_ohlcv', 'true').lower() == 'true'

                job_data = {
                    'job_id': job_id,
                    'job_type': 'csv_universe_load',  # TickStockPL expects this
                    'csv_file': csv_file,
                    'universe_type': universe_type,
                    'years': years,
                    'include_ohlcv': include_ohlcv,
                    'requested_by': current_user.username if current_user.is_authenticated else 'admin'
                }

                job_description = f"Loading {universe_type} universe from {csv_file} ({years} year(s), OHLCV: {include_ohlcv})"

            elif load_type == 'multi_timeframe':
                # Multi-timeframe load
                symbols_input = request.form.get('multi_symbols', '').strip()
                if not symbols_input:
                    flash('No symbols provided for multi-timeframe load', 'warning')
                    return redirect(url_for('admin_historical_dashboard'))

                symbols = [s.strip().upper() for s in symbols_input.split(',') if s.strip()]
                timeframes = request.form.getlist('timeframes')
                years = float(request.form.get('multi_years', 1.0))

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

                # Store initial status (using hash format for consistency)
                initial_status = {
                    'status': 'submitted',
                    'progress': '0',
                    'message': 'Job submitted to processing queue',
                    'description': job_description,
                    'submitted_at': datetime.now().isoformat()
                }

                job_key = f'tickstock.jobs.status:{job_id}'
                redis_client.hset(job_key, mapping=initial_status)
                redis_client.expire(job_key, 86400)  # 24 hour TTL

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

    @app.route('/admin/historical-data/universes', methods=['GET'])
    @login_required
    @admin_required
    def admin_get_universes():
        """
        Get available universes from RelationshipCache.

        Sprint 62: Dynamic universe dropdown population.

        Query Parameters:
            types: Comma-separated list of types to filter (default: 'UNIVERSE,ETF')

        Returns:
            JSON: {
                'universes': [...],
                'total_count': int,
                'types': [...]
            }
        """
        try:
            from src.core.services.relationship_cache import get_relationship_cache

            cache = get_relationship_cache()

            # Get universe types filter from query params
            types_param = request.args.get('types', 'UNIVERSE,ETF')
            types = [t.strip() for t in types_param.split(',') if t.strip()]

            # Get universes with metadata
            universes = cache.get_available_universes(types=types)

            # Format for frontend
            response = {
                'universes': universes,
                'total_count': len(universes),
                'types': types
            }

            app.logger.info(f"Fetched {len(universes)} universes (types: {types})")
            return jsonify(response), 200

        except Exception as e:
            app.logger.error(f"Error fetching universes: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/admin/historical-data/trigger-universe-load', methods=['POST'])
    @login_required
    @admin_required
    def admin_trigger_universe_load():
        """
        Submit historical data load job for universe(s).

        Sprint 62: Universe-based historical data loading.

        Request Body:
        {
            "universe_key": "SPY:nasdaq100",  // Single or multi-universe join
            "timeframes": ["1min", "hour", "day", "week", "month"],
            "years": 2
        }

        Returns:
            JSON: {
                'job_id': str,
                'symbol_count': int,
                'universe_key': str,
                'message': str
            }
        """
        try:
            from src.core.services.relationship_cache import get_relationship_cache

            # Get request data
            data = request.get_json()
            if not data:
                return jsonify({'error': 'Request body required'}), 400

            universe_key = data.get('universe_key', '').strip()
            timeframes = data.get('timeframes', ['day'])
            years = float(data.get('years', 1.0))
            run_analysis = data.get('run_analysis_after_import', False)  # Sprint 75 Phase 2

            if not universe_key:
                return jsonify({'error': 'universe_key required'}), 400

            if not timeframes or not isinstance(timeframes, list):
                return jsonify({'error': 'timeframes must be a non-empty list'}), 400

            # Resolve universe to symbols via RelationshipCache
            cache = get_relationship_cache()
            symbols = cache.get_universe_symbols(universe_key)

            if not symbols:
                return jsonify({'error': f'No symbols found for universe: {universe_key}'}), 404

            # Create job
            job_id = str(uuid.uuid4())
            job_data = {
                'job_id': job_id,
                'job_type': 'csv_universe_load',  # TickStockPL recognizes this type
                'source': universe_key,
                'universe_key': universe_key,
                'symbols': symbols,
                'timeframes': timeframes,
                'years': years,
                'run_analysis_after_import': run_analysis,  # Sprint 75 Phase 2
                'requested_by': current_user.username if current_user.is_authenticated else 'admin',
                'timestamp': datetime.now().isoformat()
            }

            # Submit to Redis
            redis_client.publish('tickstock.jobs.data_load', json.dumps(job_data))

            # Store job status
            initial_status = {
                'status': 'submitted',
                'progress': '0',
                'message': f'Loading {len(symbols)} symbols from {universe_key}',
                'submitted_at': datetime.now().isoformat()
            }

            job_key = f'tickstock.jobs.status:{job_id}'
            redis_client.hset(job_key, mapping=initial_status)
            redis_client.expire(job_key, 86400)  # 24 hour TTL

            # Sprint 75 Phase 2: Store run_analysis flag in SEPARATE key
            # (TickStockPL overwrites job status, so we need persistent metadata)
            if run_analysis:
                metadata_key = f'tickstock.jobs.metadata:{job_id}'
                redis_client.hset(metadata_key, mapping={
                    'run_analysis_after_import': 'true',
                    'universe_key': universe_key,
                    'timeframe': 'daily',  # Default timeframe for analysis
                    'submitted_at': datetime.now().isoformat()
                })
                redis_client.expire(metadata_key, 86400)  # 24 hour TTL
                app.logger.info(f"Sprint 75: Stored analysis metadata for job {job_id[:8]}...")

            # Add to job history
            job_history.append({
                'job_id': job_id,
                'type': 'universe_historical_load',
                'universe_key': universe_key,
                'symbol_count': len(symbols),
                'timeframes': timeframes,
                'years': years,
                'submitted_at': datetime.now(),
                'submitted_by': current_user.username if current_user.is_authenticated else 'admin'
            })

            # Keep only last 100 jobs
            if len(job_history) > 100:
                job_history.pop(0)

            app.logger.info(
                f"Universe load job submitted: {job_id[:8]}... "
                f"({len(symbols)} symbols from {universe_key}, "
                f"timeframes: {timeframes}, years: {years})"
            )

            return jsonify({
                'job_id': job_id,
                'symbol_count': len(symbols),
                'universe_key': universe_key,
                'timeframes': timeframes,
                'years': years,
                'message': f'Job submitted: Loading {len(symbols)} symbols'
            }), 200

        except Exception as e:
            app.logger.error(f"Error triggering universe load: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/admin/historical-data/load', methods=['POST'])
    @login_required
    @admin_required
    def trigger_tickstockpl_processing():
        """
        Trigger historical data processing via TickStockPL HTTP API.
        This is the proper integration method for Sprint 33 Phase 4+.
        """
        try:
            # Get parameters from request
            data = request.get_json() or {}
            skip_market_check = data.get('skip_market_check', True)  # Default True for admin
            phases = data.get('phases', ['all'])
            universe = data.get('universe')

            # Get TickStockPL API client
            api_client = get_tickstockpl_client()

            # Trigger processing
            result = api_client.trigger_processing(
                skip_market_check=skip_market_check,
                phases=phases,
                universe=universe
            )

            if result['success']:
                # Log the successful trigger
                app.logger.info(
                    f"Admin {current_user.username if current_user.is_authenticated else 'unknown'} "
                    f"triggered processing: run_id={result.get('run_id')}"
                )

                return jsonify({
                    'success': True,
                    'run_id': result.get('run_id'),
                    'message': result.get('message', 'Processing triggered successfully'),
                    'status': result.get('status')
                })
            return jsonify({
                'success': False,
                'message': result.get('message', 'Failed to trigger processing')
            }), 500

        except Exception as e:
            app.logger.error(f"Error triggering TickStockPL processing: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Error: {str(e)}'
            }), 500

    @app.route('/admin/historical-data/job/<job_id>/status')
    @login_required
    def admin_job_status(job_id):
        """Get job status from Redis (supports both hash and string formats)"""
        try:
            job_key = f'tickstock.jobs.status:{job_id}'
            # Handle both hash and string formats (TickStockPL uses strings, AppV2 uses hashes)
            key_type = redis_client.type(job_key)
            status = {}

            if key_type == b'string' or key_type == 'string':
                # TickStockPL format: JSON string
                status_data = redis_client.get(job_key)
                if status_data:
                    if isinstance(status_data, bytes):
                        status_data = status_data.decode()
                    status = json.loads(status_data)
            elif key_type == b'hash' or key_type == 'hash':
                # AppV2 format: hash
                status = redis_client.hgetall(job_key)

            if status:
                return jsonify({
                    'success': True,
                    'job_id': job_id,
                    **status
                })
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

            # Update status to cancelled immediately (not just 'cancelling')
            status_data = redis_client.get(f'job:status:{job_id}')
            if status_data:
                status = json.loads(status_data)
                status['status'] = 'cancelled'
                status['message'] = 'Cancelled by admin'
                status['cancelled_at'] = datetime.now().isoformat()
                status['cancelled_by'] = current_user.username if current_user.is_authenticated else 'admin'
                redis_client.setex(
                    f'job:status:{job_id}',
                    300,  # 5 minute TTL (short so it disappears from UI)
                    json.dumps(status)
                )

            flash(f'Cancellation requested for job {job_id[:8]}...', 'info')
            return jsonify({'success': True, 'message': 'Cancellation requested'})

        except Exception as e:
            app.logger.error(f"Error cancelling job: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/admin/historical-data/cleanup-jobs-by-prefix', methods=['POST'])
    @login_required
    @admin_required
    def cleanup_jobs_by_prefix():
        """Clean up stale jobs matching a Job ID prefix"""
        try:
            data = request.get_json()
            prefix = data.get('prefix', '').strip()

            if not prefix or len(prefix) < 4:
                return jsonify({
                    'success': False,
                    'error': 'Job ID prefix must be at least 4 characters'
                }), 400

            cleaned_jobs = []
            cleaned_count = 0

            # Scan Redis for matching job status keys (check both patterns)
            for pattern in ['job:status:*', 'tickstock.jobs.status:*']:
                for key in redis_client.scan_iter(pattern):
                    # Key is already a string if decode_responses=True
                    key_str = key if isinstance(key, str) else key.decode('utf-8')
                    job_id = key_str.replace('job:status:', '').replace('tickstock.jobs.status:', '')

                    # Check if job ID starts with prefix
                    if job_id.startswith(prefix):
                        status_data = redis_client.get(key_str)
                        if status_data:
                            status = json.loads(status_data)

                            # Only clean up running/cancelling jobs
                            if status.get('status') in ['running', 'cancelling']:
                                # Mark as cancelled
                                status['status'] = 'cancelled'
                                status['message'] = f'Cleaned up by admin ({current_user.username})'
                                status['cleaned_at'] = datetime.now().isoformat()

                                # Set short TTL (5 minutes) so it disappears soon
                                redis_client.setex(key_str, 300, json.dumps(status))

                                cleaned_jobs.append(f"{job_id[:8]}... ({status.get('job_type', 'unknown')})")
                                cleaned_count += 1

            if cleaned_count == 0:
                return jsonify({
                    'success': False,
                    'error': f'No running/cancelling jobs found matching prefix "{prefix}"'
                }), 404

            app.logger.info(f"Admin {current_user.username} cleaned up {cleaned_count} jobs with prefix '{prefix}'")

            return jsonify({
                'success': True,
                'cleaned_count': cleaned_count,
                'cleaned_jobs': cleaned_jobs,
                'message': f'Successfully cleaned up {cleaned_count} job(s)'
            })

        except Exception as e:
            app.logger.error(f"Error cleaning up jobs: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/admin/historical-data/cleanup-all-stale-jobs', methods=['POST'])
    @login_required
    @admin_required
    def cleanup_all_stale_jobs():
        """Clean up all stale jobs (no activity in last 10 minutes)"""
        try:
            cleaned_jobs = []
            cleaned_count = 0
            stale_threshold_minutes = 10

            # Scan all job status keys in Redis (check both patterns)
            for pattern in ['job:status:*', 'tickstock.jobs.status:*']:
                for key in redis_client.scan_iter(pattern):
                    # Key is already a string if decode_responses=True
                    key_str = key if isinstance(key, str) else key.decode('utf-8')
                    job_id = key_str.replace('job:status:', '').replace('tickstock.jobs.status:', '')
                    status_data = redis_client.get(key_str)

                    if status_data:
                        status = json.loads(status_data)

                        # Only process running/cancelling jobs
                        if status.get('status') in ['running', 'cancelling']:
                            # Check if job is stale (no update in last 10 minutes)
                            last_update_str = status.get('timestamp') or status.get('started_at')

                            if last_update_str:
                                try:
                                    last_update = datetime.fromisoformat(last_update_str.replace('Z', '+00:00'))
                                    time_since_update = (datetime.now() - last_update.replace(tzinfo=None)).total_seconds() / 60

                                    # If no activity in last 10 minutes, mark as stale
                                    if time_since_update > stale_threshold_minutes:
                                        status['status'] = 'cancelled'
                                        status['message'] = f'Cleaned up - stale job (no activity for {int(time_since_update)} minutes)'
                                        status['cleaned_at'] = datetime.now().isoformat()
                                        status['cleaned_by'] = current_user.username if current_user.is_authenticated else 'admin'

                                        # Set short TTL (5 minutes)
                                        redis_client.setex(key_str, 300, json.dumps(status))

                                        cleaned_jobs.append(f"{job_id[:8]}... ({status.get('job_type', 'unknown')}) - {int(time_since_update)}min old")
                                        cleaned_count += 1

                                except (ValueError, AttributeError) as date_err:
                                    # If can't parse date, consider it stale
                                    status['status'] = 'cancelled'
                                    status['message'] = 'Cleaned up - invalid timestamp'
                                    status['cleaned_at'] = datetime.now().isoformat()
                                    redis_client.setex(key_str, 300, json.dumps(status))

                                    cleaned_jobs.append(f"{job_id[:8]}... ({status.get('job_type', 'unknown')}) - invalid date")
                                    cleaned_count += 1

            app.logger.info(f"Admin {current_user.username} cleaned up {cleaned_count} stale jobs (>{stale_threshold_minutes}min old)")

            return jsonify({
                'success': True,
                'cleaned_count': cleaned_count,
                'cleaned_jobs': cleaned_jobs,
                'message': f'Cleaned up {cleaned_count} stale job(s)',
                'threshold_minutes': stale_threshold_minutes
            })

        except Exception as e:
            app.logger.error(f"Error cleaning up stale jobs: {str(e)}")
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
        """API endpoint for getting job status (supports both hash and string formats)"""
        try:
            job_key = f'tickstock.jobs.status:{job_id}'

            # Check key type first (TickStockPL uses string, we use hash)
            key_type = redis_client.type(job_key)

            if key_type == b'none' or key_type == 'none':
                return jsonify({
                    'success': False,
                    'message': 'Job not found'
                }), 404

            status = {}

            if key_type == b'string' or key_type == 'string':
                # TickStockPL format: JSON string
                status_data = redis_client.get(job_key)
                if status_data:
                    if isinstance(status_data, bytes):
                        status_data = status_data.decode()
                    status = json.loads(status_data)

            elif key_type == b'hash' or key_type == 'hash':
                # TickStockAppV2 format: hash
                status_data = redis_client.hgetall(job_key)
                if status_data:
                    status = {
                        k.decode() if isinstance(k, bytes) else k:
                        v.decode() if isinstance(v, bytes) else v
                        for k, v in status_data.items()
                    }

            if status:
                return jsonify({
                    'success': True,
                    'job_id': job_id,
                    **status
                })

            return jsonify({
                'success': False,
                'message': 'Job not found'
            }), 404

        except Exception as e:
            app.logger.error(
                f"Error reading job {job_key}: {e}",
                exc_info=True
            )
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/admin/historical-data/jobs/status')
    @login_required
    @admin_required
    def admin_jobs_status():
        """Get all job statuses for real-time monitoring"""
        try:
            # Check TickStockPL job statuses
            active_jobs = {}
            recent_jobs = []

            # Get all job keys from Redis
            job_keys = redis_client.keys('tickstock.jobs.status:*')

            for key in job_keys:
                try:
                    # Handle both hash and string formats (TickStockPL uses strings, AppV2 uses hashes)
                    key_type = redis_client.type(key)
                    status = {}

                    if key_type == b'string' or key_type == 'string':
                        # TickStockPL format: JSON string
                        status_data = redis_client.get(key)
                        if status_data:
                            if isinstance(status_data, bytes):
                                status_data = status_data.decode()
                            status = json.loads(status_data)
                    elif key_type == b'hash' or key_type == 'hash':
                        # AppV2 format: hash
                        status = redis_client.hgetall(key)

                    if status:
                        job_id = key.split(':')[-1]

                        # Check if job is active
                        if status.get('status') in ['running', 'submitted', 'queued']:
                            active_jobs[job_id] = status
                        else:
                            recent_jobs.append({
                                'job_id': job_id,
                                **status
                            })
                except Exception as e:
                    app.logger.error(f"Error reading job {key}: {e}")

            # Sort recent jobs by completion time
            recent_jobs.sort(key=lambda x: x.get('completed_at', ''), reverse=True)

            # Calculate statistics
            stats = {
                'active_jobs': len(active_jobs),
                'completed_today': sum(1 for j in recent_jobs if j.get('status') == 'completed'),
                'failed_today': sum(1 for j in recent_jobs if j.get('status') == 'failed')
            }

            return jsonify({
                'success': True,
                'active_jobs': active_jobs,
                'recent_jobs': recent_jobs[:10],  # Last 10 jobs
                'stats': stats
            })

        except Exception as e:
            app.logger.error(f"Error getting job statuses: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/admin/historical-data/csv-universe-load', methods=['POST'])
    @login_required
    @admin_required
    def admin_csv_universe_load():
        """Handle CSV universe file loading via TickStockPL job submission"""
        try:
            # Test Redis connection
            try:
                redis_client.ping()
            except redis.ConnectionError:
                flash('Redis service unavailable. Please contact administrator.', 'danger')
                return redirect(url_for('admin_historical_dashboard'))

            # Get form data
            csv_file = request.form.get('csv_file')
            years = float(request.form.get('years', 1))
            include_ohlcv = request.form.get('include_ohlcv', 'true') == 'true'

            if not csv_file:
                flash('Please select a CSV file to load', 'warning')
                return redirect(url_for('admin_historical_dashboard'))

            # Map CSV files to universe types
            csv_universe_mapping = {
                'sp_500.csv': 'SP500',
                'nasdaq_100.csv': 'NASDAQ100',
                'dow_30.csv': 'DOW30',
                'curated-etfs.csv': 'ETF',
                'russell_3000_part1.csv': 'RUSSELL3000_P1',
                'russell_3000_part2.csv': 'RUSSELL3000_P2',
                'russell_3000_part3.csv': 'RUSSELL3000_P3',
                'russell_3000_part4.csv': 'RUSSELL3000_P4',
                'russell_3000_part5.csv': 'RUSSELL3000_P5',
                'russell_3000_part6.csv': 'RUSSELL3000_P6'
            }

            universe_type = csv_universe_mapping.get(csv_file, 'CUSTOM')

            # Create job for TickStockPL
            job_id = str(uuid.uuid4())
            job_data = {
                'job_id': job_id,
                'job_type': 'csv_universe_load',
                'csv_file': csv_file,
                'universe_type': universe_type,
                'years': years,
                'include_ohlcv': include_ohlcv,
                'requested_by': current_user.username if current_user.is_authenticated else 'admin',
                'timestamp': datetime.now().isoformat()
            }

            # Submit job to TickStockPL via Redis
            redis_client.publish('tickstock.jobs.data_load', json.dumps(job_data))

            # Store initial status
            initial_status = {
                'status': 'submitted',
                'progress': 0,
                'message': 'CSV universe load job submitted to TickStockPL',
                'description': f"Loading {csv_file} with {years} year(s) of {'OHLCV' if include_ohlcv else 'symbol'} data",
                'submitted_at': datetime.now().isoformat()
            }

            redis_client.setex(
                f'job:status:{job_id}',
                7200,  # 2 hour TTL
                json.dumps(initial_status)
            )

            # Track job in history
            job_history.append({
                'job_id': job_id,
                'type': 'csv_universe_load',
                'csv_file': csv_file,
                'started_at': datetime.now()
            })

            flash(f'CSV universe load job submitted: {csv_file} ({job_id[:8]}...)', 'success')
            app.logger.info(f"CSV universe load job submitted: {job_id} for {csv_file}")

            return redirect(url_for('admin_historical_dashboard'))

        except Exception as e:
            app.logger.error(f"Error in CSV universe load: {str(e)}")
            flash(f'Error loading CSV universe: {str(e)}', 'danger')
            return redirect(url_for('admin_historical_dashboard'))

    @app.route('/admin/historical-data/universes', methods=['GET'])
    @login_required
    @admin_required
    def get_available_universes():
        """Return list of available ETF and stock_etf_combo universes for dropdown."""
        try:
            from src.infrastructure.cache.cache_control import CacheControl
            cache_control = CacheControl()

            universes = []

            # Debug: Log cache structure
            app.logger.info(f"Cache keys: {list(cache_control.cache.keys())}")
            app.logger.info(
                f"ETF universes present: {'etf_universes' in cache_control.cache}"
            )
            app.logger.info(
                f"Stock ETF combos present: "
                f"{'stock_etf_combos' in cache_control.cache}"
            )

            # Get ETF universes (nested: cache['etf_universes'][name][key] = value)
            if 'etf_universes' in cache_control.cache:
                etf_cache = cache_control.cache['etf_universes']
                app.logger.info(
                    f"ETF universes structure: {type(etf_cache)}, "
                    f"items: {list(etf_cache.keys()) if etf_cache else 'empty'}"
                )

                for name, keys_dict in etf_cache.items():
                    app.logger.info(
                        f"Processing ETF universe name='{name}', "
                        f"type={type(keys_dict)}"
                    )

                    # Iterate through each key within this name group
                    if isinstance(keys_dict, dict):
                        for key, value in keys_dict.items():
                            if isinstance(value, list):
                                symbol_count = len(value)
                            else:
                                symbol_count = len(value.get('symbols', []))

                            universes.append({
                                'key': f'etf_universe:{key}',
                                'name': name,
                                'type': 'etf_universe',
                                'symbol_count': symbol_count
                            })
                            app.logger.info(
                                f"Added ETF universe: {name} "
                                f"(key={key}, count={symbol_count})"
                            )

            # Get stock_etf_combo universes (nested structure)
            if 'stock_etf_combos' in cache_control.cache:
                combo_cache = cache_control.cache['stock_etf_combos']
                app.logger.info(
                    f"Stock ETF combos structure: {type(combo_cache)}, "
                    f"items: {list(combo_cache.keys()) if combo_cache else 'empty'}"
                )

                for name, keys_dict in combo_cache.items():
                    if isinstance(keys_dict, dict):
                        for key, value in keys_dict.items():
                            if isinstance(value, list):
                                symbol_count = len(value)
                            else:
                                symbol_count = len(value.get('symbols', []))

                            universes.append({
                                'key': f'stock_etf_combo:{key}',
                                'name': name,
                                'type': 'stock_etf_combo',
                                'symbol_count': symbol_count
                            })
                            app.logger.info(
                                f"Added combo universe: {name} "
                                f"(key={key}, count={symbol_count})"
                            )

            app.logger.info(
                f"Returning {len(universes)} total universes for dropdown"
            )
            return jsonify({'universes': universes, 'count': len(universes)})

        except Exception as e:
            app.logger.error(f"Failed to fetch universes: {e}", exc_info=True)
            return jsonify({'error': str(e)}), 500

    # DISABLED - Sprint 62: Old route replaced by admin_trigger_universe_load() at line 295
    # This route used CacheControl and expected form data. The new route uses RelationshipCache and expects JSON.
    # @app.route('/admin/historical-data/trigger-universe-load', methods=['POST'])
    # @login_required
    # @admin_required
    # def trigger_universe_load():
    #     """Submit bulk load job for symbols from CSV file or cached universe (unified endpoint)."""
    #     try:
#             # Get parameters
#             csv_file = request.form.get('csv_file')
#             universe_key_full = request.form.get('universe_key')
#             years = request.form.get('years', 1, type=float)
#             include_ohlcv = request.form.get('include_ohlcv', 'true') == 'true'
# 
#             symbols = []
#             source_name = ''
# 
#             # Determine source: CSV file or cached universe
#             if csv_file:
#                 # === CSV FILE MODE ===
#                 app.logger.info(f"CSV mode: {csv_file}, years={years}, OHLCV={include_ohlcv}")
# 
#                 # Read symbols from CSV file
#                 import csv
#                 import os
#                 csv_path = os.path.join('data/universes', csv_file)
# 
#                 if not os.path.exists(csv_path):
#                     return jsonify({'error': f'CSV file not found: {csv_file}'}), 404
# 
#                 with open(csv_path, 'r') as f:
#                     reader = csv.DictReader(f)
#                     for row in reader:
#                         symbol = row.get('symbol', '').strip()
#                         if symbol:
#                             symbols.append(symbol)
# 
#                 source_name = csv_file
#                 app.logger.info(f"Loaded {len(symbols)} symbols from CSV: {csv_file}")
# 
#             elif universe_key_full:
#                 # === CACHED UNIVERSE MODE ===
#                 app.logger.info(f"Cached mode: {universe_key_full}, years={years}")
# 
#                 # Parse universe key (format: "etf_universe:etf_core")
#                 if ':' not in universe_key_full:
#                     return jsonify({'error': 'Invalid universe key format'}), 400
# 
#                 universe_type, universe_key = universe_key_full.split(':', 1)
# 
#                 # Get symbols from cache
#                 from src.infrastructure.cache.cache_control import CacheControl
#                 cache_control = CacheControl()
# 
#                 if universe_type == 'etf_universe':
#                     for name, keys_dict in cache_control.cache.get('etf_universes', {}).items():
#                         if universe_key in keys_dict:
#                             value = keys_dict[universe_key]
#                             symbols = value if isinstance(value, list) else value.get('symbols', [])
#                             app.logger.info(f"Found universe in cache category '{name}', key '{universe_key}'")
#                             break
# 
#                 elif universe_type == 'stock_etf_combo':
#                     for name, keys_dict in cache_control.cache.get('stock_etf_combos', {}).items():
#                         if universe_key in keys_dict:
#                             value = keys_dict[universe_key]
#                             symbols = value if isinstance(value, list) else value.get('symbols', [])
#                             app.logger.info(f"Found combo universe in cache category '{name}', key '{universe_key}'")
#                             break
# 
#                 if not symbols:
#                     app.logger.error(f"No symbols found for {universe_type}:{universe_key}")
#                     return jsonify({'error': f'No symbols found for: {universe_key}'}), 404
# 
#                 source_name = universe_key_full
#                 app.logger.info(f"Found {len(symbols)} symbols from cache: {universe_key_full}")
#                 app.logger.info(f"Symbols list: {symbols}")
# 
#             else:
#                 return jsonify({'error': 'Either csv_file or universe_key required'}), 400
# 
#             if not symbols:
#                 return jsonify({'error': f'No symbols found in {source_name}'}), 404
# 
#             app.logger.info(f"Total symbols to load: {len(symbols)} from {source_name}")
# 
#             # Generate job ID
#             import random
#             import time
#             job_id = f"universe_load_{int(time.time())}_{random.randint(0, 9999)}"  # noqa: S311
# 
#             # Publish to Redis
#             message = {
#                 'job_id': job_id,
#                 'job_type': 'csv_universe_load',  # TickStockPL recognizes this type
#                 'source': source_name,
#                 'symbols': symbols,
#                 'years': years,
#                 'submitted_at': datetime.now().isoformat()
#             }
# 
#             app.logger.info(
#                 f"Publishing job {job_id}: {len(symbols)} symbols - {symbols}"
#             )
# 
#             subscriber_count = redis_client.publish(
#                 'tickstock.jobs.data_load',
#                 json.dumps(message)
#             )
#             app.logger.info(
#                 f"Published job to Redis: {job_id}, "
#                 f"subscribers={subscriber_count}"
#             )
# 
#             if subscriber_count == 0:
#                 app.logger.warning(
#                     "No subscribers on tickstock.jobs.data_load - "
#                     "is TickStockPL running?"
#                 )
# 
#             # Store job status in Redis
#             job_key = f"tickstock.jobs.status:{job_id}"
#             redis_client.hset(job_key, mapping={
#                 'status': 'submitted',
#                 'progress': 0,
#                 'message': f'Submitted {len(symbols)} symbols from {source_name}',
#                 'total_symbols': len(symbols),
#                 'submitted_at': datetime.now().isoformat()
#             })
#             redis_client.expire(job_key, 86400)  # 24-hour TTL
# 
#             app.logger.info(
#                 f"Universe load job submitted successfully: {job_id}, "
#                 f"{len(symbols)} symbols"
#             )
# 
#             return jsonify({
#                 'success': True,
#                 'job_id': job_id,
#                 'symbol_count': len(symbols),
#                 'source': source_name
#             })
# 
#         except Exception as e:
#             app.logger.error(f"Failed to submit universe load: {e}")
#             return jsonify({'error': str(e)}), 500

    return app
