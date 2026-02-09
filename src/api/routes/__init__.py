"""
API routes package.

Sprint 71: REST API Endpoints
Flask blueprints for analysis and discovery endpoints.
"""

from src.api.routes.analysis_routes import analysis_bp
from src.api.routes.discovery_routes import discovery_bp

__all__ = [
    'analysis_bp',
    'discovery_bp',
]
