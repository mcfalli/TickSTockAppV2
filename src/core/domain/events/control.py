"""
Control Event Class
Handles system control events in the typed event system.
"""
from src.core.domain.events.base import BaseEvent


class ControlEvent(BaseEvent):
    """
    System control event for queue management.
    Used for shutdown, flush, and other control operations.
    """
    
    def __init__(self, command: str, priority: int = 1):
        """
        Initialize control event.
        
        Args:
            command: Control command ('shutdown', 'flush', 'pause', 'resume')
            priority: Event priority (default 1 for high priority)
        """
        super().__init__(
            ticker='CONTROL',
            type='control',
            time=None  # Control events don't need timestamps
        )
        self.command = command
        self.priority = priority
    
    def __repr__(self):
        return f"ControlEvent(command='{self.command}', priority={self.priority})"