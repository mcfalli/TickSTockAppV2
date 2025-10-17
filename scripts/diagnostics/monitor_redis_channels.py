"""
Monitor Redis Channel Activity - Sprint 43 Diagnostic
Real-time monitoring of what Redis channels are being received by TickStockAppV2
"""

import subprocess
import sys
from collections import defaultdict
from datetime import datetime

def monitor_channels():
    """Monitor log file for Redis channel activity."""

    print("=" * 80)
    print("REDIS CHANNEL MONITOR - Sprint 43 Diagnostic")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("Monitoring for Redis channel messages...")
    print("Press Ctrl+C to stop and see summary")
    print("=" * 80)
    print()

    channel_counts = defaultdict(int)
    event_type_counts = defaultdict(int)
    total_messages = 0

    try:
        # Use tail -f to follow log file
        process = subprocess.Popen(
            ['tail', '-f', 'logs/tickstock.log'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        for line in process.stdout:
            # Look for channel debug messages
            if "REDIS-SUBSCRIBER DEBUG: Received message on channel:" in line:
                total_messages += 1
                # Extract channel name
                parts = line.split("'")
                if len(parts) >= 2:
                    channel = parts[1]
                    channel_counts[channel] += 1
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Channel: {channel}")

            # Look for event type mapping
            elif "REDIS-SUBSCRIBER DEBUG: Channel" in line and "-> EventType:" in line:
                # Extract event type
                if "EventType." in line:
                    event_type = line.split("EventType.")[1].strip().rstrip("'\"")
                    event_type_counts[event_type] += 1

            # Look for streaming buffer flush cycles
            elif "STREAMING-BUFFER: Flush cycle" in line:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {line.split('INFO - ')[-1].strip()}")

            # Look for pattern/indicator processing
            elif "Received streaming pattern" in line or "Received streaming indicator" in line:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] *** {line.split('INFO - ')[-1].strip()}")

    except KeyboardInterrupt:
        print()
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Total messages received: {total_messages}")
        print()

        print("Channels Received:")
        for channel, count in sorted(channel_counts.items(), key=lambda x: -x[1]):
            print(f"  {channel}: {count} messages")
        print()

        print("Event Types Mapped:")
        for event_type, count in sorted(event_type_counts.items(), key=lambda x: -x[1]):
            print(f"  {event_type}: {count} events")
        print()

        # Analysis
        print("ANALYSIS:")
        if 'tickstock:indicators:streaming' in channel_counts:
            print(f"  ✅ Indicators channel WORKING ({channel_counts['tickstock:indicators:streaming']} messages)")
        else:
            print("  ❌ Indicators channel NOT receiving messages")

        if 'tickstock:patterns:streaming' in channel_counts or 'tickstock:patterns:detected' in channel_counts:
            pattern_count = channel_counts.get('tickstock:patterns:streaming', 0) + channel_counts.get('tickstock:patterns:detected', 0)
            print(f"  ✅ Patterns channel WORKING ({pattern_count} messages)")
        else:
            print("  ❌ Patterns channel NOT receiving messages")

        print()
        print("=" * 80)

if __name__ == '__main__':
    try:
        monitor_channels()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
