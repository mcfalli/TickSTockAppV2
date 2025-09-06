"""
Pattern Registry Service - Sprint 22 Phase 1
Handles dynamic pattern loading, configuration, and management.
Provides database-driven pattern definitions with real-time enable/disable control.
"""

import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
import logging
from dataclasses import dataclass
from sqlalchemy import text

logger = logging.getLogger(__name__)

@dataclass
class PatternDefinition:
    """Pattern definition data structure."""
    id: int
    name: str
    short_description: str
    long_description: Optional[str]
    basic_logic_description: Optional[str]
    code_reference: Optional[str]
    category: str
    enabled: bool
    display_order: int
    confidence_threshold: float
    risk_level: str
    typical_success_rate: Optional[float]
    created_date: datetime
    updated_date: datetime
    created_by: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'name': self.name,
            'short_description': self.short_description,
            'long_description': self.long_description,
            'basic_logic_description': self.basic_logic_description,
            'code_reference': self.code_reference,
            'category': self.category,
            'enabled': self.enabled,
            'display_order': self.display_order,
            'confidence_threshold': float(self.confidence_threshold),
            'risk_level': self.risk_level,
            'typical_success_rate': float(self.typical_success_rate) if self.typical_success_rate else None,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'updated_date': self.updated_date.isoformat() if self.updated_date else None,
            'created_by': self.created_by
        }

class PatternRegistryService:
    """
    Pattern Registry Service for dynamic pattern management.
    Handles database-driven pattern loading and configuration.
    """
    
    def __init__(self):
        """Initialize pattern registry service."""
        self.cache_timeout = 300  # 5 minutes cache
        self._patterns_cache = None
        self._cache_timestamp = 0
        self._enabled_patterns_cache = None
        self._enabled_cache_timestamp = 0
        
        self.service_stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'successful_queries': 0,
            'failed_queries': 0,
            'avg_query_time_ms': 0,
            'query_times': []
        }
        
        logger.info("PATTERN-REGISTRY: Pattern registry service initialized")
    
    def is_flask_context_available(self) -> bool:
        """Check if Flask application context is available."""
        try:
            from flask import has_app_context
            return has_app_context()
        except ImportError:
            logger.error("Flask not available - cannot check application context")
            return False
        except Exception as e:
            logger.warning(f"Error checking Flask context: {e}")
            return False
    
    def _is_cache_valid(self, cache_timestamp: float) -> bool:
        """Check if cache is still valid."""
        return (time.time() - cache_timestamp) < self.cache_timeout
    
    def _record_query_time(self, start_time: float):
        """Record query execution time for performance monitoring."""
        query_time_ms = (time.time() - start_time) * 1000
        self.service_stats['query_times'].append(query_time_ms)
        
        # Keep only last 100 query times
        if len(self.service_stats['query_times']) > 100:
            self.service_stats['query_times'] = self.service_stats['query_times'][-100:]
        
        # Update average
        self.service_stats['avg_query_time_ms'] = sum(self.service_stats['query_times']) / len(self.service_stats['query_times'])
    
    def get_enabled_patterns(self) -> List[PatternDefinition]:
        """
        Get all enabled patterns for UI loading.
        
        Returns:
            List[PatternDefinition]: List of enabled patterns ordered by display_order
        """
        start_time = time.time()
        self.service_stats['total_requests'] += 1
        
        try:
            # Check cache first
            if self._enabled_patterns_cache and self._is_cache_valid(self._enabled_cache_timestamp):
                self.service_stats['cache_hits'] += 1
                return self._enabled_patterns_cache
            
            self.service_stats['cache_misses'] += 1
            
            if not self.is_flask_context_available():
                logger.error("PATTERN-REGISTRY: No Flask context available for database query")
                return []
            
            from src.infrastructure.database import db
            
            query = text("""
                SELECT id, name, short_description, long_description, basic_logic_description,
                       code_reference, category, enabled, display_order, confidence_threshold,
                       risk_level, typical_success_rate, created_date, updated_date, created_by
                FROM pattern_definitions 
                WHERE enabled = true 
                ORDER BY display_order, name
            """)
            
            result = db.session.execute(query)
            rows = result.fetchall()
            
            patterns = []
            for row in rows:
                pattern = PatternDefinition(
                    id=row.id,
                    name=row.name,
                    short_description=row.short_description,
                    long_description=row.long_description,
                    basic_logic_description=row.basic_logic_description,
                    code_reference=row.code_reference,
                    category=row.category,
                    enabled=row.enabled,
                    display_order=row.display_order,
                    confidence_threshold=float(row.confidence_threshold),
                    risk_level=row.risk_level,
                    typical_success_rate=float(row.typical_success_rate) if row.typical_success_rate else None,
                    created_date=row.created_date,
                    updated_date=row.updated_date,
                    created_by=row.created_by
                )
                patterns.append(pattern)
            
            # Update cache
            self._enabled_patterns_cache = patterns
            self._enabled_cache_timestamp = time.time()
            
            self.service_stats['successful_queries'] += 1
            self._record_query_time(start_time)
            
            logger.info(f"PATTERN-REGISTRY: Loaded {len(patterns)} enabled patterns")
            return patterns
            
        except Exception as e:
            self.service_stats['failed_queries'] += 1
            logger.error(f"PATTERN-REGISTRY: Failed to get enabled patterns: {e}")
            return []
    
    def get_all_patterns(self) -> List[PatternDefinition]:
        """
        Get all patterns (enabled and disabled) for admin use.
        
        Returns:
            List[PatternDefinition]: List of all patterns ordered by display_order
        """
        start_time = time.time()
        self.service_stats['total_requests'] += 1
        
        try:
            # Check cache first
            if self._patterns_cache and self._is_cache_valid(self._cache_timestamp):
                self.service_stats['cache_hits'] += 1
                return self._patterns_cache
            
            self.service_stats['cache_misses'] += 1
            
            if not self.is_flask_context_available():
                logger.error("PATTERN-REGISTRY: No Flask context available for database query")
                return []
            
            from src.infrastructure.database import db
            
            query = text("""
                SELECT id, name, short_description, long_description, basic_logic_description,
                       code_reference, category, enabled, display_order, confidence_threshold,
                       risk_level, typical_success_rate, created_date, updated_date, created_by
                FROM pattern_definitions 
                ORDER BY display_order, name
            """)
            
            result = db.session.execute(query)
            rows = result.fetchall()
            
            patterns = []
            for row in rows:
                pattern = PatternDefinition(
                    id=row.id,
                    name=row.name,
                    short_description=row.short_description,
                    long_description=row.long_description,
                    basic_logic_description=row.basic_logic_description,
                    code_reference=row.code_reference,
                    category=row.category,
                    enabled=row.enabled,
                    display_order=row.display_order,
                    confidence_threshold=float(row.confidence_threshold),
                    risk_level=row.risk_level,
                    typical_success_rate=float(row.typical_success_rate) if row.typical_success_rate else None,
                    created_date=row.created_date,
                    updated_date=row.updated_date,
                    created_by=row.created_by
                )
                patterns.append(pattern)
            
            # Update cache
            self._patterns_cache = patterns
            self._cache_timestamp = time.time()
            
            self.service_stats['successful_queries'] += 1
            self._record_query_time(start_time)
            
            logger.info(f"PATTERN-REGISTRY: Loaded {len(patterns)} total patterns")
            return patterns
            
        except Exception as e:
            self.service_stats['failed_queries'] += 1
            logger.error(f"PATTERN-REGISTRY: Failed to get all patterns: {e}")
            return []
    
    def get_pattern_by_name(self, name: str) -> Optional[PatternDefinition]:
        """
        Get specific pattern configuration by name.
        
        Args:
            name: Pattern name to lookup
            
        Returns:
            PatternDefinition or None if not found
        """
        start_time = time.time()
        self.service_stats['total_requests'] += 1
        
        try:
            if not self.is_flask_context_available():
                logger.error("PATTERN-REGISTRY: No Flask context available for database query")
                return None
            
            from src.infrastructure.database import db
            
            query = text("""
                SELECT id, name, short_description, long_description, basic_logic_description,
                       code_reference, category, enabled, display_order, confidence_threshold,
                       risk_level, typical_success_rate, created_date, updated_date, created_by
                FROM pattern_definitions 
                WHERE name = :name
            """)
            
            result = db.session.execute(query, {'name': name})
            row = result.fetchone()
            
            if not row:
                self.service_stats['successful_queries'] += 1
                return None
            
            pattern = PatternDefinition(
                id=row.id,
                name=row.name,
                short_description=row.short_description,
                long_description=row.long_description,
                basic_logic_description=row.basic_logic_description,
                code_reference=row.code_reference,
                category=row.category,
                enabled=row.enabled,
                display_order=row.display_order,
                confidence_threshold=float(row.confidence_threshold),
                risk_level=row.risk_level,
                typical_success_rate=float(row.typical_success_rate) if row.typical_success_rate else None,
                created_date=row.created_date,
                updated_date=row.updated_date,
                created_by=row.created_by
            )
            
            self.service_stats['successful_queries'] += 1
            self._record_query_time(start_time)
            
            logger.debug(f"PATTERN-REGISTRY: Found pattern {name}")
            return pattern
            
        except Exception as e:
            self.service_stats['failed_queries'] += 1
            logger.error(f"PATTERN-REGISTRY: Failed to get pattern {name}: {e}")
            return None
    
    def update_pattern_status(self, pattern_id: int, enabled: bool) -> bool:
        """
        Enable/disable pattern dynamically.
        
        Args:
            pattern_id: Pattern ID to update
            enabled: New enabled status
            
        Returns:
            bool: True if successful, False otherwise
        """
        start_time = time.time()
        self.service_stats['total_requests'] += 1
        
        try:
            if not self.is_flask_context_available():
                logger.error("PATTERN-REGISTRY: No Flask context available for database query")
                return False
            
            from src.infrastructure.database import db
            
            query = text("""
                UPDATE pattern_definitions 
                SET enabled = :enabled, updated_date = CURRENT_TIMESTAMP
                WHERE id = :pattern_id
            """)
            
            result = db.session.execute(query, {
                'pattern_id': pattern_id,
                'enabled': enabled
            })
            
            db.session.commit()
            
            # Invalidate cache
            self._patterns_cache = None
            self._enabled_patterns_cache = None
            
            self.service_stats['successful_queries'] += 1
            self._record_query_time(start_time)
            
            logger.info(f"PATTERN-REGISTRY: Updated pattern {pattern_id} enabled={enabled}")
            return True
            
        except Exception as e:
            self.service_stats['failed_queries'] += 1
            logger.error(f"PATTERN-REGISTRY: Failed to update pattern {pattern_id}: {e}")
            try:
                db.session.rollback()
            except:
                pass
            return False
    
    def toggle_pattern_by_name(self, name: str) -> bool:
        """
        Toggle pattern enabled status by name.
        
        Args:
            name: Pattern name to toggle
            
        Returns:
            bool: True if successful, False otherwise
        """
        start_time = time.time()
        self.service_stats['total_requests'] += 1
        
        try:
            if not self.is_flask_context_available():
                logger.error("PATTERN-REGISTRY: No Flask context available for database query")
                return False
            
            from src.infrastructure.database import db
            
            # Use the database function
            query = text("SELECT toggle_pattern_enabled(:name)")
            result = db.session.execute(query, {'name': name})
            success = result.scalar()
            
            db.session.commit()
            
            if success:
                # Invalidate cache
                self._patterns_cache = None
                self._enabled_patterns_cache = None
                
                self.service_stats['successful_queries'] += 1
                self._record_query_time(start_time)
                
                logger.info(f"PATTERN-REGISTRY: Toggled pattern {name}")
                return True
            else:
                logger.warning(f"PATTERN-REGISTRY: Pattern {name} not found for toggle")
                return False
                
        except Exception as e:
            self.service_stats['failed_queries'] += 1
            logger.error(f"PATTERN-REGISTRY: Failed to toggle pattern {name}: {e}")
            try:
                db.session.rollback()
            except:
                pass
            return False
    
    def calculate_success_rates(self, pattern_id: int, days: int = 30) -> Dict[str, Any]:
        """
        Calculate real success rates from detection history.
        
        Args:
            pattern_id: Pattern ID to analyze
            days: Number of days to look back
            
        Returns:
            dict: Success rate statistics
        """
        start_time = time.time()
        self.service_stats['total_requests'] += 1
        
        try:
            if not self.is_flask_context_available():
                logger.error("PATTERN-REGISTRY: No Flask context available for database query")
                return {}
            
            from src.infrastructure.database import db
            
            query = text("""
                SELECT 
                    pd.name,
                    COUNT(det.id) as total_detections,
                    COUNT(CASE WHEN det.outcome_1d > 0 THEN 1 END) as positive_1d,
                    COUNT(CASE WHEN det.outcome_5d > 0 THEN 1 END) as positive_5d,
                    COUNT(CASE WHEN det.outcome_30d > 0 THEN 1 END) as positive_30d,
                    CASE 
                        WHEN COUNT(CASE WHEN det.outcome_1d IS NOT NULL THEN 1 END) > 0 
                        THEN ROUND((COUNT(CASE WHEN det.outcome_1d > 0 THEN 1 END) * 100.0 / COUNT(CASE WHEN det.outcome_1d IS NOT NULL THEN 1 END)), 2)
                        ELSE NULL 
                    END as success_rate_1d,
                    AVG(det.confidence) as avg_confidence
                FROM pattern_definitions pd
                LEFT JOIN pattern_detections det ON pd.id = det.pattern_id
                    AND det.detected_at >= CURRENT_TIMESTAMP - INTERVAL '1 day' * :days
                WHERE pd.id = :pattern_id
                GROUP BY pd.id, pd.name
            """)
            
            result = db.session.execute(query, {
                'pattern_id': pattern_id,
                'days': days
            })
            
            row = result.fetchone()
            
            if not row:
                return {}
            
            success_data = {
                'pattern_name': row.name,
                'total_detections': row.total_detections,
                'positive_1d': row.positive_1d,
                'positive_5d': row.positive_5d,
                'positive_30d': row.positive_30d,
                'success_rate_1d': float(row.success_rate_1d) if row.success_rate_1d else None,
                'avg_confidence': float(row.avg_confidence) if row.avg_confidence else None,
                'days_analyzed': days
            }
            
            self.service_stats['successful_queries'] += 1
            self._record_query_time(start_time)
            
            return success_data
            
        except Exception as e:
            self.service_stats['failed_queries'] += 1
            logger.error(f"PATTERN-REGISTRY: Failed to calculate success rates for pattern {pattern_id}: {e}")
            return {}
    
    def get_pattern_distribution(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get pattern distribution for analytics dashboard.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            List[Dict]: Pattern distribution data
        """
        start_time = time.time()
        self.service_stats['total_requests'] += 1
        
        try:
            if not self.is_flask_context_available():
                logger.error("PATTERN-REGISTRY: No Flask context available for database query")
                return []
            
            from src.infrastructure.database import db
            
            query = text("SELECT * FROM get_pattern_distribution(:days)")
            result = db.session.execute(query, {'days': days})
            rows = result.fetchall()
            
            distribution = []
            for row in rows:
                distribution.append({
                    'pattern_name': row.pattern_name,
                    'detection_count': row.detection_count,
                    'percentage': float(row.percentage)
                })
            
            self.service_stats['successful_queries'] += 1
            self._record_query_time(start_time)
            
            return distribution
            
        except Exception as e:
            self.service_stats['failed_queries'] += 1
            logger.error(f"PATTERN-REGISTRY: Failed to get pattern distribution: {e}")
            return []
    
    def get_service_stats(self) -> Dict[str, Any]:
        """Get service performance statistics."""
        return self.service_stats.copy()
    
    def clear_cache(self):
        """Clear all cached data to force refresh."""
        self._patterns_cache = None
        self._enabled_patterns_cache = None
        self._cache_timestamp = 0
        self._enabled_cache_timestamp = 0
        logger.info("PATTERN-REGISTRY: Cache cleared")

# Global instance for use throughout the application
pattern_registry = PatternRegistryService()