"""
Run streaming test - clean version without Unicode issues
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.integration.test_streaming_phase5 import StreamingEventSimulator
import time

def main():
    print("\n" + "="*60)
    print("Running Streaming Integration Test")
    print("="*60)

    simulator = StreamingEventSimulator()

    print("\n1. Starting streaming session...")
    simulator.start_session()
    time.sleep(1)

    print("\n2. Generating pattern detections...")
    simulator.simulate_pattern_detection(5)

    print("\n3. Generating indicator calculations...")
    simulator.simulate_indicator_calculations(5)

    print("\n4. Sending indicator alerts...")
    simulator.send_indicator_alert('RSI_OVERBOUGHT', 'AAPL', {'rsi': 75.5})
    simulator.send_indicator_alert('RSI_OVERSOLD', 'TSLA', {'rsi': 28.3})
    simulator.send_indicator_alert('MACD_BULLISH_CROSS', 'MSFT', {'macd': 0.5, 'signal': 0.3})

    print("\n5. Sending health update...")
    simulator.simulate_health_update()

    print("\n6. Waiting for events to process...")
    time.sleep(2)

    print("\n7. Stopping session...")
    simulator.stop_session()

    print("\n" + "="*60)
    print("Test Complete!")
    print("Check http://localhost:5000/streaming/ to see the events")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()