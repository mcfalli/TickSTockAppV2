"""
Admin Historical Data Management Routes
Provides web interface for managing historical data loads in production.

Features:
- Historical data status dashboard
- Trigger background data loads
- Monitor load progress
- View load history and logs
- Manage data quality and cleanup
"""

import json
import time
from datetime import datetime, timedelta
from threading import Thread
from typing import Dict, Any, List, Optional
from src.core.services.config_manager import get_config

from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from src.utils.auth_decorators import admin_required

# Historical loader will be imported on demand to avoid pandas dependency at startup

def _get_historical_loader():
    """Import and return PolygonHistoricalLoader on demand."""
    try:
        import sys
        from pathlib import Path
        sys.path.append(str(Path(__file__).parent.parent.parent))
        from src.data.historical_loader import PolygonHistoricalLoader
        return PolygonHistoricalLoader
    except ImportError as e:
        raise ImportError(f"Historical loader not available: {e}")

def _get_bulk_universe_seeder():
    """Import and return BulkUniverseSeeder on demand."""
    try:
        import sys
        from pathlib import Path
        sys.path.append(str(Path(__file__).parent.parent.parent))
        from src.data.bulk_universe_seeder import BulkUniverseSeeder, UniverseType, BulkLoadRequest
        return BulkUniverseSeeder, UniverseType, BulkLoadRequest
    except ImportError as e:
        raise ImportError(f"Bulk universe seeder not available: {e}")

def register_admin_historical_routes(app):
    """Register admin historical data routes with the Flask app"""
    
    # In-memory job tracking (in production, use Redis or database)
    active_jobs = {}
    job_history = []
    
    @app.route('/admin/historical-data')
    @login_required
    @admin_required
    def admin_historical_dashboard():
        """Main admin dashboard for historical data management"""
        try:
            # Get current data status
            PolygonHistoricalLoader = _get_historical_loader()
            loader = PolygonHistoricalLoader()
            
            daily_summary = loader.get_data_summary('day')
            minute_summary = loader.get_data_summary('minute')
            
            # Get available symbols
            available_symbols = loader.load_symbols_from_cache('top_50')
            
            # Get available bulk universes
            config = get_config()
            BulkUniverseSeeder, UniverseType, BulkLoadRequest = _get_bulk_universe_seeder()
            bulk_seeder = BulkUniverseSeeder(
                polygon_api_key=config.get('POLYGON_API_KEY'),
                database_uri=config.get('DATABASE_URI')
            )
            available_universes = bulk_seeder.get_available_universes()
            # Get job status
            job_stats = {
                'active_jobs': len([j for j in active_jobs.values() if j['status'] == 'running']),
                'completed_today': len([j for j in job_history if j['completed_at'] and 
                                      j['completed_at'].date() == datetime.now().date()]),
                'failed_today': len([j for j in job_history if j['status'] == 'failed' and 
                                   j['completed_at'] and j['completed_at'].date() == datetime.now().date()])
            }
            
            return render_template('admin/historical_data_dashboard.html',
                                 daily_summary=daily_summary,
                                 minute_summary=minute_summary,
                                 available_symbols=available_symbols,
                                 available_universes=available_universes,
                                 job_stats=job_stats,
                                 active_jobs=active_jobs,
                                 recent_jobs=job_history[-10:])
                                 
        except Exception as e:
            flash(f'Error loading dashboard: {str(e)}', 'error')
            return render_template('admin/historical_data_dashboard.html',
                                 daily_summary={}, minute_summary={}, available_symbols=[],
                                 available_universes={}, job_stats={}, active_jobs={}, recent_jobs=[])
    
    @app.route('/admin/historical-data/trigger-load', methods=['POST'])
    @login_required
    @admin_required
    def admin_trigger_historical_load():
        """Trigger a background historical data load job"""
        try:
            # Get form parameters
            load_type = request.form.get('load_type', 'universe')  # 'universe' or 'symbols'
            universe_key = request.form.get('universe_key', 'top_50')
            symbols_input = request.form.get('symbols', '')
            years = float(request.form.get('years', '1'))
            timespan = request.form.get('timespan', 'day')
            priority = request.form.get('priority', 'normal')
            
            # Validate inputs
            if years <= 0 or years > 10:
                flash('Years must be between 0.1 and 10', 'error')
                return redirect(url_for('admin_historical_dashboard'))
                
            if timespan not in ['day', 'minute']:
                flash('Invalid timespan selected', 'error')
                return redirect(url_for('admin_historical_dashboard'))
            
            # Determine symbols to load
            if load_type == 'symbols' and symbols_input:
                symbols = [s.strip().upper() for s in symbols_input.split(',') if s.strip()]
                if not symbols:
                    flash('No valid symbols provided', 'error')
                    return redirect(url_for('admin_historical_dashboard'))
            elif load_type == 'universe':
                try:
                    PolygonHistoricalLoader = _get_historical_loader()
                    loader = PolygonHistoricalLoader()
                    symbols = loader.load_symbols_from_cache(universe_key)
                    if not symbols:
                        flash(f'No symbols found in universe: {universe_key}', 'error')
                        return redirect(url_for('admin_historical_dashboard'))
                except Exception as e:
                    flash(f'Error loading universe {universe_key}: {str(e)}', 'error')
                    return redirect(url_for('admin_historical_dashboard'))
            else:
                flash('Invalid load configuration', 'error')
                return redirect(url_for('admin_historical_dashboard'))
            
            # Create job
            job_id = f"load_{int(time.time())}_{len(active_jobs)}"
            job = {
                'id': job_id,
                'status': 'queued',
                'type': load_type,
                'symbols': symbols,
                'years': years,
                'timespan': timespan,
                'priority': priority,
                'created_at': datetime.now(),
                'created_by': current_user.username if hasattr(current_user, 'username') else 'admin',
                'progress': 0,
                'current_symbol': None,
                'successful_symbols': [],
                'failed_symbols': [],
                'log_messages': [],
                'completed_at': None
            }
            
            active_jobs[job_id] = job
            
            # Start background job
            def run_load_job(job_data):
                try:
                    job_data['status'] = 'running'
                    job_data['log_messages'].append(f"Started loading {len(job_data['symbols'])} symbols")
                    
                    PolygonHistoricalLoader = _get_historical_loader()
                    loader = PolygonHistoricalLoader()
                    
                    for i, symbol in enumerate(job_data['symbols']):
                        if job_data['status'] == 'cancelled':
                            break
                            
                        job_data['current_symbol'] = symbol
                        job_data['progress'] = int((i / len(job_data['symbols'])) * 100)
                        
                        try:
                            # Ensure symbol exists in database first
                            if not loader.ensure_symbol_exists(symbol):
                                job_data['failed_symbols'].append(symbol)
                                job_data['log_messages'].append(f"[FAIL] {symbol}: Failed to create symbol record")
                                continue
                            
                            # Load data for this symbol
                            start_date = datetime.now() - timedelta(days=int(job_data['years'] * 365))
                            end_date = datetime.now()
                            
                            df = loader.fetch_symbol_data(
                                symbol, 
                                start_date.strftime('%Y-%m-%d'),
                                end_date.strftime('%Y-%m-%d'),
                                job_data['timespan']
                            )
                            
                            if not df.empty:
                                loader.save_data_to_db(df, job_data['timespan'])
                                job_data['successful_symbols'].append(symbol)
                                job_data['log_messages'].append(f"[OK] {symbol}: {len(df)} records loaded")
                            else:
                                job_data['failed_symbols'].append(symbol)
                                job_data['log_messages'].append(f"[FAIL] {symbol}: No data received")
                                
                        except Exception as e:
                            job_data['failed_symbols'].append(symbol)
                            job_data['log_messages'].append(f"[FAIL] {symbol}: {str(e)}")
                    
                    # Complete job
                    job_data['progress'] = 100
                    job_data['current_symbol'] = None
                    job_data['status'] = 'completed'
                    job_data['completed_at'] = datetime.now()
                    job_data['log_messages'].append(f"Load completed: {len(job_data['successful_symbols'])} successful, {len(job_data['failed_symbols'])} failed")
                    
                    # Move to history
                    job_history.append(job_data.copy())
                    if job_id in active_jobs:
                        del active_jobs[job_id]
                        
                except Exception as e:
                    job_data['status'] = 'failed'
                    job_data['completed_at'] = datetime.now()
                    job_data['log_messages'].append(f"Job failed: {str(e)}")
                    
                    # Move to history
                    job_history.append(job_data.copy())
                    if job_id in active_jobs:
                        del active_jobs[job_id]
            
            # Start background thread
            thread = Thread(target=run_load_job, args=(job,))
            thread.daemon = True
            thread.start()
            
            flash(f'Historical data load started: {job_id}', 'success')
            return redirect(url_for('admin_historical_dashboard'))
            
        except Exception as e:
            flash(f'Error starting load job: {str(e)}', 'error')
            return redirect(url_for('admin_historical_dashboard'))
    
    @app.route('/admin/historical-data/job/<job_id>/status')
    @login_required
    def admin_job_status(job_id):
        """Get real-time job status via AJAX"""
        job = active_jobs.get(job_id)
        if not job:
            # Check history
            job = next((j for j in job_history if j['id'] == job_id), None)
            if not job:
                return jsonify({'error': 'Job not found'}), 404
        
        return jsonify({
            'id': job.get('id', job_id),
            'status': job.get('status', 'unknown'),
            'progress': job.get('progress', 0),
            'current_symbol': job.get('current_symbol', ''),
            'successful_count': len(job.get('successful_symbols', [])),
            'failed_count': len(job.get('failed_symbols', [])),
            'log_messages': job.get('log_messages', [])[-20:],  # Last 20 messages
            'completed_at': job['completed_at'].isoformat() if job.get('completed_at') else None
        })
    
    @app.route('/admin/historical-data/job/<job_id>/cancel', methods=['POST'])
    @login_required
    @admin_required
    def admin_cancel_job(job_id):
        """Cancel a running job"""
        job = active_jobs.get(job_id)
        if job and job['status'] == 'running':
            job['status'] = 'cancelled'
            job['completed_at'] = datetime.now()
            job['log_messages'].append('Job cancelled by user')
            
            # Move to history
            job_history.append(job.copy())
            del active_jobs[job_id]
            
            return jsonify({'success': True})
        
        return jsonify({'error': 'Job not found or not running'}), 404
    
    @app.route('/admin/bulk-universe/trigger-load', methods=['POST'])
    @login_required
    @admin_required
    def admin_trigger_bulk_universe_load():
        """Trigger bulk universe loading with optional testing limiter."""
        try:
            # Get form parameters
            universe_type = request.form.get('universe_type')
            limit = request.form.get('limit')
            sort_by = request.form.get('sort_by', 'market_cap')
            overwrite_existing = request.form.get('overwrite_existing') == 'on'
            create_cache_entries = request.form.get('create_cache_entries', 'on') == 'on'
            
            # Validate inputs
            if not universe_type:
                flash('Universe type is required', 'error')
                return redirect(url_for('admin_historical_dashboard'))
                
            # Parse limit (optional testing limiter)
            limit_int = None
            if limit and limit.strip():
                try:
                    limit_int = int(limit.strip())
                    if limit_int <= 0 or limit_int > 5000:
                        flash('Limit must be between 1 and 5000', 'error')
                        return redirect(url_for('admin_historical_dashboard'))
                except ValueError:
                    flash('Limit must be a valid number', 'error')
                    return redirect(url_for('admin_historical_dashboard'))
                    
            if sort_by not in ['market_cap', 'name', 'volume']:
                flash('Invalid sort option selected', 'error')
                return redirect(url_for('admin_historical_dashboard'))
            
            # Initialize bulk seeder
            config = get_config()
            BulkUniverseSeeder, UniverseType, BulkLoadRequest = _get_bulk_universe_seeder()
            bulk_seeder = BulkUniverseSeeder(
                polygon_api_key=config.get('POLYGON_API_KEY'),
                database_uri=config.get('DATABASE_URI')
            )
            
            # Validate universe type
            universe_enum = None
            for enum_val in UniverseType:
                if enum_val.value == universe_type:
                    universe_enum = enum_val
                    break
                    
            if not universe_enum:
                flash(f'Invalid universe type: {universe_type}', 'error')
                return redirect(url_for('admin_historical_dashboard'))
            
            # Create bulk load request
            bulk_request = BulkLoadRequest(
                universe_type=universe_enum,
                limit=limit_int,
                sort_by=sort_by,
                create_cache_entries=create_cache_entries,
                overwrite_existing=overwrite_existing
            )
            
            # Estimate load size for user feedback
            estimated_size = bulk_seeder.estimate_load_size(bulk_request)
            
            # Create job
            job_id = f"bulk_{universe_type}_{int(time.time())}_{len(active_jobs)}"
            job = {
                'id': job_id,
                'type': 'bulk_universe',
                'status': 'queued',
                'universe_type': universe_type,
                'limit': limit_int,
                'sort_by': sort_by,
                'estimated_size': estimated_size,
                'overwrite_existing': overwrite_existing,
                'create_cache_entries': create_cache_entries,
                'created_at': datetime.now(),
                'created_by': current_user.username if hasattr(current_user, 'username') else 'admin',
                'progress': 0,
                'symbols_loaded': 0,
                'symbols_updated': 0,
                'symbols_skipped': 0,
                'cache_entries_created': 0,
                'log_messages': [],
                'errors': [],
                'completed_at': None
            }
            
            active_jobs[job_id] = job
            
            # Start background job
            def run_bulk_universe_job(job_data):
                try:
                    job_data['status'] = 'running'
                    job_data['log_messages'].append(
                        f"Starting bulk load of {universe_type} universe (limit: {limit_int or 'none'})"
                    )
                    
                    # Execute bulk load
                    result = bulk_seeder.load_universe(bulk_request)
                    
                    # Update job with results
                    job_data['symbols_loaded'] = result.symbols_loaded
                    job_data['symbols_updated'] = result.symbols_updated  
                    job_data['symbols_skipped'] = result.symbols_skipped
                    job_data['cache_entries_created'] = result.cache_entries_created
                    job_data['errors'].extend(result.errors)
                    job_data['progress'] = 100
                    
                    if result.success:
                        job_data['status'] = 'completed'
                        job_data['log_messages'].append(
                            f"[OK] Bulk load completed: {result.symbols_loaded} loaded, "
                            f"{result.symbols_updated} updated, {result.symbols_skipped} skipped"
                        )
                        if result.cache_entries_created:
                            job_data['log_messages'].append(
                                f"[OK] Created {result.cache_entries_created} cache entries"
                            )
                    else:
                        job_data['status'] = 'failed'
                        job_data['log_messages'].append(f"[FAIL] Bulk load failed: {'; '.join(result.errors)}")
                        
                    job_data['completed_at'] = datetime.now()
                    
                except Exception as e:
                    job_data['status'] = 'failed'
                    job_data['errors'].append(str(e))
                    job_data['log_messages'].append(f"[FAIL] Job failed with exception: {str(e)}")
                    job_data['completed_at'] = datetime.now()
                    logger.error(f"Bulk universe job {job_id} failed: {e}")
                finally:
                    # Move to history
                    job_history.append(job_data.copy())
                    if job_id in active_jobs:
                        del active_jobs[job_id]
            
            # Start job in background thread
            job_thread = Thread(target=run_bulk_universe_job, args=(job,), daemon=True)
            job_thread.start()
            
            flash(f'Bulk universe load started for {universe_type} '
                  f'(estimated {estimated_size} symbols, limit: {limit_int or "none"})', 'info')
            return redirect(url_for('admin_historical_dashboard'))
            
        except Exception as e:
            flash(f'Error starting bulk universe load: {str(e)}', 'error')
            logger.error(f"Failed to start bulk universe load: {e}")
            return redirect(url_for('admin_historical_dashboard'))

    @app.route('/admin/bulk-universe/estimate', methods=['POST'])
    @login_required
    @admin_required
    def admin_estimate_bulk_universe():
        """Get size estimate for bulk universe loading."""
        try:
            universe_type = request.json.get('universe_type')
            limit = request.json.get('limit')
            
            if not universe_type:
                return jsonify({'error': 'Universe type is required'}), 400
                
            # Parse limit
            limit_int = None
            if limit:
                try:
                    limit_int = int(limit)
                except ValueError:
                    return jsonify({'error': 'Limit must be a valid number'}), 400
            
            # Initialize bulk seeder
            config = get_config()
            BulkUniverseSeeder, UniverseType, BulkLoadRequest = _get_bulk_universe_seeder()
            bulk_seeder = BulkUniverseSeeder(
                polygon_api_key=config.get('POLYGON_API_KEY'),
                database_uri=config.get('DATABASE_URI')
            )
            
            # Find universe enum
            universe_enum = None
            for enum_val in UniverseType:
                if enum_val.value == universe_type:
                    universe_enum = enum_val
                    break
                    
            if not universe_enum:
                return jsonify({'error': f'Invalid universe type: {universe_type}'}), 400
            
            # Create request for estimation
            bulk_request = BulkLoadRequest(
                universe_type=universe_enum,
                limit=limit_int
            )
            
            # Get estimate
            estimated_size = bulk_seeder.estimate_load_size(bulk_request)
            universe_config = bulk_seeder.UNIVERSE_CONFIGS.get(universe_enum, {})
            
            return jsonify({
                'estimated_size': estimated_size,
                'universe_name': getattr(universe_config, 'name', universe_type),
                'description': getattr(universe_config, 'description', ''),
                'total_available': getattr(universe_config, 'estimated_count', 0)
            })
            
        except Exception as e:
            logger.error(f"Failed to estimate bulk universe size: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/admin/historical-data/data-summary')
    @login_required
    def admin_data_summary():
        """Get detailed data summary via AJAX"""
        try:
            PolygonHistoricalLoader = _get_historical_loader()
            loader = PolygonHistoricalLoader()
            
            # Get detailed statistics
            from psycopg2.extras import RealDictCursor
            import psycopg2
            
            conn = psycopg2.connect(loader.database_uri)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Daily data by symbol
            cursor.execute("""
                SELECT 
                    symbol,
                    COUNT(*) as record_count,
                    MIN(date) as earliest_date,
                    MAX(date) as latest_date,
                    AVG(volume) as avg_volume
                FROM ohlcv_daily
                GROUP BY symbol
                ORDER BY record_count DESC
            """)
            daily_by_symbol = [dict(row) for row in cursor.fetchall()]
            
            # Recent data gaps
            cursor.execute("""
                SELECT symbol, MAX(date) as last_date
                FROM ohlcv_daily
                GROUP BY symbol
                HAVING MAX(date) < CURRENT_DATE - INTERVAL '7 days'
                ORDER BY MAX(date) ASC
            """)
            stale_data = [dict(row) for row in cursor.fetchall()]
            
            cursor.close()
            conn.close()
            
            return jsonify({
                'daily_by_symbol': daily_by_symbol,
                'stale_data': stale_data
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/admin/historical-data/cleanup', methods=['POST'])
    @login_required
    @admin_required
    def admin_data_cleanup():
        """Clean up old or duplicate data"""
        try:
            cleanup_type = request.form.get('cleanup_type')
            
            if cleanup_type == 'duplicates':
                # Remove duplicate records (keep latest)
                PolygonHistoricalLoader = _get_historical_loader()
                loader = PolygonHistoricalLoader()
                loader._connect_db()
                
                with loader.conn.cursor() as cursor:
                    cursor.execute("""
                        DELETE FROM ohlcv_daily a USING ohlcv_daily b
                        WHERE a.symbol = b.symbol AND a.date = b.date 
                        AND a.created_at < b.created_at
                    """)
                    removed_count = cursor.rowcount
                    loader.conn.commit()
                
                flash(f'Removed {removed_count} duplicate records', 'success')
                
            elif cleanup_type == 'old_data':
                cutoff_days = int(request.form.get('cutoff_days', '2190'))  # 6 years default
                cutoff_date = datetime.now() - timedelta(days=cutoff_days)
                
                PolygonHistoricalLoader = _get_historical_loader()
                loader = PolygonHistoricalLoader()
                loader._connect_db()
                
                with loader.conn.cursor() as cursor:
                    cursor.execute("""
                        DELETE FROM ohlcv_daily WHERE date < %s
                    """, (cutoff_date.date(),))
                    removed_count = cursor.rowcount
                    loader.conn.commit()
                
                flash(f'Removed {removed_count} records older than {cutoff_days} days', 'success')
                
            return redirect(url_for('admin_historical_dashboard'))
            
        except Exception as e:
            flash(f'Cleanup error: {str(e)}', 'error')
            return redirect(url_for('admin_historical_dashboard'))
    
    @app.route('/admin/historical-data/rebuild-cache', methods=['POST'])
    @login_required
    @admin_required
    def admin_rebuild_cache():
        """Trigger cache synchronization via TickStockPL API"""
        try:
            import requests
            from flask import session

            # Get options from form
            preserve_existing = request.form.get('preserve_existing') == '1'
            mode = 'full'  # Default to full sync

            # Get TickStockPL configuration
            config = get_config()
            tickstockpl_host = config.get('TICKSTOCKPL_HOST', 'localhost')
            tickstockpl_port = config.get('TICKSTOCKPL_PORT', 8080)
            api_key = config.get('TICKSTOCKPL_API_KEY', 'tickstock-cache-sync-2025')

            # Make API call to TickStockPL
            try:
                response = requests.post(
                    f'http://{tickstockpl_host}:{tickstockpl_port}/api/processing/cache-sync/trigger',
                    headers={
                        'X-API-Key': api_key,
                        'Content-Type': 'application/json'
                    },
                    json={
                        'mode': mode,
                        'force': not preserve_existing  # Force if not preserving
                    },
                    timeout=10
                )

                if response.status_code == 202:
                    result = response.json()
                    job_id = result.get('job_id')

                    # Store job ID in session for status tracking
                    session['cache_sync_job_id'] = job_id

                    flash(f'Cache synchronization started successfully (Job ID: {job_id[:8]}...)', 'success')
                    flash('Check back in a few minutes for completion status', 'info')

                else:
                    error_msg = f'Failed to trigger cache sync: HTTP {response.status_code}'
                    try:
                        error_data = response.json()
                        if 'message' in error_data:
                            error_msg = f'Failed to trigger cache sync: {error_data["message"]}'
                    except:
                        pass
                    flash(error_msg, 'error')

            except requests.exceptions.RequestException as e:
                flash(f'Failed to connect to TickStockPL API: {str(e)}', 'error')
                logger.error(f"TickStockPL API call failed: {e}")

        except Exception as e:
            flash(f'Cache sync request failed: {str(e)}', 'error')
            logger.error(f"Cache sync error: {e}")

        return redirect(url_for('admin_historical_dashboard'))

    @app.route('/api/admin/cache-sync/status/<job_id>')
    @login_required
    @admin_required
    def get_cache_sync_status(job_id):
        """Get cache sync job status from TickStockPL"""
        try:
            import requests

            # Get TickStockPL configuration
            config = get_config()
            tickstockpl_host = config.get('TICKSTOCKPL_HOST', 'localhost')
            tickstockpl_port = config.get('TICKSTOCKPL_PORT', 8080)
            api_key = config.get('TICKSTOCKPL_API_KEY', 'tickstock-cache-sync-2025')

            response = requests.get(
                f'http://{tickstockpl_host}:{tickstockpl_port}/api/processing/cache-sync/status/{job_id}',
                headers={'X-API-Key': api_key},
                timeout=5
            )

            if response.status_code == 200:
                return jsonify(response.json())
            else:
                return jsonify({'error': 'Failed to get status'}), response.status_code

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get cache sync status: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/admin/csv-universe-load', methods=['POST'])
    @login_required
    @admin_required
    def admin_csv_universe_load():
        """Load symbols and OHLCV data from CSV file with symbol_load_log tracking."""
        try:
            # Get form parameters
            csv_file = request.form.get('csv_file')
            years = float(request.form.get('years', '1'))
            
            # Validate inputs
            if not csv_file:
                flash('CSV file selection is required', 'error')
                return redirect(url_for('admin_historical_dashboard'))
                
            if years <= 0 or years > 10:
                flash('Years must be between 0.1 and 10', 'error')
                return redirect(url_for('admin_historical_dashboard'))
            
            # Import required classes
            import csv
            import psycopg2
            from psycopg2.extras import RealDictCursor
            
            # Get project root and CSV path
            import os
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            csv_path = os.path.join(project_root, 'data', csv_file)
            
            # Verify CSV file exists
            if not os.path.exists(csv_path):
                flash(f'CSV file not found: {csv_file}', 'error')
                return redirect(url_for('admin_historical_dashboard'))
            
            # Read symbols from CSV
            symbols = []
            try:
                with open(csv_path, 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        symbol = row['symbol'].strip().upper()
                        if symbol:
                            symbols.append(symbol)
            except Exception as e:
                flash(f'Error reading CSV file: {str(e)}', 'error')
                return redirect(url_for('admin_historical_dashboard'))
            
            if not symbols:
                flash('No valid symbols found in CSV file', 'error')
                return redirect(url_for('admin_historical_dashboard'))
            
            # Create job for background processing
            job_id = f"csv_{csv_file.replace('.csv', '')}_{int(time.time())}_{len(active_jobs)}"
            job = {
                'id': job_id,
                'type': 'csv_universe',
                'status': 'queued',
                'csv_file': csv_file,
                'csv_path': csv_path,
                'symbols': symbols,
                'years': years,
                'created_at': datetime.now(),
                'created_by': current_user.username if hasattr(current_user, 'username') else 'admin',
                'progress': 0,
                'current_symbol': None,
                'symbols_loaded': 0,
                'symbols_updated': 0,
                'symbols_skipped': 0,
                'ohlcv_records_loaded': 0,
                'load_log_id': None,
                'log_messages': [],
                'errors': [],
                'completed_at': None
            }
            
            active_jobs[job_id] = job
            
            # Start background job
            def run_csv_universe_job(job_data):
                config = get_config()
                database_uri = config.get('DATABASE_URI')
                conn = None
                
                try:
                    job_data['status'] = 'running'
                    job_data['log_messages'].append(f"Starting CSV universe load from {job_data['csv_file']}")
                    job_data['log_messages'].append(f"Found {len(job_data['symbols'])} symbols to process")
                    
                    # Connect to database
                    config = get_config()
                    database_uri = config.get('DATABASE_URI')
                    conn = psycopg2.connect(database_uri)
                    cursor = conn.cursor(cursor_factory=RealDictCursor)
                    
                    # Create initial symbol_load_log entry
                    cursor.execute("""
                        INSERT INTO symbol_load_log (csv_filename, symbol_count, load_status)
                        VALUES (%s, %s, 'running')
                        RETURNING id
                    """, (job_data['csv_file'], len(job_data['symbols'])))
                    job_data['load_log_id'] = cursor.fetchone()['id']
                    conn.commit()
                    
                    # Import historical loader
                    PolygonHistoricalLoader = _get_historical_loader()
                    loader = PolygonHistoricalLoader()
                    
                    # Process each symbol
                    for i, symbol in enumerate(job_data['symbols']):
                        if job_data['status'] == 'cancelled':
                            break
                            
                        job_data['current_symbol'] = symbol
                        job_data['progress'] = int((i / len(job_data['symbols'])) * 100)
                        
                        try:
                            # Step 1: Ensure symbol exists in symbols table (with full Polygon.io data)
                            symbol_created = loader.ensure_symbol_exists(symbol)
                            
                            if symbol_created:
                                job_data['symbols_loaded'] += 1
                                job_data['log_messages'].append(f"[OK] {symbol}: Symbol created in database")
                            else:
                                # Symbol already existed, count as updated/verified
                                job_data['symbols_updated'] += 1
                                job_data['log_messages'].append(f"[OK] {symbol}: Symbol verified in database")
                            
                            # Step 2: Load OHLCV daily data
                            start_date = datetime.now() - timedelta(days=int(job_data['years'] * 365))
                            end_date = datetime.now()
                            
                            try:
                                df = loader.fetch_symbol_data(
                                    symbol, 
                                    start_date.strftime('%Y-%m-%d'),
                                    end_date.strftime('%Y-%m-%d'),
                                    'day'  # Daily data
                                )
                                
                                if not df.empty:
                                    records_saved = loader.save_data_to_db(df, 'day')
                                    job_data['ohlcv_records_loaded'] += len(df)
                                    job_data['log_messages'].append(
                                        f"[OK] {symbol}: {len(df)} OHLCV records loaded ({job_data['years']} years)"
                                    )
                                else:
                                    job_data['log_messages'].append(f"! {symbol}: No OHLCV data available")
                                    
                            except Exception as e:
                                job_data['errors'].append(f"{symbol}: OHLCV load failed - {str(e)}")
                                job_data['log_messages'].append(f"[FAIL] {symbol}: OHLCV load failed - {str(e)}")
                                
                        except Exception as e:
                            job_data['symbols_skipped'] += 1
                            job_data['errors'].append(f"{symbol}: {str(e)}")
                            job_data['log_messages'].append(f"[FAIL] {symbol}: Failed - {str(e)}")
                    
                    # Complete job
                    job_data['progress'] = 100
                    job_data['current_symbol'] = None
                    job_data['status'] = 'completed'
                    job_data['completed_at'] = datetime.now()
                    
                    # Calculate duration
                    duration = (job_data['completed_at'] - job_data['created_at']).total_seconds()
                    
                    # Update symbol_load_log with final results
                    cursor.execute("""
                        UPDATE symbol_load_log SET 
                            symbols_loaded = %s,
                            symbols_updated = %s,
                            symbols_skipped = %s,
                            ohlcv_records_loaded = %s,
                            load_status = 'completed',
                            load_duration_seconds = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (
                        job_data['symbols_loaded'],
                        job_data['symbols_updated'], 
                        job_data['symbols_skipped'],
                        job_data['ohlcv_records_loaded'],
                        duration,
                        job_data['load_log_id']
                    ))
                    conn.commit()
                    
                    # Final summary
                    job_data['log_messages'].append(
                        f"[SUCCESS] CSV load completed: {job_data['symbols_loaded']} new, "
                        f"{job_data['symbols_updated']} updated, {job_data['symbols_skipped']} skipped, "
                        f"{job_data['ohlcv_records_loaded']} OHLCV records"
                    )
                    
                except Exception as e:
                    job_data['status'] = 'failed'
                    job_data['completed_at'] = datetime.now()
                    job_data['errors'].append(f"Job failed: {str(e)}")
                    job_data['log_messages'].append(f"[FAIL] CSV load failed: {str(e)}")
                    
                    # Update symbol_load_log with failure
                    if job_data.get('load_log_id') and conn:
                        try:
                            cursor = conn.cursor()
                            cursor.execute("""
                                UPDATE symbol_load_log SET 
                                    symbols_loaded = %s,
                                    symbols_updated = %s,
                                    symbols_skipped = %s,
                                    ohlcv_records_loaded = %s,
                                    load_status = 'failed',
                                    error_message = %s,
                                    updated_at = CURRENT_TIMESTAMP
                                WHERE id = %s
                            """, (
                                job_data['symbols_loaded'],
                                job_data['symbols_updated'], 
                                job_data['symbols_skipped'],
                                job_data['ohlcv_records_loaded'],
                                str(e)[:500],  # Truncate error message if too long
                                job_data['load_log_id']
                            ))
                            conn.commit()
                        except Exception as log_error:
                            job_data['log_messages'].append(f"Failed to update load log: {str(log_error)}")
                            
                finally:
                    if conn:
                        conn.close()
                    
                    # Move to history
                    job_history.append(job_data.copy())
                    if job_id in active_jobs:
                        del active_jobs[job_id]
            
            # Start job in background thread
            job_thread = Thread(target=run_csv_universe_job, args=(job,), daemon=True)
            job_thread.start()
            
            flash(f'CSV universe load started: {csv_file} ({len(symbols)} symbols, {years} years historical data)', 'info')
            return redirect(url_for('admin_historical_dashboard'))
            
        except Exception as e:
            flash(f'Error starting CSV universe load: {str(e)}', 'error')
            return redirect(url_for('admin_historical_dashboard'))