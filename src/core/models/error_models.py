"""Sprint 32: Error Management System Models

This module defines the standard error format for the unified error handling
system shared between TickStockAppV2 and TickStockPL.

Created: 2025-09-25
Purpose: Pydantic models for consistent error handling across systems
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
import uuid


class ErrorMessage(BaseModel):
    """Standard error format for both TickStockAppV2 and TickStockPL systems

    This model ensures consistent error structure across all systems for:
    - File logging
    - Database storage
    - Redis pub-sub messaging
    - Cross-system error integration
    """

    error_id: str = Field(..., description="UUID for tracking errors across systems")
    source: str = Field(..., description="System that generated the error: 'TickStockAppV2' or 'TickStockPL'")
    severity: str = Field(..., description="Error severity level: critical|error|warning|info|debug")
    category: Optional[str] = Field(None, description="Error category: pattern|database|network|validation|performance|security|configuration")
    message: str = Field(..., description="Human-readable error message")
    component: Optional[str] = Field(None, description="Component/class that generated the error")
    traceback: Optional[str] = Field(None, description="Stack trace if available")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context data (symbol, user_id, etc.)")
    timestamp: datetime = Field(..., description="When the error occurred")

    @classmethod
    def create(
        cls,
        source: str,
        severity: str,
        message: str,
        category: Optional[str] = None,
        component: Optional[str] = None,
        traceback: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> 'ErrorMessage':
        """Create a new ErrorMessage with auto-generated ID and timestamp

        Args:
            source: System name ('TickStockAppV2' or 'TickStockPL')
            severity: Error severity level
            message: Human-readable error message
            category: Optional error category
            component: Optional component name
            traceback: Optional stack trace
            context: Optional context dictionary

        Returns:
            ErrorMessage: Fully populated error message
        """
        return cls(
            error_id=str(uuid.uuid4()),
            source=source,
            severity=severity,
            category=category,
            message=message,
            component=component,
            traceback=traceback,
            context=context or {},
            timestamp=datetime.utcnow()
        )

    def to_json(self) -> str:
        """Convert to JSON for Redis publishing

        Returns:
            str: JSON representation of the error message
        """
        return self.model_dump_json()

    @classmethod
    def from_json(cls, json_str: str) -> 'ErrorMessage':
        """Create ErrorMessage from JSON received via Redis

        Args:
            json_str: JSON string representation

        Returns:
            ErrorMessage: Parsed error message object

        Raises:
            ValidationError: If JSON is invalid or missing required fields
        """
        return cls.model_validate_json(json_str)

    def to_database_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format suitable for database insertion

        Returns:
            Dict: Dictionary with database column names as keys
        """
        return {
            'error_id': self.error_id,
            'source': self.source,
            'severity': self.severity,
            'category': self.category,
            'message': self.message,
            'component': self.component,
            'traceback': self.traceback,
            'context': self.context,
            'timestamp': self.timestamp
        }

    def get_display_message(self) -> str:
        """Get formatted message for logging display

        Returns:
            str: Formatted message with source and severity
        """
        return f"[{self.source}] [{self.severity.upper()}] {self.message}"

    def __str__(self) -> str:
        """String representation for logging"""
        context_str = f" Context: {self.context}" if self.context else ""
        return f"{self.get_display_message()}{context_str}"


# Severity level constants for validation and comparison
SEVERITY_LEVELS = {
    'debug': 10,
    'info': 20,
    'warning': 30,
    'error': 40,
    'critical': 50
}

# Valid error categories
ERROR_CATEGORIES = [
    'pattern',       # Pattern detection failures
    'database',      # Database connection/query errors
    'network',       # External API/network errors
    'validation',    # Data validation failures
    'performance',   # Performance threshold violations
    'security',      # Authentication/authorization failures
    'configuration', # System configuration errors
    'integration',   # Cross-system integration errors
    'websocket',     # WebSocket connection/message errors
    'redis'          # Redis connection/pub-sub errors
]

def validate_severity(severity: str) -> bool:
    """Validate if severity level is valid

    Args:
        severity: Severity level to validate

    Returns:
        bool: True if valid severity level
    """
    return severity.lower() in SEVERITY_LEVELS

def validate_category(category: str) -> bool:
    """Validate if error category is valid

    Args:
        category: Category to validate

    Returns:
        bool: True if valid category
    """
    return category.lower() in ERROR_CATEGORIES

def get_severity_level(severity: str) -> int:
    """Get numeric level for severity comparison

    Args:
        severity: Severity level string

    Returns:
        int: Numeric level (0 if invalid)
    """
    return SEVERITY_LEVELS.get(severity.lower(), 0)