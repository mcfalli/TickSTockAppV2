"""
Test script to simulate Sprint 33 Phase 1 processing events
This simulates events that TickStockPL will publish
"""

import argparse
import json
import time
from datetime import datetime, timedelta

import redis


class ProcessingEventSimulator:
    """Simulates processing events from TickStockPL"""

    def __init__(self, redis_host='localhost', redis_port=6379):
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            decode_responses=True
        )
        print(f"Connected to Redis at {redis_host}:{redis_port}")

    def simulate_full_processing_cycle(self, symbols_count=505, duration_minutes=30):
        """Simulate a complete daily processing cycle"""

        run_id = f"test-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        start_time = datetime.now()

        print("\n=== Starting Processing Simulation ===")
        print(f"Run ID: {run_id}")
        print(f"Symbols: {symbols_count}")
        print(f"Duration: {duration_minutes} minutes")

        # 1. Processing Started Event
        self.send_processing_started(run_id, symbols_count)
        time.sleep(2)

        # 2. Progress Updates
        phases = [
            ('data_import', 0.3),
            ('indicator_calculation', 0.5),
            ('pattern_detection', 0.7),
            ('alert_generation', 0.9),
            ('finalization', 1.0)
        ]

        symbols_per_phase = symbols_count // len(phases)
        current_symbol_index = 0

        for phase_name, target_progress in phases:
            # Send multiple progress updates per phase
            for i in range(3):
                current_symbol_index += symbols_per_phase // 3
                current_symbol = self._get_sample_symbol(current_symbol_index)

                progress = (target_progress - 0.2) + (i * 0.1)
                if progress > target_progress:
                    progress = target_progress

                self.send_processing_progress(
                    run_id=run_id,
                    phase=phase_name,
                    symbols_completed=int(symbols_count * progress),
                    symbols_total=symbols_count,
                    percent_complete=progress * 100,
                    current_symbol=current_symbol,
                    estimated_completion=start_time + timedelta(minutes=duration_minutes)
                )
                time.sleep(1)

        # 3. Processing Completed Event
        self.send_processing_completed(
            run_id=run_id,
            status='success',
            duration_seconds=duration_minutes * 60,
            symbols_processed=symbols_count,
            symbols_failed=0
        )

        print("\n=== Processing Simulation Complete ===")

    def simulate_phase2_import(self):
        """Simulate Phase 2 data import events"""

        print("\n=== Starting Phase 2 Data Import Simulation ===")

        run_id = f"import-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Data Import Started
        self.send_event('tickstock:data:import:status', {
            'event': 'data_import_started',
            'timestamp': datetime.now().isoformat() + 'Z',
            'source': 'daily_import_job',
            'version': '1.0',
            'payload': {
                'run_id': run_id,
                'universe_names': ['sp500'],
                'total_symbols': 505,
                'timeframes': ['hourly', 'daily', 'weekly', 'monthly'],
                'lookback_days': {
                    'hourly': 90,
                    'daily': 365,
                    'weekly': 730,
                    'monthly': 1825
                }
            }
        })

        time.sleep(2)

        # Job Progress Updates
        for i in range(1, 6):
            progress = i * 20
            self.send_event('tickstock:monitoring', {
                'event': 'job_progress_update',
                'timestamp': datetime.now().isoformat() + 'Z',
                'source': 'job_progress_tracker',
                'version': '1.0',
                'payload': {
                    'run_id': run_id,
                    'phase': 'data_import',
                    'total_symbols': 505,
                    'completed': progress * 5,
                    'failed': i,
                    'processed': progress * 5 + i,
                    'remaining': 505 - (progress * 5 + i),
                    'percentage': progress,
                    'current_symbol': self._get_sample_symbol(progress * 5),
                    'estimated_completion': (datetime.now() + timedelta(minutes=10)).isoformat() + 'Z',
                    'avg_processing_time_ms': 120
                }
            })
            time.sleep(1)

        # Data Import Completed
        self.send_event('tickstock:data:import:status', {
            'event': 'data_import_completed',
            'timestamp': datetime.now().isoformat() + 'Z',
            'source': 'daily_import_job',
            'version': '1.0',
            'payload': {
                'run_id': run_id,
                'duration_seconds': 2100,
                'total_symbols': 505,
                'successful_symbols': 500,
                'failed_symbols': ['SYMBOL1', 'SYMBOL2', 'SYMBOL3', 'SYMBOL4', 'SYMBOL5'],
                'total_records_imported': 183250,
                'success_rate': 99.0
            }
        })

        print("\n=== Phase 2 Import Simulation Complete ===")

    def send_processing_started(self, run_id, symbols_count):
        """Send processing started event"""
        event = {
            'event': 'daily_processing_started',
            'timestamp': datetime.now().isoformat() + 'Z',
            'source': 'daily_processing_scheduler',
            'version': '1.0',
            'payload': {
                'run_id': run_id,
                'symbols_count': symbols_count,
                'trigger_type': 'manual'
            }
        }
        self.send_event('tickstock:processing:status', event)
        print(f"[OK] Sent: daily_processing_started (run_id={run_id})")

    def send_processing_progress(self, run_id, phase, symbols_completed, symbols_total,
                                percent_complete, current_symbol, estimated_completion):
        """Send processing progress event"""
        event = {
            'event': 'daily_processing_progress',
            'timestamp': datetime.now().isoformat() + 'Z',
            'source': 'daily_processing_scheduler',
            'version': '1.0',
            'payload': {
                'run_id': run_id,
                'phase': phase,
                'symbols_completed': symbols_completed,
                'symbols_total': symbols_total,
                'percent_complete': percent_complete,
                'current_symbol': current_symbol,
                'estimated_completion': estimated_completion.isoformat() + 'Z'
            }
        }
        self.send_event('tickstock:processing:status', event)
        print(f"[OK] Sent: progress update - {phase} ({percent_complete:.1f}%) - {current_symbol}")

    def send_processing_completed(self, run_id, status, duration_seconds,
                                 symbols_processed, symbols_failed):
        """Send processing completed event"""
        event = {
            'event': 'daily_processing_completed',
            'timestamp': datetime.now().isoformat() + 'Z',
            'source': 'daily_processing_scheduler',
            'version': '1.0',
            'payload': {
                'run_id': run_id,
                'status': status,
                'duration_seconds': duration_seconds,
                'symbols_processed': symbols_processed,
                'symbols_failed': symbols_failed
            }
        }
        self.send_event('tickstock:processing:status', event)
        print(f"[OK] Sent: daily_processing_completed (status={status})")

    def send_error_event(self, severity='error', component='processing', message='Test error'):
        """Send an error event"""
        event = {
            'event': 'critical_error',
            'timestamp': datetime.now().isoformat() + 'Z',
            'source': 'daily_processing',
            'version': '1.0',
            'payload': {
                'severity': severity,
                'component': component,
                'message': message,
                'context': {
                    'run_id': 'test-error',
                    'phase': 'data_import'
                }
            }
        }
        self.send_event('tickstock:errors', event)
        print(f"[OK] Sent: error event ({severity}: {message})")

    def send_schedule_update(self):
        """Send schedule update event"""
        event = {
            'event': 'schedule_updated',
            'timestamp': datetime.now().isoformat() + 'Z',
            'source': 'scheduler',
            'version': '1.0',
            'payload': {
                'schedule': {
                    'enabled': True,
                    'trigger_time': '21:10',
                    'market_check': True,
                    'next_run': (datetime.now() + timedelta(days=1)).replace(
                        hour=21, minute=10, second=0
                    ).isoformat() + 'Z'
                }
            }
        }
        self.send_event('tickstock:processing:schedule', event)
        print("[OK] Sent: schedule_updated")

    def send_event(self, channel, event):
        """Send event to Redis channel"""
        self.redis_client.publish(channel, json.dumps(event))

    def _get_sample_symbol(self, index):
        """Get a sample symbol for testing"""
        symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'META', 'NVDA', 'AMD',
                  'INTC', 'NFLX', 'DIS', 'PYPL', 'SQ', 'SHOP', 'SNAP']
        return symbols[index % len(symbols)]

    def run_interactive_menu(self):
        """Run interactive menu for testing"""
        while True:
            print("\n=== Processing Event Simulator ===")
            print("1. Simulate full processing cycle (Phase 1)")
            print("2. Simulate data import (Phase 2)")
            print("3. Send processing started event")
            print("4. Send progress update")
            print("5. Send processing completed")
            print("6. Send error event")
            print("7. Send schedule update")
            print("8. Run continuous simulation (Ctrl+C to stop)")
            print("0. Exit")

            choice = input("\nSelect option: ")

            if choice == '1':
                self.simulate_full_processing_cycle()
            elif choice == '2':
                self.simulate_phase2_import()
            elif choice == '3':
                run_id = f"manual-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                self.send_processing_started(run_id, 505)
            elif choice == '4':
                run_id = input("Enter run_id (or press Enter for default): ") or "test-001"
                self.send_processing_progress(
                    run_id=run_id,
                    phase='data_import',
                    symbols_completed=250,
                    symbols_total=505,
                    percent_complete=49.5,
                    current_symbol='AAPL',
                    estimated_completion=datetime.now() + timedelta(minutes=15)
                )
            elif choice == '5':
                run_id = input("Enter run_id (or press Enter for default): ") or "test-001"
                self.send_processing_completed(
                    run_id=run_id,
                    status='success',
                    duration_seconds=1800,
                    symbols_processed=505,
                    symbols_failed=0
                )
            elif choice == '6':
                self.send_error_event()
            elif choice == '7':
                self.send_schedule_update()
            elif choice == '8':
                print("\nRunning continuous simulation. Press Ctrl+C to stop...")
                try:
                    while True:
                        self.simulate_full_processing_cycle(symbols_count=100, duration_minutes=5)
                        print("\nWaiting 30 seconds before next cycle...")
                        time.sleep(30)
                except KeyboardInterrupt:
                    print("\nContinuous simulation stopped")
            elif choice == '0':
                print("Exiting...")
                break
            else:
                print("Invalid option")


def main():
    parser = argparse.ArgumentParser(description='Simulate TickStockPL processing events')
    parser.add_argument('--host', default='localhost', help='Redis host')
    parser.add_argument('--port', type=int, default=6379, help='Redis port')
    parser.add_argument('--auto', action='store_true', help='Run automatic simulation')
    parser.add_argument('--phase2', action='store_true', help='Run Phase 2 import simulation')

    args = parser.parse_args()

    simulator = ProcessingEventSimulator(redis_host=args.host, redis_port=args.port)

    if args.auto:
        simulator.simulate_full_processing_cycle()
    elif args.phase2:
        simulator.simulate_phase2_import()
    else:
        simulator.run_interactive_menu()


if __name__ == "__main__":
    main()
