"""
Quick test for streaming events - runs without user input
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.integration.test_streaming_phase5 import StreamingEventSimulator

def main():
    print("Running quick streaming test (5 seconds)...")
    simulator = StreamingEventSimulator()

    # Run quick test
    simulator.start_session()
    simulator.simulate_pattern_detection(3)
    simulator.simulate_indicator_calculations(5)
    simulator.send_indicator_alert('RSI_OVERBOUGHT', 'AAPL', {'rsi': 75.5})
    simulator.simulate_health_update()
    simulator.stop_session()

    print("\nTest complete! Check the streaming dashboard for events.")

if __name__ == "__main__":
    main()