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

import os
import json
import time
from datetime import datetime, timedelta
from threading import Thread
from typing import Dict, Any, List, Optional

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
                                 job_stats=job_stats,
                                 active_jobs=active_jobs,
                                 recent_jobs=job_history[-10:])
                                 
        except Exception as e:
            flash(f'Error loading dashboard: {str(e)}', 'error')
            return render_template('admin/historical_data_dashboard.html',
                                 daily_summary={}, minute_summary={}, available_symbols=[],
                                 job_stats={}, active_jobs={}, recent_jobs=[])
    
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
                                job_data['log_messages'].append(f"✗ {symbol}: Failed to create symbol record")
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
                                job_data['log_messages'].append(f"✓ {symbol}: {len(df)} records loaded")
                            else:
                                job_data['failed_symbols'].append(symbol)
                                job_data['log_messages'].append(f"✗ {symbol}: No data received")
                                
                        except Exception as e:
                            job_data['failed_symbols'].append(symbol)
                            job_data['log_messages'].append(f"✗ {symbol}: {str(e)}")
                    
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
            'id': job['id'],
            'status': job['status'],
            'progress': job['progress'],
            'current_symbol': job['current_symbol'],
            'successful_count': len(job['successful_symbols']),
            'failed_count': len(job['failed_symbols']),
            'log_messages': job['log_messages'][-20:],  # Last 20 messages
            'completed_at': job['completed_at'].isoformat() if job['completed_at'] else None
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