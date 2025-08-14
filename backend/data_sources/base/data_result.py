from datetime import datetime
from typing import Any, Optional

class DataResult:
    """Standardized result type for data provider operations."""
    
    def __init__(self, success: bool, data: Any = None, error: str = None):
        self.success = success
        self.data = data
        self.error = error
        self.timestamp = datetime.now()
    
    @classmethod
    def ok(cls, data: Any = None) -> 'DataResult':
        """Create a successful result."""
        return cls(success=True, data=data)
    
    @classmethod
    def error(cls, message: str) -> 'DataResult':
        """Create an error result."""
        return cls(success=False, error=message)
    
    def __bool__(self) -> bool:
        """Allow using the result in boolean context to check success."""
        return self.success
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        if self.success:
            return f"DataResult(success=True, data={repr(self.data)})"
        else:
            return f"DataResult(success=False, error='{self.error}')"