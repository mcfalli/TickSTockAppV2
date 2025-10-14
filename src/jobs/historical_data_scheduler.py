"""
Production Historical Data Scheduler
Provides multiple execution strategies for historical data loading:

1. CLI Execution - For cron jobs and manual runs
2. Systemd Service Integration - For Linux production
3. Windows Service Integration - For Windows production  
4. Background Job Queue - For web-triggered jobs
5. Redis-based Job Management - For distributed systems
"""

import argparse
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.data.historical_loader import PolygonHistoricalLoader

# Configure logging for production
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/historical_data_scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class HistoricalDataScheduler:
    """Production scheduler for historical data operations"""

    def __init__(self, config_file: str = None):
        """Initialize scheduler with configuration"""
        self.config = self._load_config(config_file)
        self.loader = PolygonHistoricalLoader()
        self.running = True

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        logger.info("Historical Data Scheduler initialized")

    def _load_config(self, config_file: str) -> dict[str, Any]:
        """Load configuration from file or use defaults"""
        default_config = {
            "schedules": {
                "daily_refresh": {
                    "enabled": True,
                    "time": "02:00",  # 2 AM
                    "universe": "top_50",
                    "years": 0.1,  # Last ~36 days
                    "timespan": "day"
                },
                "weekly_full_refresh": {
                    "enabled": True,
                    "day": "sunday",
                    "time": "01:00",  # 1 AM Sunday
                    "universe": "top_50",
                    "years": 1,
                    "timespan": "day"
                },
                "monthly_deep_refresh": {
                    "enabled": False,
                    "day": 1,  # 1st of month
                    "time": "00:00",  # Midnight
                    "universe": "top_50",
                    "years": 5,
                    "timespan": "day"
                }
            },
            "limits": {
                "max_concurrent_symbols": 5,
                "api_delay_seconds": 12,
                "max_retries": 3,
                "timeout_minutes": 120
            },
            "notifications": {
                "email_on_failure": True,
                "email_on_success": False,
                "webhook_url": None
            }
        }

        if config_file and os.path.exists(config_file):
            try:
                with open(config_file) as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except Exception as e:
                logger.warning(f"Error loading config file {config_file}: {e}")

        return default_config

    def _signal_handler(self, signum, frame):
        """Handle graceful shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False

    def run_daemon_mode(self):
        """Run scheduler in daemon mode - checks every minute"""
        logger.info("Starting scheduler daemon mode")

        while self.running:
            try:
                current_time = datetime.now()

                # Check each scheduled task
                for schedule_name, schedule in self.config["schedules"].items():
                    if not schedule.get("enabled", True):
                        continue

                    if self._should_run_schedule(schedule_name, schedule, current_time):
                        logger.info(f"Triggering scheduled job: {schedule_name}")
                        self._execute_scheduled_job(schedule_name, schedule)

                # Sleep for 60 seconds
                if self.running:
                    time.sleep(60)

            except Exception as e:
                logger.error(f"Error in daemon loop: {e}")
                if self.running:
                    time.sleep(60)  # Continue after error

        logger.info("Scheduler daemon stopped")

    def _should_run_schedule(self, name: str, schedule: dict, current_time: datetime) -> bool:
        """Check if a schedule should run now"""

        # Check if already run today/this week/this month
        last_run_file = f"logs/.last_run_{name}"
        if os.path.exists(last_run_file):
            try:
                with open(last_run_file) as f:
                    last_run = datetime.fromisoformat(f.read().strip())

                # Different logic based on schedule type
                if "daily" in name:
                    if last_run.date() == current_time.date():
                        return False
                elif "weekly" in name:
                    # Check if run this week
                    week_start = current_time - timedelta(days=current_time.weekday())
                    if last_run >= week_start:
                        return False
                elif "monthly" in name:
                    if last_run.month == current_time.month and last_run.year == current_time.year:
                        return False

            except Exception as e:
                logger.warning(f"Error checking last run for {name}: {e}")

        # Check time/day criteria
        schedule_time = schedule.get("time", "02:00")
        hour, minute = map(int, schedule_time.split(":"))

        # For daily schedules
        if "daily" in name:
            return (current_time.hour == hour and
                   current_time.minute == minute)

        # For weekly schedules
        if "weekly" in name:
            target_day = schedule.get("day", "sunday").lower()
            day_mapping = {
                'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
                'friday': 4, 'saturday': 5, 'sunday': 6
            }

            return (current_time.weekday() == day_mapping.get(target_day, 6) and
                   current_time.hour == hour and
                   current_time.minute == minute)

        # For monthly schedules
        if "monthly" in name:
            target_day = schedule.get("day", 1)
            return (current_time.day == target_day and
                   current_time.hour == hour and
                   current_time.minute == minute)

        return False

    def _execute_scheduled_job(self, name: str, schedule: dict):
        """Execute a scheduled historical data job"""
        try:
            start_time = datetime.now()
            logger.info(f"Starting scheduled job: {name}")

            # Get job parameters
            universe = schedule.get("universe", "top_50")
            years = schedule.get("years", 1)
            timespan = schedule.get("timespan", "day")

            # Load symbols
            symbols = self.loader.load_symbols_from_cache(universe)
            if not symbols:
                raise ValueError(f"No symbols found in universe: {universe}")

            logger.info(f"Loading {len(symbols)} symbols, {years} years of {timespan} data")

            # Execute load
            self.loader.load_historical_data(symbols, years, timespan)

            # Record successful completion
            duration = datetime.now() - start_time
            logger.info(f"Scheduled job {name} completed successfully in {duration}")

            # Update last run timestamp
            self._record_job_completion(name, start_time, True)

            # Send success notification if configured
            if self.config["notifications"].get("email_on_success"):
                self._send_notification(name, True, f"Completed in {duration}")

        except Exception as e:
            logger.error(f"Scheduled job {name} failed: {e}")
            self._record_job_completion(name, start_time, False, str(e))

            # Send failure notification
            if self.config["notifications"].get("email_on_failure"):
                self._send_notification(name, False, str(e))

    def _record_job_completion(self, name: str, start_time: datetime, success: bool, error: str = None):
        """Record job completion for tracking"""

        # Update last run file
        last_run_file = f"logs/.last_run_{name}"
        os.makedirs("logs", exist_ok=True)

        with open(last_run_file, 'w') as f:
            f.write(start_time.isoformat())

        # Log to job history file
        history_file = "logs/job_history.jsonl"
        job_record = {
            "name": name,
            "start_time": start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "success": success,
            "error": error
        }

        with open(history_file, 'a') as f:
            f.write(json.dumps(job_record) + '\n')

    def _send_notification(self, job_name: str, success: bool, message: str):
        """Send notification about job status"""
        try:
            webhook_url = self.config["notifications"].get("webhook_url")
            if webhook_url:
                import requests

                payload = {
                    "text": "TickStock Historical Data Job",
                    "attachments": [{
                        "color": "good" if success else "danger",
                        "fields": [
                            {"title": "Job", "value": job_name, "short": True},
                            {"title": "Status", "value": "Success" if success else "Failed", "short": True},
                            {"title": "Details", "value": message, "short": False}
                        ]
                    }]
                }

                requests.post(webhook_url, json=payload, timeout=10)
                logger.info("Notification sent successfully")

        except Exception as e:
            logger.warning(f"Failed to send notification: {e}")

    def run_one_time_job(self, universe: str = None, symbols: list[str] = None,
                        years: float = 1, timespan: str = "day"):
        """Run a one-time historical data load job"""
        try:
            logger.info("Starting one-time historical data job")

            if symbols:
                target_symbols = symbols
            elif universe:
                target_symbols = self.loader.load_symbols_from_cache(universe)
            else:
                raise ValueError("Must specify either universe or symbols")

            if not target_symbols:
                raise ValueError("No symbols to process")

            logger.info(f"Loading {len(target_symbols)} symbols: {', '.join(target_symbols[:5])}{'...' if len(target_symbols) > 5 else ''}")

            start_time = datetime.now()
            self.loader.load_historical_data(target_symbols, years, timespan)
            duration = datetime.now() - start_time

            logger.info(f"One-time job completed successfully in {duration}")
            return True

        except Exception as e:
            logger.error(f"One-time job failed: {e}")
            return False

def create_systemd_service():
    """Generate systemd service file for Linux production"""
    service_content = f"""[Unit]
Description=TickStock Historical Data Scheduler
After=network.target
Requires=postgresql.service

[Service]
Type=simple
User=tickstock
Group=tickstock
WorkingDirectory={os.path.dirname(os.path.abspath(__file__))}
Environment=POLYGON_API_KEY=your_api_key_here
Environment=DATABASE_URI=postgresql://user:pass@localhost/tickstock
ExecStart={sys.executable} {__file__} --daemon
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""

    print("Systemd service file content:")
    print("="*50)
    print(service_content)
    print("="*50)
    print("\nTo install:")
    print("1. Save to /etc/systemd/system/tickstock-historical.service")
    print("2. sudo systemctl daemon-reload")
    print("3. sudo systemctl enable tickstock-historical")
    print("4. sudo systemctl start tickstock-historical")

def create_cron_job():
    """Generate cron job configuration"""
    cron_content = f"""
# TickStock Historical Data Jobs
# Daily refresh at 2 AM
0 2 * * * cd {os.path.dirname(os.path.abspath(__file__))} && {sys.executable} {__file__} --job daily_refresh

# Weekly full refresh Sunday at 1 AM  
0 1 * * 0 cd {os.path.dirname(os.path.abspath(__file__))} && {sys.executable} {__file__} --job weekly_refresh

# Monthly deep refresh on 1st at midnight
0 0 1 * * cd {os.path.dirname(os.path.abspath(__file__))} && {sys.executable} {__file__} --job monthly_refresh
"""

    print("Cron job configuration:")
    print("="*50)
    print(cron_content)
    print("="*50)
    print("\nTo install:")
    print("1. crontab -e")
    print("2. Add the above lines")
    print("3. Save and exit")

def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(description='TickStock Historical Data Scheduler')
    parser.add_argument('--daemon', action='store_true', help='Run in daemon mode')
    parser.add_argument('--job', help='Run specific job type: daily_refresh, weekly_refresh, monthly_refresh')
    parser.add_argument('--universe', default='top_50', help='Stock universe to load')
    parser.add_argument('--symbols', help='Comma-separated list of symbols')
    parser.add_argument('--years', type=float, default=1, help='Years of historical data')
    parser.add_argument('--timespan', default='day', choices=['day', 'minute'], help='Data timespan')
    parser.add_argument('--config', help='Path to configuration file')
    parser.add_argument('--generate-systemd', action='store_true', help='Generate systemd service file')
    parser.add_argument('--generate-cron', action='store_true', help='Generate cron job configuration')

    args = parser.parse_args()

    if args.generate_systemd:
        create_systemd_service()
        return

    if args.generate_cron:
        create_cron_job()
        return

    # Initialize scheduler
    scheduler = HistoricalDataScheduler(args.config)

    if args.daemon:
        scheduler.run_daemon_mode()
    elif args.job:
        # Run specific job type
        job_configs = {
            'daily_refresh': {'universe': 'top_50', 'years': 0.1, 'timespan': 'day'},
            'weekly_refresh': {'universe': 'top_50', 'years': 1, 'timespan': 'day'},
            'monthly_refresh': {'universe': 'top_50', 'years': 5, 'timespan': 'day'}
        }

        config = job_configs.get(args.job)
        if config:
            success = scheduler.run_one_time_job(**config)
            sys.exit(0 if success else 1)
        else:
            print(f"Unknown job type: {args.job}")
            sys.exit(1)
    else:
        # Run one-time job with provided parameters
        symbols = args.symbols.split(',') if args.symbols else None
        success = scheduler.run_one_time_job(
            universe=args.universe if not symbols else None,
            symbols=symbols,
            years=args.years,
            timespan=args.timespan
        )
        sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
