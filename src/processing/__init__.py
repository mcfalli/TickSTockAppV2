"""
Processing Pipeline Package
Handles event processing, priority management, and worker coordination.
"""

from src.processing.tick_processor import TickProcessor, TickProcessingResult
from src.processing.event_detector import EventDetector, EventDetectionResult
from src.processing.priority_manager import PriorityManager, QueueDiagnostics
from src.processing.worker_pool import WorkerPoolManager

__all__ = [
    'TickProcessor',
    'TickProcessingResult',
    'EventDetector',
    'EventDetectionResult', 
    'PriorityManager',
    'QueueStats',
    'WorkerPoolManager'
]