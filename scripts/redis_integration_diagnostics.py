#!/usr/bin/env python3
"""
Redis Integration Diagnostics Tool
Comprehensive analysis of TickStockPL ↔ TickStockAppV2 Redis integration

This tool diagnoses the Redis pub-sub integration between TickStockPL (producer)
and TickStockAppV2 (consumer) to identify why pattern events are not being received.

Author: Redis Integration Specialist
Date: 2025-09-12
"""

import sys
import os
import time
import json
import threading
import redis
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def print_subsection(title: str):
    """Print a formatted subsection header."""
    print(f"\n{'-'*40}")
    print(f" {title}")
    print(f"{'-'*40}")

class RedisIntegrationDiagnostics:
    """Comprehensive Redis integration diagnostics for TickStock systems."""
    
    def __init__(self):
        self.redis_client = None
        self.results = {
            'connection': {},
            'channels': {},
            'producer_status': {},
            'consumer_status': {},
            'message_flow': {},
            'performance': {},
            'recommendations': []
        }
        
    def connect_redis(self) -> bool:
        """Establish Redis connection."""
        try:
            # Try multiple Redis configurations
            redis_configs = [
                {'host': 'localhost', 'port': 6379, 'db': 0},
                {'host': '127.0.0.1', 'port': 6379, 'db': 0},
                {'host': 'redis', 'port': 6379, 'db': 0},  # Docker
            ]
            
            for config in redis_configs:
                try:
                    self.redis_client = redis.Redis(**config, decode_responses=True, socket_timeout=5)
                    self.redis_client.ping()
                    self.results['connection'] = {
                        'status': 'connected',
                        'config': config,
                        'server_info': self.redis_client.info('server')
                    }
                    print(f"OK Connected to Redis: {config}")
                    return True
                except Exception as e:
                    print(f"ERR Failed to connect with {config}: {e}")
                    
            return False
            
        except Exception as e:
            self.results['connection'] = {'status': 'failed', 'error': str(e)}
            return False
    
    def diagnose_channels(self):
        """Diagnose Redis channel configuration and activity."""
        print_subsection("Channel Analysis")
        
        # TickStockPL event channels
        tickstock_channels = [
            'tickstock.events.patterns',
            'tickstock.events.backtesting.progress', 
            'tickstock.events.backtesting.results',
            'tickstock.health.status'
        ]
        
        # TickStockApp job channels  
        job_channels = [
            'tickstock.jobs.backtest',
            'tickstock.jobs.alerts',
            'tickstock.jobs.system'
        ]
        
        all_channels = tickstock_channels + job_channels
        channel_info = {}
        
        for channel in all_channels:
            try:
                # Get channel subscribers count
                subscribers = self.redis_client.pubsub_numsub(channel)[0][1]
                
                # Try to get recent activity from Redis keyspace
                activity_key = f"channel_stats:{channel}"
                last_activity = self.redis_client.get(activity_key)
                
                channel_info[channel] = {
                    'subscribers': subscribers,
                    'last_activity': last_activity,
                    'type': 'event' if 'events' in channel else 'job' if 'jobs' in channel else 'health'
                }
                
                status = "OK" if subscribers > 0 else "NO"
                print(f"{status} {channel}: {subscribers} subscribers")
                
            except Exception as e:
                channel_info[channel] = {'error': str(e)}
                print(f"ERR {channel}: Error - {e}")
        
        self.results['channels'] = channel_info
        
        # Check for pattern-specific channels
        print_subsection("Pattern Detection Channels")
        pattern_channels = self.redis_client.keys('pattern:*')
        if pattern_channels:
            print(f"Found {len(pattern_channels)} pattern-specific channels")
            for channel in pattern_channels[:5]:  # Show first 5
                print(f"  - {channel}")
        else:
            print("NO pattern-specific channels found")
    
    def test_producer_simulation(self):
        """Simulate TickStockPL producer to test message flow."""
        print_subsection("Producer Simulation Test")
        
        # Simulate pattern event
        test_pattern_event = {
            'event_type': 'pattern_detected',
            'pattern': 'Doji',
            'symbol': 'AAPL', 
            'timestamp': time.time(),
            'confidence': 0.85,
            'timeframe': '1min',
            'direction': 'reversal',
            'source': 'tickstock_pl_simulation',
            'metadata': {
                'price': 150.25,
                'volume': 1000
            }
        }
        
        try:
            # Publish test message
            channel = 'tickstock.events.patterns'
            message = json.dumps(test_pattern_event)
            subscribers = self.redis_client.publish(channel, message)
            
            print(f"OK Published test pattern event to {channel}")
            print(f"   Delivered to {subscribers} subscribers")
            print(f"   Message: {test_pattern_event['pattern']} on {test_pattern_event['symbol']}")
            
            self.results['producer_status'] = {
                'test_publish': 'success',
                'channel': channel,
                'subscribers_reached': subscribers,
                'message_size': len(message)
            }
            
            if subscribers == 0:
                print("WARN: No subscribers received the test message")
                self.results['recommendations'].append(
                    "No Redis subscribers active - TickStockAppV2 consumer may not be running"
                )
                
        except Exception as e:
            print(f"ERR Failed to publish test message: {e}")
            self.results['producer_status'] = {'test_publish': 'failed', 'error': str(e)}
    
    def test_consumer_simulation(self):
        """Test Redis consumer functionality."""
        print_subsection("Consumer Simulation Test")
        
        received_messages = []
        
        def message_listener():
            """Background thread to listen for messages."""
            try:
                pubsub = self.redis_client.pubsub()
                pubsub.subscribe('tickstock.events.patterns')
                
                print("LISTEN: Listening for messages for 10 seconds...")
                
                for message in pubsub.listen():
                    if message['type'] == 'message':
                        received_messages.append({
                            'channel': message['channel'],
                            'data': message['data'],
                            'timestamp': time.time()
                        })
                        print(f"RECV: Received message from {message['channel']}")
                        break
                        
                pubsub.unsubscribe()
                pubsub.close()
                
            except Exception as e:
                print(f"ERR Consumer error: {e}")
        
        # Start listener in background
        listener_thread = threading.Thread(target=message_listener, daemon=True)
        listener_thread.start()
        
        # Wait a moment then send test message
        time.sleep(1)
        self.test_producer_simulation()
        
        # Wait for response
        listener_thread.join(timeout=10)
        
        self.results['consumer_status'] = {
            'messages_received': len(received_messages),
            'test_duration': 10
        }
        
        if received_messages:
            print(f"OK Consumer test successful: {len(received_messages)} messages received")
        else:
            print("ERR Consumer test failed: No messages received")
            self.results['recommendations'].append(
                "Redis pub-sub message flow is not working - check Redis configuration"
            )
    
    def check_tickstock_pl_integration(self):
        """Check for TickStockPL system integration indicators."""
        print_subsection("TickStockPL Integration Status")
        
        # Check for TickStockPL system indicators
        indicators = {
            'pattern_cache': self.redis_client.exists('tickstock:patterns:*'),
            'job_queue': self.redis_client.exists('tickstock:jobs:*'),
            'system_health': self.redis_client.get('tickstock:system:health'),
            'producer_heartbeat': self.redis_client.get('tickstock:producer:heartbeat')
        }
        
        print("TickStockPL System Indicators:")
        for indicator, value in indicators.items():
            status = "OK" if value else "NO"
            print(f"{status} {indicator}: {value}")
        
        # Check for recent TickStockPL activity
        pattern_keys = self.redis_client.keys('tickstock:*')
        if pattern_keys:
            print(f"\nOK Found {len(pattern_keys)} TickStockPL keys in Redis")
            for key in pattern_keys[:5]:
                ttl = self.redis_client.ttl(key)
                print(f"   {key} (TTL: {ttl}s)")
        else:
            print("\nNO TickStockPL keys found in Redis")
            self.results['recommendations'].append(
                "TickStockPL system appears to be offline or not publishing to Redis"
            )
        
        self.results['producer_status']['indicators'] = indicators
        self.results['producer_status']['redis_keys'] = len(pattern_keys)
    
    def performance_analysis(self):
        """Analyze Redis performance metrics."""
        print_subsection("Performance Analysis")
        
        try:
            info = self.redis_client.info()
            
            performance_metrics = {
                'connected_clients': info.get('connected_clients', 0),
                'used_memory_human': info.get('used_memory_human', 'unknown'),
                'instantaneous_ops_per_sec': info.get('instantaneous_ops_per_sec', 0),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'total_commands_processed': info.get('total_commands_processed', 0)
            }
            
            # Calculate hit ratio
            hits = performance_metrics['keyspace_hits']
            misses = performance_metrics['keyspace_misses']
            hit_ratio = (hits / (hits + misses) * 100) if (hits + misses) > 0 else 0
            
            print(f"Connected Clients: {performance_metrics['connected_clients']}")
            print(f"Memory Usage: {performance_metrics['used_memory_human']}")
            print(f"Operations/sec: {performance_metrics['instantaneous_ops_per_sec']}")
            print(f"Cache Hit Ratio: {hit_ratio:.1f}%")
            print(f"Total Commands: {performance_metrics['total_commands_processed']}")
            
            self.results['performance'] = {
                **performance_metrics,
                'cache_hit_ratio': hit_ratio
            }
            
            # Performance recommendations
            if performance_metrics['connected_clients'] == 0:
                self.results['recommendations'].append(
                    "No Redis clients connected - TickStockAppV2 may not be connecting to Redis"
                )
            
            if hit_ratio < 70 and (hits + misses) > 100:
                self.results['recommendations'].append(
                    f"Low cache hit ratio ({hit_ratio:.1f}%) - consider cache optimization"
                )
                
        except Exception as e:
            print(f"ERR Performance analysis failed: {e}")
    
    def generate_integration_report(self):
        """Generate comprehensive integration report."""
        print_section("REDIS INTEGRATION DIAGNOSTIC REPORT")
        
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Redis Connection: {self.results['connection'].get('status', 'unknown')}")
        
        # Summary of findings
        print_subsection("CRITICAL FINDINGS")
        
        issues_found = 0
        
        # Check connection
        if self.results['connection'].get('status') != 'connected':
            print("X CRITICAL: Redis connection failed")
            issues_found += 1
        
        # Check producer status
        if self.results['producer_status'].get('subscribers_reached', 0) == 0:
            print("X CRITICAL: No active Redis subscribers (TickStockAppV2 consumer not listening)")
            issues_found += 1
        
        # Check TickStockPL indicators
        if self.results['producer_status'].get('redis_keys', 0) == 0:
            print("X CRITICAL: No TickStockPL data in Redis (producer system offline)")
            issues_found += 1
        
        # Check consumer functionality
        if self.results['consumer_status'].get('messages_received', 0) == 0:
            print("X CRITICAL: Redis pub-sub message flow broken")
            issues_found += 1
        
        if issues_found == 0:
            print("OK All critical systems appear to be functioning")
        
        print_subsection("RECOMMENDATIONS")
        
        if not self.results['recommendations']:
            print("OK No specific recommendations - system appears healthy")
        else:
            for i, rec in enumerate(self.results['recommendations'], 1):
                print(f"{i}. {rec}")
        
        # Additional recommendations based on analysis
        if issues_found > 0:
            print(f"\n{issues_found + len(self.results['recommendations'])}. Implement Redis health monitoring in TickStockAppV2")
            print(f"{issues_found + len(self.results['recommendations']) + 1}. Add fallback pattern detection for TickStockPL unavailability")
            print(f"{issues_found + len(self.results['recommendations']) + 2}. Create Redis integration testing suite")
        
        return issues_found
    
    def run_diagnostics(self):
        """Run complete Redis integration diagnostics."""
        print_section("TICKSTOCK REDIS INTEGRATION DIAGNOSTICS")
        print("Analyzing TickStockPL (Producer) <-> TickStockAppV2 (Consumer)")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Step 1: Redis Connection
        if not self.connect_redis():
            print("X FATAL: Cannot connect to Redis - diagnostics cannot continue")
            return False
        
        # Step 2: Channel Analysis
        self.diagnose_channels()
        
        # Step 3: TickStockPL Integration Check
        self.check_tickstock_pl_integration()
        
        # Step 4: Message Flow Test
        self.test_consumer_simulation()
        
        # Step 5: Performance Analysis
        self.performance_analysis()
        
        # Step 6: Generate Report
        issues_found = self.generate_integration_report()
        
        return issues_found == 0

def main():
    """Main diagnostic execution."""
    diagnostics = RedisIntegrationDiagnostics()
    
    try:
        success = diagnostics.run_diagnostics()
        
        if success:
            print("\nOK DIAGNOSTICS COMPLETED - System appears healthy")
            sys.exit(0)
        else:
            print("\nERR DIAGNOSTICS COMPLETED - Issues found that require attention")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\nWARN Diagnostics interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nERR FATAL ERROR during diagnostics: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()