#!/usr/bin/env python3
"""
Sprint 14 Phase 3 Redis Message Flow Integration Tests

Specialized tests for Redis pub-sub integration patterns and message flow validation:
- Message delivery performance and ordering guarantees
- Cross-system communication patterns (TickStockApp <-> TickStockPL)
- Message persistence and offline handling
- Channel management and subscription patterns
- Error handling and resilience in Redis operations
- Queue overflow and high-volume message handling

Performance Targets:
- Message delivery: <100ms end-to-end
- Message persistence: Available for offline consumers
- High-volume handling: 1000+ messages without overflow
- Connection recovery: Automatic reconnection within 5s
"""

import os
from src.core.services.config_manager import get_config
import sys
import pytest
import asyncio
import json
import time
import threading
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, patch, AsyncMock
import concurrent.futures

# Initialize configuration with fallback
try:
    config = get_config()
except Exception:
    # Fallback if config_manager not available
    class ConfigFallback:
        def get(self, key, default=None):
            return default  # Use defaults only
    config = ConfigFallback()


# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

import redis
import redis.asyncio as async_redis

# Import Phase 3 modules  
from src.data.etf_universe_manager import ETFUniverseManager
from archive.sprint36_migration.cache_entries_synchronizer import CacheEntriesSynchronizer

class TestPhase3RedisMessageFlows:
    """
    Redis Message Flow Integration Tests for Sprint 14 Phase 3
    
    Validates:
    1. Message delivery performance and reliability
    2. Cross-system communication via Redis pub-sub
    3. Message persistence for offline consumers
    4. High-volume message handling and queue management
    5. Error recovery and connection resilience
    6. Channel organization and subscription patterns
    """
    
    @pytest.fixture(scope="class")
    def redis_config(self):
        """Redis configuration for testing"""
        return {
            'host': config.get('TEST_REDIS_HOST', 'localhost'),
            'port': int(config.get('TEST_REDIS_PORT', '6379')),
            'db': 14  # Dedicated test database for message flow tests
        }
    
    @pytest.fixture
    def redis_client(self, redis_config):
        """Synchronous Redis client"""
        client = redis.Redis(**redis_config, decode_responses=True)
        client.flushdb()
        yield client
        client.flushdb()
        client.close()
    
    @pytest.fixture
    async def async_redis_client(self, redis_config):
        """Asynchronous Redis client"""
        client = async_redis.Redis(**redis_config, decode_responses=True)
        await client.flushdb()
        yield client
        await client.flushdb()
        await client.aclose()
    
    @pytest.fixture
    def message_tracker(self):
        """Helper for tracking message delivery"""
        class MessageTracker:
            def __init__(self):
                self.sent_messages = []
                self.received_messages = []
                self.delivery_times = []
                self.errors = []
            
            def track_sent(self, channel, message, timestamp=None):
                self.sent_messages.append({
                    'channel': channel,
                    'message': message,
                    'sent_at': timestamp or time.time()
                })
            
            def track_received(self, channel, message, timestamp=None):
                received_at = timestamp or time.time()
                self.received_messages.append({
                    'channel': channel,
                    'message': message,
                    'received_at': received_at
                })
                
                # Calculate delivery time if matching sent message found
                for sent in self.sent_messages:
                    if (sent['channel'] == channel and 
                        isinstance(message, dict) and 
                        message.get('message_id') and
                        sent['message'].get('message_id') == message.get('message_id')):
                        delivery_time = (received_at - sent['sent_at']) * 1000  # ms
                        self.delivery_times.append(delivery_time)
                        break
            
            def track_error(self, error, context=None):
                self.errors.append({
                    'error': str(error),
                    'context': context,
                    'timestamp': time.time()
                })
                
            @property
            def avg_delivery_time(self):
                return sum(self.delivery_times) / len(self.delivery_times) if self.delivery_times else 0
                
            @property
            def max_delivery_time(self):
                return max(self.delivery_times) if self.delivery_times else 0
                
            @property
            def delivery_success_rate(self):
                if not self.sent_messages:
                    return 0
                return len(self.received_messages) / len(self.sent_messages) * 100
                
        return MessageTracker()

    # =================================================================
    # MESSAGE DELIVERY PERFORMANCE TESTS
    # =================================================================
    
    @pytest.mark.asyncio
    async def test_message_delivery_latency_target(self, async_redis_client, message_tracker):
        """Test message delivery meets <100ms latency target"""
        test_channel = 'tickstock.performance.latency_test'
        
        # Set up subscriber
        pubsub = async_redis_client.pubsub()
        await pubsub.subscribe(test_channel)
        
        async def latency_listener():
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    data = json.loads(message['data'])
                    message_tracker.track_received(test_channel, data)
        
        listener_task = asyncio.create_task(latency_listener())
        
        try:
            # Send test messages with precise timestamps
            for i in range(20):
                message = {
                    'message_id': f'latency_test_{i}',
                    'timestamp': time.time(),
                    'data': f'test_payload_{i}'
                }
                
                send_time = time.time()
                await async_redis_client.publish(test_channel, json.dumps(message))
                message_tracker.track_sent(test_channel, message, send_time)
                
                await asyncio.sleep(0.05)  # 50ms between messages
            
            # Wait for message processing
            await asyncio.sleep(1.0)
            
            # Validate delivery performance
            assert len(message_tracker.delivery_times) >= 15, f"Only {len(message_tracker.delivery_times)} messages measured"
            
            avg_latency = message_tracker.avg_delivery_time
            max_latency = message_tracker.max_delivery_time
            
            assert avg_latency < 100, f"Average latency {avg_latency:.2f}ms exceeds 100ms target"
            assert max_latency < 200, f"Max latency {max_latency:.2f}ms exceeds reasonable bounds"
            
            # Validate delivery success rate
            success_rate = message_tracker.delivery_success_rate
            assert success_rate >= 95, f"Delivery success rate {success_rate:.1f}% too low"
            
        finally:
            listener_task.cancel()
            await pubsub.unsubscribe(test_channel)
            await pubsub.aclose()
    
    @pytest.mark.asyncio
    async def test_message_ordering_guarantee(self, async_redis_client):
        """Test message ordering is preserved in Redis pub-sub"""
        test_channel = 'tickstock.ordering.test'
        received_messages = []
        
        pubsub = async_redis_client.pubsub()
        await pubsub.subscribe(test_channel)
        
        async def order_listener():
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    data = json.loads(message['data'])
                    received_messages.append(data)
        
        listener_task = asyncio.create_task(order_listener())
        
        try:
            # Send ordered sequence of messages
            message_count = 50
            for i in range(message_count):
                message = {
                    'sequence_id': i,
                    'timestamp': time.time(),
                    'operation': f'universe_update_{i}'
                }
                await async_redis_client.publish(test_channel, json.dumps(message))
                await asyncio.sleep(0.001)  # Minimal delay
            
            # Wait for all messages
            await asyncio.sleep(0.5)
            
            # Validate ordering
            assert len(received_messages) >= message_count * 0.95, "Too many messages lost"
            
            # Check sequence integrity
            sequence_ids = [msg['sequence_id'] for msg in received_messages]
            for i in range(len(sequence_ids) - 1):
                assert sequence_ids[i] < sequence_ids[i + 1], f"Message order violated at position {i}"
                
        finally:
            listener_task.cancel()
            await pubsub.unsubscribe(test_channel)
            await pubsub.aclose()
    
    @pytest.mark.asyncio
    async def test_concurrent_publisher_performance(self, async_redis_client):
        """Test performance with multiple concurrent publishers"""
        test_channel = 'tickstock.concurrent.test'
        all_messages = []
        
        pubsub = async_redis_client.pubsub()
        await pubsub.subscribe(test_channel)
        
        async def collector():
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    data = json.loads(message['data'])
                    all_messages.append(data)
        
        collector_task = asyncio.create_task(collector())
        
        async def concurrent_publisher(publisher_id, message_count):
            """Simulate concurrent service publishing messages"""
            for i in range(message_count):
                message = {
                    'publisher_id': publisher_id,
                    'message_seq': i,
                    'timestamp': time.time(),
                    'service': f'service_{publisher_id}',
                    'data': f'concurrent_payload_{publisher_id}_{i}'
                }
                await async_redis_client.publish(test_channel, json.dumps(message))
                await asyncio.sleep(0.01)  # Simulate realistic publishing rate
        
        try:
            # Run 5 concurrent publishers
            start_time = time.time()
            
            tasks = [
                concurrent_publisher(publisher_id, 20)
                for publisher_id in range(5)
            ]
            
            await asyncio.gather(*tasks)
            
            # Wait for message collection
            await asyncio.sleep(0.5)
            total_time = time.time() - start_time
            
            # Validate performance
            expected_messages = 5 * 20  # 5 publishers * 20 messages each
            received_count = len(all_messages)
            
            assert received_count >= expected_messages * 0.95, f"Lost messages: {received_count}/{expected_messages}"
            assert total_time < 5.0, f"Concurrent publishing took {total_time:.2f}s, too slow"
            
            # Validate all publishers represented
            publisher_ids = set(msg['publisher_id'] for msg in all_messages)
            assert len(publisher_ids) == 5, f"Missing publishers: {publisher_ids}"
            
        finally:
            collector_task.cancel()
            await pubsub.unsubscribe(test_channel)
            await pubsub.aclose()

    # =================================================================
    # CROSS-SYSTEM COMMUNICATION TESTS
    # =================================================================
    
    @pytest.mark.asyncio
    async def test_etf_manager_to_tickstockapp_flow(self, async_redis_client):
        """Test ETF Universe Manager to TickStockApp message flow"""
        # Simulate TickStockApp subscriber
        tickstockapp_messages = []
        
        pubsub = async_redis_client.pubsub()
        await pubsub.subscribe('tickstock.universe.updated')
        
        async def tickstockapp_subscriber():
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    data = json.loads(message['data'])
                    tickstockapp_messages.append({
                        'received_at': time.time(),
                        'data': data
                    })
        
        subscriber_task = asyncio.create_task(tickstockapp_subscriber())
        
        try:
            # Simulate ETF Universe Manager publishing updates
            etf_updates = [
                {
                    'service': 'etf_universe_manager',
                    'event_type': 'universe_expansion_complete',
                    'themes_processed': 7,
                    'total_symbols': 215,
                    'timestamp': datetime.now().isoformat()
                },
                {
                    'service': 'etf_universe_manager',
                    'event_type': 'theme_updated',
                    'theme': 'sectors',
                    'symbol_count': 10,
                    'action': 'updated',
                    'timestamp': datetime.now().isoformat()
                }
            ]
            
            for update in etf_updates:
                await async_redis_client.publish('tickstock.universe.updated', json.dumps(update))
                await asyncio.sleep(0.1)
            
            # Wait for TickStockApp processing
            await asyncio.sleep(0.3)
            
            # Validate TickStockApp received messages
            assert len(tickstockapp_messages) == 2, f"Expected 2 messages, got {len(tickstockapp_messages)}"
            
            # Validate message structure for TickStockApp consumption
            expansion_msg = next(msg for msg in tickstockapp_messages if msg['data'].get('event_type') == 'universe_expansion_complete')
            theme_msg = next(msg for msg in tickstockapp_messages if msg['data'].get('event_type') == 'theme_updated')
            
            # Expansion message validation
            expansion_data = expansion_msg['data']
            assert 'themes_processed' in expansion_data, "Missing themes_processed for TickStockApp"
            assert 'total_symbols' in expansion_data, "Missing total_symbols for TickStockApp"
            assert expansion_data['service'] == 'etf_universe_manager', "Wrong service identification"
            
            # Theme update message validation
            theme_data = theme_msg['data']
            assert 'theme' in theme_data, "Missing theme for TickStockApp"
            assert 'symbol_count' in theme_data, "Missing symbol_count for TickStockApp"
            assert theme_data['action'] == 'updated', "Wrong action type"
            
        finally:
            subscriber_task.cancel()
            await pubsub.unsubscribe('tickstock.universe.updated')
            await pubsub.aclose()
    
    @pytest.mark.asyncio
    async def test_cache_sync_to_tickstockapp_flow(self, async_redis_client):
        """Test Cache Synchronizer to TickStockApp message flow"""
        tickstockapp_sync_messages = []
        
        # Subscribe to both sync channels TickStockApp would monitor
        pubsub = async_redis_client.pubsub()
        await pubsub.subscribe('tickstock.cache.sync_complete', 'tickstock.universe.updated')
        
        async def tickstockapp_sync_subscriber():
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    tickstockapp_sync_messages.append({
                        'channel': message['channel'],
                        'data': json.loads(message['data']),
                        'received_at': time.time()
                    })
        
        subscriber_task = asyncio.create_task(tickstockapp_sync_subscriber())
        
        try:
            # Simulate Cache Synchronizer publishing sync completion
            sync_complete_msg = {
                'service': 'cache_entries_synchronizer',
                'event_type': 'daily_sync_complete',
                'total_changes': 15,
                'task_summary': {
                    'market_cap_recalculation': 'completed',
                    'ipo_universe_assignment': 'completed',
                    'delisted_cleanup': 'completed'
                },
                'timestamp': datetime.now().isoformat()
            }
            
            await async_redis_client.publish('tickstock.cache.sync_complete', json.dumps(sync_complete_msg))
            
            # Simulate individual universe updates
            universe_updates = [
                {
                    'service': 'cache_entries_synchronizer',
                    'event_type': 'universe_synchronized',
                    'universe': 'large_cap',
                    'change_count': 5,
                    'actions': ['added', 'added', 'removed', 'added', 'added']
                },
                {
                    'service': 'cache_entries_synchronizer',
                    'event_type': 'universe_synchronized',
                    'universe': 'top_500',
                    'change_count': 8,
                    'actions': ['added', 'removed', 'added', 'added']
                }
            ]
            
            for update in universe_updates:
                await async_redis_client.publish('tickstock.universe.updated', json.dumps(update))
                await asyncio.sleep(0.05)
            
            # Wait for TickStockApp processing
            await asyncio.sleep(0.5)
            
            # Validate TickStockApp received sync messages
            assert len(tickstockapp_sync_messages) >= 3, f"Expected 3+ messages, got {len(tickstockapp_sync_messages)}"
            
            # Validate sync completion message
            sync_msgs = [m for m in tickstockapp_sync_messages if m['channel'] == 'tickstock.cache.sync_complete']
            assert len(sync_msgs) == 1, "Missing or duplicate sync completion message"
            
            sync_data = sync_msgs[0]['data']
            assert sync_data['service'] == 'cache_entries_synchronizer', "Wrong service identification"
            assert 'total_changes' in sync_data, "Missing total_changes for TickStockApp"
            assert 'task_summary' in sync_data, "Missing task_summary for TickStockApp"
            
            # Validate universe update messages  
            universe_msgs = [m for m in tickstockapp_sync_messages if m['channel'] == 'tickstock.universe.updated']
            assert len(universe_msgs) >= 2, "Missing universe update messages"
            
            for msg in universe_msgs:
                msg_data = msg['data']
                assert 'universe' in msg_data, "Missing universe field for TickStockApp"
                assert 'change_count' in msg_data, "Missing change_count for TickStockApp"
                assert msg_data['service'] == 'cache_entries_synchronizer', "Wrong service identification"
                
        finally:
            subscriber_task.cancel()
            await pubsub.unsubscribe('tickstock.cache.sync_complete', 'tickstock.universe.updated')
            await pubsub.aclose()
    
    @pytest.mark.asyncio
    async def test_multi_service_channel_isolation(self, async_redis_client):
        """Test different services can use same channels without interference"""
        service_messages = {'etf_manager': [], 'cache_sync': [], 'test_service': []}
        
        pubsub = async_redis_client.pubsub()
        await pubsub.subscribe('tickstock.universe.updated')
        
        async def service_message_collector():
            async for message in pubssub.listen():
                if message['type'] == 'message':
                    data = json.loads(message['data'])
                    service = data.get('service', 'unknown')
                    if service in service_messages:
                        service_messages[service].append(data)
        
        collector_task = asyncio.create_task(service_message_collector())
        
        try:
            # Publish messages from different services to same channel
            messages = [
                ('etf_universe_manager', {'service': 'etf_universe_manager', 'event': 'expansion', 'data': 'etf_data'}),
                ('cache_entries_synchronizer', {'service': 'cache_entries_synchronizer', 'event': 'sync', 'data': 'sync_data'}),
                ('test_service', {'service': 'test_service', 'event': 'test', 'data': 'test_data'}),
                ('etf_universe_manager', {'service': 'etf_universe_manager', 'event': 'validation', 'data': 'validation_data'}),
                ('cache_entries_synchronizer', {'service': 'cache_entries_synchronizer', 'event': 'cleanup', 'data': 'cleanup_data'})
            ]
            
            for service_id, message in messages:
                await async_redis_client.publish('tickstock.universe.updated', json.dumps(message))
                await asyncio.sleep(0.1)
            
            await asyncio.sleep(0.5)
            
            # Validate service isolation
            assert len(service_messages['etf_manager']) == 2, "ETF manager messages not isolated"
            assert len(service_messages['cache_sync']) == 2, "Cache sync messages not isolated"  
            assert len(service_messages['test_service']) == 1, "Test service messages not isolated"
            
            # Validate message content integrity
            etf_events = [msg['event'] for msg in service_messages['etf_manager']]
            assert 'expansion' in etf_events and 'validation' in etf_events, "ETF manager message content corrupted"
            
            sync_events = [msg['event'] for msg in service_messages['cache_sync']]
            assert 'sync' in sync_events and 'cleanup' in sync_events, "Cache sync message content corrupted"
            
        finally:
            collector_task.cancel()
            await pubsub.unsubscribe('tickstock.universe.updated')
            await pubsub.aclose()

    # =================================================================
    # MESSAGE PERSISTENCE AND OFFLINE HANDLING TESTS
    # =================================================================
    
    @pytest.mark.asyncio
    async def test_message_persistence_streams(self, async_redis_client):
        """Test Redis Streams for message persistence and offline consumer support"""
        stream_key = 'tickstock.persistent.universe_updates'
        
        # Add messages to stream (simulating online publishing)
        persistent_messages = [
            {'service': 'etf_universe_manager', 'event': 'expansion', 'theme': 'sectors', 'timestamp': time.time()},
            {'service': 'etf_universe_manager', 'event': 'validation', 'status': 'complete', 'timestamp': time.time()},
            {'service': 'cache_entries_synchronizer', 'event': 'sync_complete', 'changes': 12, 'timestamp': time.time()},
            {'service': 'cache_entries_synchronizer', 'event': 'ipo_assignment', 'count': 3, 'timestamp': time.time()}
        ]
        
        message_ids = []
        for msg in persistent_messages:
            msg_id = await async_redis_client.xadd(stream_key, msg)
            message_ids.append(msg_id)
            await asyncio.sleep(0.05)
        
        # Simulate offline TickStockApp coming online
        await asyncio.sleep(0.2)
        
        # Read all messages from beginning (offline consumer behavior)
        messages = await async_redis_client.xread({stream_key: '0'})
        
        assert len(messages) == 1, "Expected one stream"
        stream_name, stream_messages = messages[0]
        assert stream_name == stream_key, "Wrong stream name"
        assert len(stream_messages) == 4, f"Expected 4 persisted messages, got {len(stream_messages)}"
        
        # Validate message persistence and order
        for i, (msg_id, fields) in enumerate(stream_messages):
            assert msg_id in message_ids, f"Message ID {msg_id} not in original IDs"
            assert 'service' in fields, f"Missing service field in message {i}"
            assert 'event' in fields, f"Missing event field in message {i}"
            assert 'timestamp' in fields, f"Missing timestamp field in message {i}"
        
        # Test consumer group functionality for multiple TickStockApp instances
        consumer_group = 'tickstock_app_consumers'
        
        # Create consumer group
        try:
            await async_redis_client.xgroup_create(stream_key, consumer_group, id='0', mkstream=True)
        except redis.exceptions.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise
        
        # Simulate consumer reading with acknowledgment
        consumer_messages = await async_redis_client.xreadgroup(
            consumer_group, 'consumer_1', {stream_key: '>'}, count=2
        )
        
        assert len(consumer_messages[0][1]) <= 2, "Consumer read more messages than requested"
        
        # Acknowledge messages
        for msg_id, fields in consumer_messages[0][1]:
            await async_redis_client.xack(stream_key, consumer_group, msg_id)
        
        # Cleanup
        await async_redis_client.delete(stream_key)
    
    @pytest.mark.asyncio 
    async def test_offline_consumer_catch_up(self, async_redis_client):
        """Test offline consumers can catch up on missed messages"""
        catch_up_channel = 'tickstock.catchup.test'
        stream_key = 'tickstock.catchup.stream'
        
        # Phase 1: Publish messages while consumer is "offline"
        offline_messages = []
        for i in range(10):
            message = {
                'message_id': f'offline_{i}',
                'service': 'etf_universe_manager',
                'event': f'update_{i}',
                'timestamp': time.time()
            }
            offline_messages.append(message)
            await async_redis_client.xadd(stream_key, message)
            await asyncio.sleep(0.01)
        
        # Phase 2: Consumer comes online and catches up
        caught_up_messages = []
        
        # Read all messages since stream start
        messages = await async_redis_client.xread({stream_key: '0'})
        
        if messages:
            stream_name, stream_messages = messages[0]
            for msg_id, fields in stream_messages:
                caught_up_messages.append(fields)
        
        # Validate catch-up completeness
        assert len(caught_up_messages) == 10, f"Expected 10 messages, caught up on {len(caught_up_messages)}"
        
        # Validate message order preservation
        message_ids = [msg['message_id'] for msg in caught_up_messages]
        expected_ids = [f'offline_{i}' for i in range(10)]
        assert message_ids == expected_ids, "Message order not preserved during catch-up"
        
        # Phase 3: Test real-time processing after catch-up
        real_time_messages = []
        
        # Set up real-time subscriber
        pubsub = async_redis_client.pubsub()
        await pubsub.subscribe(catch_up_channel)
        
        async def real_time_listener():
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    real_time_messages.append(json.loads(message['data']))
        
        listener_task = asyncio.create_task(real_time_listener())
        
        try:
            # Publish real-time messages
            for i in range(5):
                message = {
                    'message_id': f'realtime_{i}',
                    'service': 'cache_entries_synchronizer',
                    'event': f'sync_{i}',
                    'timestamp': time.time()
                }
                await async_redis_client.publish(catch_up_channel, json.dumps(message))
                await asyncio.sleep(0.02)
            
            await asyncio.sleep(0.2)
            
            # Validate real-time processing works after catch-up
            assert len(real_time_messages) == 5, f"Expected 5 real-time messages, got {len(real_time_messages)}"
            
        finally:
            listener_task.cancel()
            await pubsub.unsubscribe(catch_up_channel)
            await pubsub.aclose()
            await async_redis_client.delete(stream_key)

    # =================================================================
    # HIGH-VOLUME AND ERROR HANDLING TESTS
    # =================================================================
    
    @pytest.mark.asyncio
    async def test_high_volume_message_handling(self, async_redis_client, message_tracker):
        """Test system handles high-volume messages without overflow"""
        high_volume_channel = 'tickstock.highvolume.test'
        
        pubsub = async_redis_client.pubsub()
        await pubsub.subscribe(high_volume_channel)
        
        async def high_volume_collector():
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    data = json.loads(message['data'])
                    message_tracker.track_received(high_volume_channel, data)
        
        collector_task = asyncio.create_task(high_volume_collector())
        
        try:
            # Send high volume of messages (1000 messages)
            message_count = 1000
            batch_size = 50
            
            start_time = time.time()
            
            for batch in range(0, message_count, batch_size):
                batch_tasks = []
                for i in range(batch, min(batch + batch_size, message_count)):
                    message = {
                        'message_id': f'hv_{i}',
                        'batch': batch // batch_size,
                        'sequence': i,
                        'timestamp': time.time(),
                        'data': f'high_volume_payload_{i}'
                    }
                    
                    task = async_redis_client.publish(high_volume_channel, json.dumps(message))
                    batch_tasks.append(task)
                    message_tracker.track_sent(high_volume_channel, message)
                
                # Execute batch in parallel
                await asyncio.gather(*batch_tasks)
                await asyncio.sleep(0.01)  # Small delay between batches
            
            # Wait for processing
            await asyncio.sleep(2.0)
            total_time = time.time() - start_time
            
            # Validate high-volume performance
            received_count = len(message_tracker.received_messages)
            success_rate = (received_count / message_count) * 100
            
            assert success_rate >= 95, f"High-volume success rate {success_rate:.1f}% too low"
            assert total_time < 30, f"High-volume processing took {total_time:.1f}s, too slow"
            
            # Validate no message corruption
            message_ids = set(msg['message_id'] for msg in message_tracker.received_messages)
            assert len(message_ids) == received_count, "Duplicate messages detected in high-volume test"
            
            # Check for proper batching behavior
            batches_represented = set(msg['batch'] for msg in message_tracker.received_messages)
            expected_batches = set(range(message_count // batch_size))
            assert batches_represented == expected_batches, "Missing batches in high-volume processing"
            
        finally:
            collector_task.cancel()
            await pubsub.unsubscribe(high_volume_channel)
            await pubsub.aclose()
    
    @pytest.mark.asyncio
    async def test_redis_connection_recovery(self, redis_config, message_tracker):
        """Test Redis connection recovery and message delivery resilience"""
        recovery_channel = 'tickstock.recovery.test'
        
        # Create initial connection
        redis_client = async_redis.Redis(**redis_config, decode_responses=True, 
                                        health_check_interval=1, retry_on_timeout=True)
        
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(recovery_channel)
        
        recovery_messages = []
        
        async def recovery_listener():
            try:
                async for message in pubsub.listen():
                    if message['type'] == 'message':
                        data = json.loads(message['data'])
                        recovery_messages.append(data)
                        message_tracker.track_received(recovery_channel, data)
            except Exception as e:
                message_tracker.track_error(e, "recovery_listener")
        
        listener_task = asyncio.create_task(recovery_listener())
        
        try:
            # Phase 1: Normal operation
            for i in range(5):
                message = {'message_id': f'normal_{i}', 'timestamp': time.time()}
                await redis_client.publish(recovery_channel, json.dumps(message))
                message_tracker.track_sent(recovery_channel, message)
                await asyncio.sleep(0.1)
            
            await asyncio.sleep(0.5)
            initial_count = len(recovery_messages)
            assert initial_count == 5, f"Normal operation failed: {initial_count}/5 messages"
            
            # Phase 2: Simulate connection disruption
            await redis_client.connection_pool.disconnect()
            await asyncio.sleep(0.2)
            
            # Attempt to send messages during disruption
            disruption_messages = []
            for i in range(3):
                message = {'message_id': f'disruption_{i}', 'timestamp': time.time()}
                disruption_messages.append(message)
                try:
                    await redis_client.publish(recovery_channel, json.dumps(message))
                    message_tracker.track_sent(recovery_channel, message)
                except Exception as e:
                    message_tracker.track_error(e, f"disruption_send_{i}")
                await asyncio.sleep(0.1)
            
            # Phase 3: Connection recovery
            await asyncio.sleep(1.0)  # Allow recovery time
            
            # Test recovery by sending more messages
            for i in range(5):
                message = {'message_id': f'recovery_{i}', 'timestamp': time.time()}
                try:
                    await redis_client.publish(recovery_channel, json.dumps(message))
                    message_tracker.track_sent(recovery_channel, message)
                except Exception as e:
                    message_tracker.track_error(e, f"recovery_send_{i}")
                await asyncio.sleep(0.1)
            
            await asyncio.sleep(0.5)
            
            # Validate recovery behavior
            final_count = len(recovery_messages)
            recovery_count = final_count - initial_count
            
            assert recovery_count >= 3, f"Connection recovery failed: only {recovery_count} post-recovery messages"
            
            # Validate error handling
            connection_errors = [e for e in message_tracker.errors if 'connection' in e['error'].lower()]
            assert len(connection_errors) > 0, "No connection errors tracked during disruption"
            
            # Check message IDs to ensure recovery messages arrived
            final_message_ids = [msg['message_id'] for msg in recovery_messages]
            recovery_ids = [mid for mid in final_message_ids if mid.startswith('recovery_')]
            assert len(recovery_ids) >= 3, f"Expected 3+ recovery messages, got {len(recovery_ids)}"
            
        finally:
            listener_task.cancel()
            await pubsub.unsubscribe(recovery_channel)
            await pubsub.aclose()
            await redis_client.aclose()
    
    @pytest.mark.asyncio
    async def test_message_queue_overflow_handling(self, async_redis_client):
        """Test graceful handling of message queue overflow scenarios"""
        overflow_channel = 'tickstock.overflow.test'
        
        # Configure subscriber with limited buffer
        pubsub = async_redis_client.pubsub()
        await pubsub.subscribe(overflow_channel)
        
        processed_messages = []
        processing_delays = []
        
        async def slow_processor():
            """Simulate slow message processing to create backlog"""
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    process_start = time.time()
                    
                    # Simulate processing work
                    await asyncio.sleep(0.1)  # 100ms processing time
                    
                    data = json.loads(message['data'])
                    processed_messages.append(data)
                    
                    process_time = time.time() - process_start
                    processing_delays.append(process_time)
        
        processor_task = asyncio.create_task(slow_processor())
        
        try:
            # Send messages faster than they can be processed
            message_count = 50
            send_interval = 0.02  # 50ms between sends, 100ms to process = backlog
            
            start_time = time.time()
            
            for i in range(message_count):
                message = {
                    'message_id': f'overflow_{i}',
                    'timestamp': time.time(),
                    'sequence': i,
                    'data': f'overflow_test_payload_{i}'
                }
                
                await async_redis_client.publish(overflow_channel, json.dumps(message))
                await asyncio.sleep(send_interval)
            
            send_duration = time.time() - start_time
            
            # Allow processing to catch up
            catch_up_time = 10.0  # Allow reasonable time for processing backlog
            await asyncio.sleep(catch_up_time)
            
            # Validate overflow handling
            processed_count = len(processed_messages)
            success_rate = (processed_count / message_count) * 100
            
            # System should handle backlog gracefully, even if not 100% processed
            assert success_rate >= 80, f"Overflow handling failed: only {success_rate:.1f}% processed"
            assert processed_count > 0, "No messages processed during overflow test"
            
            # Validate processing remained stable
            if processing_delays:
                avg_delay = sum(processing_delays) / len(processing_delays)
                assert avg_delay < 0.5, f"Processing delays too high: {avg_delay:.2f}s average"
            
            # Validate message ordering preserved despite overflow
            sequences = [msg['sequence'] for msg in processed_messages]
            if len(sequences) > 1:
                for i in range(len(sequences) - 1):
                    assert sequences[i] < sequences[i + 1], f"Message order violated during overflow at position {i}"
                    
        finally:
            processor_task.cancel()
            await pubsub.unsubscribe(overflow_channel)
            await pubsub.aclose()

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])