"""
Admin Process Stock Analysis Routes

Sprint 73: Independent Analysis Page
Provides web interface for manually triggering pattern/indicator analysis on selected
stocks or universes, with background job execution and real-time progress tracking.

Features:
- Universe selector or manual symbol entry
- Analysis type selection (patterns, indicators, both)
- Timeframe selection (daily, hourly, weekly, monthly)
- Background job execution with progress tracking
- Real-time status polling via AJAX
- Job cancellation support
- Integration with Sprint 68-72 analysis services
"""

import logging
import time
from datetime import datetime, timedelta
from threading import Thread

from flask import Blueprint, flash, jsonify, render_template, request
from flask_login import current_user, login_required
from sqlalchemy import text

from src.utils.auth_decorators import admin_required
from src.infrastructure.database.tickstock_db import TickStockDatabase
from src.core.services.config_manager import get_config

logger = logging.getLogger(__name__)

# Create blueprint
admin_process_analysis_bp = Blueprint(
    "admin_process_analysis", __name__, url_prefix="/admin/process-analysis"
)

# In-memory job tracking (in production, would use Redis or database)
active_jobs = {}
job_history = []


def _cleanup_old_patterns():
    """
    Clean up old pattern detections (keep last 48 hours).

    Sprint 74: Pattern retention policy - patterns are detection events,
    keep recent history for analysis but prevent unbounded growth.

    Returns:
        Number of patterns deleted
    """
    try:
        config = get_config()
        db = TickStockDatabase(config)

        with db.get_connection() as conn:
            result = conn.execute(text("""
                DELETE FROM daily_patterns
                WHERE detection_timestamp < NOW() - INTERVAL '48 hours'
            """))

            deleted_count = result.rowcount
            conn.commit()

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old pattern detections (>48h)")

            return deleted_count

    except Exception as e:
        logger.error(f"Pattern cleanup failed: {e}")
        return 0


def _persist_pattern_results(symbol, patterns, timeframe):
    """
    Persist detected patterns to daily_patterns table.

    Args:
        symbol: Stock symbol
        patterns: Dict of pattern results from AnalysisService
                 Format: {pattern_name: {'detected': bool, 'confidence': float}}
        timeframe: Timeframe string (daily, hourly, etc.)

    Returns:
        Number of patterns persisted
    """
    import json

    # Filter to only detected patterns (where detected=True)
    detected_patterns = {
        name: result for name, result in patterns.items()
        if result.get('detected', False) is True
    }

    if not detected_patterns:
        logger.info(f"No patterns detected for {symbol} - returning 0")
        return 0

    # Expiration: Next day at market close (daily data valid until next update)
    expiration_date = datetime.now() + timedelta(days=1)

    try:
        config = get_config()
        db = TickStockDatabase(config)

        with db.get_connection() as conn:
            for pattern_name, result in detected_patterns.items():
                detected = result['detected']
                confidence = result.get('confidence', 1.0)

                # Build comprehensive pattern_data
                pattern_data = {
                    'pattern_name': pattern_name,
                    'detected': True,
                    'confidence': float(confidence),
                    'detection_timestamp': datetime.now().isoformat(),
                    'timeframe': timeframe,
                    'symbol': symbol,
                }

                # Sprint 74: DELETE + INSERT for TimescaleDB hypertables
                # (Hypertables can't use unique constraints without timestamp)

                # Delete existing entry for this symbol+pattern+timeframe
                conn.execute(text("""
                    DELETE FROM daily_patterns
                    WHERE symbol = :symbol
                        AND pattern_type = :pattern_type
                        AND timeframe = :timeframe
                """), {
                    'symbol': symbol,
                    'pattern_type': pattern_name,
                    'timeframe': timeframe
                })

                # Insert new/updated entry
                conn.execute(text("""
                    INSERT INTO daily_patterns
                    (symbol, pattern_type, confidence, pattern_data,
                     detection_timestamp, expiration_date, timeframe, metadata)
                    VALUES (:symbol, :pattern_type, :confidence, :pattern_data,
                            NOW(), :expiration_date, :timeframe, :metadata)
                """), {
                    'symbol': symbol,
                    'pattern_type': pattern_name,
                    'confidence': float(confidence),
                    'pattern_data': json.dumps(pattern_data),
                    'expiration_date': expiration_date,
                    'timeframe': timeframe,
                    'metadata': json.dumps({
                        'source': 'admin_process_analysis',
                        'sprint': 73,
                        'detected': True
                    })
                })

            conn.commit()
            logger.info(f"Persisted {len(detected_patterns)} patterns for {symbol}")
            return len(detected_patterns)

    except Exception as e:
        logger.error(f"Failed to persist patterns for {symbol}: {e}", exc_info=True)
        return 0


def _persist_indicator_results(symbol, indicators, timeframe):
    """
    Persist indicator calculations to daily_indicators table.

    Args:
        symbol: Stock symbol
        indicators: Dict of indicator results from AnalysisService
        timeframe: Timeframe string (daily, hourly, etc.)

    Returns:
        Number of indicators persisted
    """
    import json

    if not indicators:
        return 0

    # Expiration: Next day at market close
    expiration_date = datetime.now() + timedelta(days=1)

    try:
        config = get_config()
        db = TickStockDatabase(config)

        with db.get_connection() as conn:
            for indicator_name, result in indicators.items():
                # Sprint 74: DELETE + INSERT for TimescaleDB hypertables
                # (Hypertables can't use unique constraints without timestamp)

                # Delete existing entry for this symbol+indicator+timeframe
                conn.execute(text("""
                    DELETE FROM daily_indicators
                    WHERE symbol = :symbol
                        AND indicator_type = :indicator_type
                        AND timeframe = :timeframe
                """), {
                    'symbol': symbol,
                    'indicator_type': indicator_name,
                    'timeframe': timeframe
                })

                # Insert new/updated entry
                conn.execute(text("""
                    INSERT INTO daily_indicators
                    (symbol, indicator_type, value_data,
                     calculation_timestamp, expiration_date, timeframe, metadata)
                    VALUES (:symbol, :indicator_type, :value_data,
                            NOW(), :expiration_date, :timeframe, :metadata)
                """), {
                    'symbol': symbol,
                    'indicator_type': indicator_name,
                    'value_data': json.dumps(result),
                    'expiration_date': expiration_date,
                    'timeframe': timeframe,
                    'metadata': json.dumps({
                        'source': 'admin_process_analysis',
                        'sprint': 73,
                        'indicator_type': result.get('indicator_type', 'unknown')
                    })
                })

            conn.commit()
            logger.info(f"Persisted {len(indicators)} indicators for {symbol}")
            return len(indicators)

    except Exception as e:
        logger.error(f"Failed to persist indicators for {symbol}: {e}", exc_info=True)
        return 0


def _process_single_symbol(job_data, symbol, data_service, analysis_service):
    """
    Process analysis for a single symbol.

    Helper function to reduce complexity of main background job function.
    Updates job_data in-place with results.

    Returns:
        tuple: (success: bool, error_message: str or None)
    """
    try:
        # Fetch OHLCV data (Sprint 72 database access)
        data = data_service.get_ohlcv_data(
            symbol=symbol,
            timeframe=job_data["timeframe"],
            limit=250,  # 250 bars for indicator calculations
        )

        if data.empty:
            return False, "No OHLCV data available"

        # Ensure timestamp is a column (patterns require it)
        if 'timestamp' not in data.columns and data.index.name in ['timestamp', 'date']:
            data = data.reset_index()
            if 'date' in data.columns:
                data = data.rename(columns={'date': 'timestamp'})

        # Ensure timestamp column is datetime type
        if 'timestamp' in data.columns:
            import pandas as pd
            data['timestamp'] = pd.to_datetime(data['timestamp'])

        # Determine which analysis to run based on analysis_type
        indicators_list = None
        patterns_list = None

        if job_data["analysis_type"] == "indicators":
            indicators_list = None  # None = all available indicators
            patterns_list = []  # Empty = skip patterns
        elif job_data["analysis_type"] == "patterns":
            indicators_list = []  # Empty = skip indicators
            patterns_list = None  # None = all available patterns
        else:  # 'both'
            indicators_list = None  # All indicators
            patterns_list = None  # All patterns

        # Run analysis (Sprint 68 AnalysisService)
        result = analysis_service.analyze_symbol(
            symbol=symbol,
            data=data,
            timeframe=job_data["timeframe"],
            indicators=indicators_list,
            patterns=patterns_list,
            calculate_all=(job_data["analysis_type"] == "both"),
        )

        # Count results for progress reporting
        patterns_count = sum(
            1 for p in result.get("patterns", {}).values() if p.get("detected", False)
        )
        indicators_count = len(result.get("indicators", {}))

        job_data["patterns_detected"] += patterns_count
        job_data["indicators_calculated"] += indicators_count

        # Persist results to database (Sprint 73 enhancement)
        patterns_persisted = 0
        indicators_persisted = 0

        if result.get("patterns"):
            patterns_persisted = _persist_pattern_results(
                symbol=symbol,
                patterns=result["patterns"],
                timeframe=job_data["timeframe"]
            )

        if result.get("indicators"):
            indicators_persisted = _persist_indicator_results(
                symbol=symbol,
                indicators=result["indicators"],
                timeframe=job_data["timeframe"]
            )

        return True, f"{patterns_count} patterns, {indicators_count} indicators (saved: {patterns_persisted} patterns, {indicators_persisted} indicators)"

    except Exception as e:
        logger.error(f"Analysis failed for {symbol}: {e}", exc_info=True)
        return False, str(e)


def run_analysis_job(job_data: dict, app):
    """
    Background thread function for analyzing symbols.

    Processes symbols sequentially, updating job_data in-place for real-time
    status polling. Uses Flask app context for database and service access.

    Args:
        job_data: Job dict (updated in-place, thread-safe under GIL for simple ops)
        app: Flask app object (for establishing Flask context in background thread)
    """
    try:
        # CRITICAL: Establish Flask context for this background thread
        with app.app_context():
            # Mark job as running
            job_data["status"] = "running"
            symbols_total = len(job_data["symbols"])
            job_data["log_messages"].append(
                f"Started analyzing {symbols_total} symbols "
                f"({job_data['analysis_type']}, {job_data['timeframe']})"
            )

            # Initialize services (Sprint 68-72)
            from src.analysis.data.ohlcv_data_service import OHLCVDataService
            from src.analysis.services.analysis_service import AnalysisService

            analysis_service = AnalysisService()
            data_service = OHLCVDataService()

            # Process each symbol
            for i, symbol in enumerate(job_data["symbols"]):
                # Cancellation check (CRITICAL: allows user to stop job)
                if job_data["status"] == "cancelled":
                    break

                # Update progress (for UI polling)
                job_data["current_symbol"] = symbol
                job_data["progress"] = int((i / symbols_total) * 100)
                job_data["symbols_completed"] = i

                # Process symbol using helper function
                success, message = _process_single_symbol(
                    job_data, symbol, data_service, analysis_service
                )

                if success:
                    job_data["log_messages"].append(f"[OK] {symbol}: {message}")
                else:
                    job_data["failed_symbols"].append(symbol)
                    job_data["log_messages"].append(f"[FAIL] {symbol}: {message}")

            # Complete job (or mark as cancelled if user stopped it)
            if job_data["status"] != "cancelled":
                # Sprint 74: Cleanup old patterns (48-hour retention)
                deleted_count = _cleanup_old_patterns()

                job_data["progress"] = 100
                job_data["current_symbol"] = None
                job_data["status"] = "completed"
                job_data["completed_at"] = datetime.now()

                job_data["log_messages"].append(
                    f"Analysis complete: {job_data['symbols_completed']} symbols, "
                    f"{job_data['patterns_detected']} patterns detected, "
                    f"{job_data['indicators_calculated']} indicators calculated, "
                    f"{len(job_data['failed_symbols'])} failed"
                )

                if deleted_count > 0:
                    job_data["log_messages"].append(
                        f"Cleaned up {deleted_count} old pattern detections (>48h)"
                    )

            # Move to history and remove from active jobs
            job_history.append(job_data.copy())
            job_id = job_data["id"]
            if job_id in active_jobs:
                del active_jobs[job_id]

    except Exception as e:
        # Error handling for unexpected failures
        job_data["status"] = "failed"
        job_data["completed_at"] = datetime.now()
        job_data["log_messages"].append(f"Job failed: {str(e)}")
        logger.error(f"Job {job_data['id']} failed: {e}", exc_info=True)

        # Move to history and remove from active jobs
        job_history.append(job_data.copy())
        job_id = job_data["id"]
        if job_id in active_jobs:
            del active_jobs[job_id]


@admin_process_analysis_bp.route("")
@login_required
@admin_required
def admin_process_analysis_dashboard():
    """Main admin dashboard for process stock analysis"""
    try:
        # Get universe list (will be populated via AJAX from existing endpoint)
        available_universes = []

        # Get job statistics
        job_stats = {
            "active_jobs": len([j for j in active_jobs.values() if j["status"] == "running"]),
            "completed_today": len(
                [
                    j
                    for j in job_history
                    if j.get("completed_at") and j["completed_at"].date() == datetime.now().date()
                ]
            ),
        }

        return render_template(
            "admin/process_analysis_dashboard.html",
            available_universes=available_universes,
            job_stats=job_stats,
            active_jobs=active_jobs,
            recent_jobs=job_history[-10:],
        )

    except Exception as e:
        logger.error(f"Error loading dashboard: {e}", exc_info=True)
        flash(f"Error loading dashboard: {str(e)}", "error")
        return render_template(
            "admin/process_analysis_dashboard.html",
            available_universes=[],
            job_stats={},
            active_jobs={},
            recent_jobs=[],
        )


@admin_process_analysis_bp.route("/trigger", methods=["POST"])
@login_required
@admin_required
def admin_trigger_analysis():
    """Trigger background analysis job"""
    try:
        # Parse request (JSON or form data)
        data = request.get_json() if request.is_json else request.form.to_dict()

        universe_key = data.get("universe_key", "").strip()
        symbols_input = data.get("symbols", "").strip()
        analysis_type = data.get("analysis_type", "both")
        timeframe = data.get("timeframe", "daily")

        # Validate: require universe XOR symbols
        if not universe_key and not symbols_input:
            return jsonify({"success": False, "error": "Must provide universe or symbols"}), 400

        # Validate timeframe
        valid_timeframes = ["daily", "hourly", "1min", "weekly", "monthly"]
        if timeframe not in valid_timeframes:
            return jsonify({"success": False, "error": f"Invalid timeframe: {timeframe}"}), 400

        # Validate analysis type
        valid_types = ["patterns", "indicators", "both"]
        if analysis_type not in valid_types:
            return jsonify(
                {"success": False, "error": f"Invalid analysis_type: {analysis_type}"}
            ), 400

        # Get symbols list
        from src.core.services.relationship_cache import get_relationship_cache

        cache = get_relationship_cache()

        if universe_key:
            # Load symbols from universe (Sprint 61 RelationshipCache)
            symbols = cache.get_universe_symbols(universe_key)
            if not symbols:
                return jsonify(
                    {"success": False, "error": f"No symbols found in universe: {universe_key}"}
                ), 404
        else:
            # Parse comma-separated symbols
            symbols = [s.strip().upper() for s in symbols_input.split(",") if s.strip()]
            if not symbols:
                return jsonify({"success": False, "error": "No valid symbols provided"}), 400

        # Create job
        job_id = f"analysis_{int(time.time())}_{len(active_jobs)}"
        job = {
            "id": job_id,
            "status": "queued",
            "type": "analysis",
            "universe_key": universe_key if universe_key else None,
            "symbols": symbols,
            "analysis_type": analysis_type,
            "timeframe": timeframe,
            "created_at": datetime.now(),
            "created_by": current_user.username if hasattr(current_user, "username") else "admin",
            "progress": 0,
            "current_symbol": None,
            "symbols_completed": 0,
            "symbols_total": len(symbols),
            "patterns_detected": 0,
            "indicators_calculated": 0,
            "failed_symbols": [],
            "log_messages": [],
            "completed_at": None,
        }

        active_jobs[job_id] = job

        # Start background thread
        # CRITICAL: Pass Flask app object (not current_app) to background thread
        from flask import current_app

        thread = Thread(target=run_analysis_job, args=(job, current_app._get_current_object()))
        thread.daemon = True  # CRITICAL: Allows clean shutdown
        thread.start()

        return jsonify(
            {
                "success": True,
                "job_id": job_id,
                "symbols_count": len(symbols),
                "analysis_type": analysis_type,
                "timeframe": timeframe,
            }
        ), 202  # 202 Accepted (async operation)

    except Exception as e:
        logger.error(f"Error triggering analysis: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@admin_process_analysis_bp.route("/job-status/<job_id>")
@login_required
def admin_get_analysis_job_status(job_id):
    """Get real-time job status via AJAX polling"""
    job = active_jobs.get(job_id)
    if not job:
        # Check history
        job = next((j for j in job_history if j["id"] == job_id), None)
        if not job:
            return jsonify({"error": "Job not found"}), 404

    return jsonify(
        {
            "id": job.get("id", job_id),
            "status": job.get("status", "unknown"),
            "progress": job.get("progress", 0),
            "current_symbol": job.get("current_symbol", ""),
            "symbols_completed": job.get("symbols_completed", 0),
            "symbols_total": job.get("symbols_total", 0),
            "patterns_detected": job.get("patterns_detected", 0),
            "indicators_calculated": job.get("indicators_calculated", 0),
            "failed_symbols": job.get("failed_symbols", []),
            "log_messages": job.get("log_messages", [])[-20:],  # Last 20 only
            "completed_at": job["completed_at"].isoformat() if job.get("completed_at") else None,
        }
    ), 200


@admin_process_analysis_bp.route("/job/<job_id>/cancel", methods=["POST"])
@login_required
@admin_required
def admin_cancel_analysis_job(job_id):
    """Cancel a running analysis job"""
    job = active_jobs.get(job_id)
    if job and job["status"] == "running":
        job["status"] = "cancelled"
        job["completed_at"] = datetime.now()
        job["log_messages"].append("Job cancelled by user")

        # Move to history (background thread will see cancelled status and stop)
        job_history.append(job.copy())
        del active_jobs[job_id]

        return jsonify({"success": True}), 200

    return jsonify({"error": "Job not found or not running"}), 404
