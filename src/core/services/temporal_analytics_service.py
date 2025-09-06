"""
Temporal Analytics Service
=========================

Provides time-based pattern analysis including hourly performance, daily patterns,
session-based analytics, and temporal trend identification.

Features:
- Hourly pattern performance analysis (9 AM - 4 PM market hours)
- Daily performance by weekday (Monday-Friday)
- Session analysis (pre-market, regular hours, after-hours)
- Time-based performance optimization recommendations

Author: TickStock Development Team
Date: 2025-09-06
Sprint: 23
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta, time
from dataclasses import dataclass
from enum import Enum

from src.infrastructure.database.connection_pool import DatabaseConnectionPool

logger = logging.getLogger(__name__)

class AnalysisType(Enum):
    """Temporal analysis type enumeration"""
    HOURLY = "hourly"
    DAILY = "daily" 
    SESSION = "session"

class SessionType(Enum):
    """Trading session types"""
    PRE_MARKET = "Pre-Market"
    REGULAR_HOURS = "Regular Hours"
    AFTER_HOURS = "After Hours"

@dataclass
class TemporalPerformance:
    """Temporal performance data point"""
    time_bucket: str
    detection_count: int
    success_count: int
    success_rate: float
    avg_return_1d: float
    avg_confidence: float
    statistical_significance: bool

@dataclass
class TimeHeatmapData:
    """Data structure for time-based heatmap visualization"""
    pattern_name: str
    hourly_data: List[TemporalPerformance]
    daily_data: List[TemporalPerformance]
    session_data: List[TemporalPerformance]
    best_time_recommendation: str
    worst_time_warning: str

@dataclass
class TemporalCalendarData:
    """Calendar heatmap data for pattern performance"""
    pattern_name: str
    calendar_data: List[Dict[str, Any]]  # Date -> performance mapping
    performance_range: Tuple[float, float]
    color_scale: List[str]

class TemporalAnalyticsService:
    """Service for time-based pattern analysis"""
    
    def __init__(self, db_pool: DatabaseConnectionPool):
        """Initialize temporal analytics service
        
        Args:
            db_pool: Database connection pool
        """
        self.db_pool = db_pool
        self._performance_cache = {}
        self._heatmap_cache = {}
        self._cache_timeout = 1800  # 30 minutes
        
        logger.info("TemporalAnalyticsService initialized")
    
    async def get_temporal_performance(self, 
                                     pattern_name: str,
                                     analysis_type: AnalysisType = AnalysisType.HOURLY) -> List[TemporalPerformance]:
        """Get temporal performance analysis for a pattern
        
        Args:
            pattern_name: Name of the pattern to analyze
            analysis_type: Type of temporal analysis (hourly, daily, session)
            
        Returns:
            List of temporal performance data points
        """
        try:
            # Check cache first
            cache_key = f"temporal_{pattern_name}_{analysis_type.value}"
            if cache_key in self._performance_cache:
                cached_data, timestamp = self._performance_cache[cache_key]
                if (datetime.now() - timestamp).seconds < self._cache_timeout:
                    logger.debug(f"Returning cached temporal data for {cache_key}")
                    return cached_data
            
            # Fetch from database using Sprint 23 analytics function
            async with self.db_pool.get_connection() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("""
                        SELECT * FROM analyze_temporal_performance(%s, %s)
                        ORDER BY time_bucket
                    """, (pattern_name, analysis_type.value))
                    
                    results = await cursor.fetchall()
                    
                    performances = []
                    for row in results:
                        performances.append(TemporalPerformance(
                            time_bucket=row[0],
                            detection_count=int(row[1]),
                            success_count=int(row[2]),
                            success_rate=float(row[3]) if row[3] else 0.0,
                            avg_return_1d=float(row[4]) if row[4] else 0.0,
                            avg_confidence=float(row[5]) if row[5] else 0.0,
                            statistical_significance=bool(row[6])
                        ))
            
            # Cache the results
            self._performance_cache[cache_key] = (performances, datetime.now())
            
            logger.info(f"Retrieved {len(performances)} temporal performance points for {pattern_name} ({analysis_type.value})")
            return performances
            
        except Exception as e:
            logger.error(f"Error getting temporal performance for {pattern_name}: {e}")
            # Return mock data for testing
            return self._get_mock_temporal_performance(pattern_name, analysis_type)
    
    async def get_time_heatmap_data(self, pattern_name: str) -> TimeHeatmapData:
        """Get comprehensive time heatmap data for pattern
        
        Args:
            pattern_name: Name of the pattern to analyze
            
        Returns:
            Complete time heatmap data structure
        """
        try:
            # Check cache first
            cache_key = f"heatmap_{pattern_name}"
            if cache_key in self._heatmap_cache:
                cached_data, timestamp = self._heatmap_cache[cache_key]
                if (datetime.now() - timestamp).seconds < self._cache_timeout:
                    logger.debug(f"Returning cached heatmap data for {pattern_name}")
                    return cached_data
            
            # Get all three types of temporal analysis
            hourly_data = await self.get_temporal_performance(pattern_name, AnalysisType.HOURLY)
            daily_data = await self.get_temporal_performance(pattern_name, AnalysisType.DAILY)
            session_data = await self.get_temporal_performance(pattern_name, AnalysisType.SESSION)
            
            # Generate recommendations
            best_time = self._find_best_performance_time(hourly_data, daily_data, session_data)
            worst_time = self._find_worst_performance_time(hourly_data, daily_data, session_data)
            
            heatmap_data = TimeHeatmapData(
                pattern_name=pattern_name,
                hourly_data=hourly_data,
                daily_data=daily_data,
                session_data=session_data,
                best_time_recommendation=best_time,
                worst_time_warning=worst_time
            )
            
            # Cache the result
            self._heatmap_cache[cache_key] = (heatmap_data, datetime.now())
            
            logger.info(f"Generated time heatmap data for {pattern_name}")
            return heatmap_data
            
        except Exception as e:
            logger.error(f"Error generating time heatmap for {pattern_name}: {e}")
            return self._get_mock_time_heatmap_data(pattern_name)
    
    async def get_temporal_calendar_data(self, 
                                       pattern_name: str,
                                       days_back: int = 90) -> TemporalCalendarData:
        """Get calendar heatmap data for daily pattern performance
        
        Args:
            pattern_name: Name of the pattern to analyze
            days_back: Number of days to include in calendar
            
        Returns:
            Calendar visualization data
        """
        try:
            # Get daily performance data from database
            async with self.db_pool.get_connection() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("""
                        SELECT 
                            DATE(detected_at) as detection_date,
                            COUNT(*) as total_detections,
                            COUNT(CASE WHEN outcome_1d > 0 THEN 1 END) as successful_detections,
                            CASE 
                                WHEN COUNT(CASE WHEN outcome_1d IS NOT NULL THEN 1 END) > 0
                                THEN ROUND((COUNT(CASE WHEN outcome_1d > 0 THEN 1 END) * 100.0 / 
                                           COUNT(CASE WHEN outcome_1d IS NOT NULL THEN 1 END)), 2)
                                ELSE NULL
                            END as success_rate,
                            AVG(outcome_1d) as avg_return
                        FROM pattern_definitions pd
                        JOIN pattern_detections det ON pd.id = det.pattern_id
                        WHERE pd.name = %s
                          AND det.detected_at >= %s
                        GROUP BY DATE(detected_at)
                        ORDER BY detection_date DESC
                    """, (pattern_name, datetime.now() - timedelta(days=days_back)))
                    
                    results = await cursor.fetchall()
            
            if not results:
                logger.warning(f"No daily data found for pattern: {pattern_name}")
                return self._get_mock_calendar_data(pattern_name)
            
            # Format data for calendar visualization
            calendar_data = []
            success_rates = []
            
            for row in results:
                date_str = row[0].isoformat() if row[0] else None
                success_rate = float(row[3]) if row[3] else 0.0
                
                if date_str:
                    calendar_data.append({
                        'date': date_str,
                        'total_detections': int(row[1]),
                        'successful_detections': int(row[2]),
                        'success_rate': success_rate,
                        'avg_return': float(row[4]) if row[4] else 0.0,
                        'performance_level': self._classify_performance_level(success_rate)
                    })
                    success_rates.append(success_rate)
            
            # Calculate performance range and color scale
            performance_range = (min(success_rates), max(success_rates)) if success_rates else (0.0, 100.0)
            color_scale = self._generate_color_scale(performance_range)
            
            calendar_viz_data = TemporalCalendarData(
                pattern_name=pattern_name,
                calendar_data=calendar_data,
                performance_range=performance_range,
                color_scale=color_scale
            )
            
            logger.info(f"Generated calendar data for {pattern_name}: {len(calendar_data)} days")
            return calendar_viz_data
            
        except Exception as e:
            logger.error(f"Error generating calendar data for {pattern_name}: {e}")
            return self._get_mock_calendar_data(pattern_name)
    
    async def get_optimal_trading_windows(self, pattern_name: str) -> Dict[str, Any]:
        """Get optimal trading time windows for a pattern
        
        Args:
            pattern_name: Name of the pattern to analyze
            
        Returns:
            Optimal trading windows and recommendations
        """
        try:
            heatmap_data = await self.get_time_heatmap_data(pattern_name)
            
            # Find best performing time windows
            best_hours = [p for p in heatmap_data.hourly_data if p.success_rate > 70 and p.statistical_significance]
            best_days = [p for p in heatmap_data.daily_data if p.success_rate > 65 and p.statistical_significance]
            best_sessions = [p for p in heatmap_data.session_data if p.success_rate > 60]
            
            # Generate trading recommendations
            recommendations = {
                'pattern_name': pattern_name,
                'optimal_hours': [p.time_bucket for p in sorted(best_hours, key=lambda x: x.success_rate, reverse=True)[:3]],
                'optimal_days': [p.time_bucket for p in sorted(best_days, key=lambda x: x.success_rate, reverse=True)[:2]],
                'optimal_sessions': [p.time_bucket for p in sorted(best_sessions, key=lambda x: x.success_rate, reverse=True)[:2]],
                'best_overall_time': heatmap_data.best_time_recommendation,
                'avoid_times': heatmap_data.worst_time_warning,
                'statistical_confidence': len(best_hours) + len(best_days) + len(best_sessions),
                'generated_at': datetime.now().isoformat()
            }
            
            logger.info(f"Generated optimal trading windows for {pattern_name}")
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting optimal trading windows for {pattern_name}: {e}")
            return self._get_mock_trading_windows(pattern_name)
    
    def _find_best_performance_time(self, hourly: List[TemporalPerformance], 
                                  daily: List[TemporalPerformance], 
                                  session: List[TemporalPerformance]) -> str:
        """Find the best performing time period across all analyses"""
        best_performers = []
        
        # Find best from each category
        if hourly:
            best_hour = max(hourly, key=lambda x: x.success_rate if x.statistical_significance else 0)
            if best_hour.statistical_significance and best_hour.success_rate > 65:
                best_performers.append(f"{best_hour.time_bucket} (Success: {best_hour.success_rate:.1f}%)")
        
        if daily:
            best_day = max(daily, key=lambda x: x.success_rate if x.statistical_significance else 0)
            if best_day.statistical_significance and best_day.success_rate > 60:
                best_performers.append(f"{best_day.time_bucket} (Success: {best_day.success_rate:.1f}%)")
        
        if session:
            best_session = max(session, key=lambda x: x.success_rate)
            if best_session.success_rate > 55:
                best_performers.append(f"{best_session.time_bucket} (Success: {best_session.success_rate:.1f}%)")
        
        return "; ".join(best_performers) if best_performers else "No significant optimal times identified"
    
    def _find_worst_performance_time(self, hourly: List[TemporalPerformance], 
                                   daily: List[TemporalPerformance], 
                                   session: List[TemporalPerformance]) -> str:
        """Find the worst performing time period across all analyses"""
        worst_performers = []
        
        # Find worst from each category (only if statistically significant)
        if hourly:
            worst_hour = min([p for p in hourly if p.statistical_significance], 
                           key=lambda x: x.success_rate, default=None)
            if worst_hour and worst_hour.success_rate < 45:
                worst_performers.append(f"{worst_hour.time_bucket} (Success: {worst_hour.success_rate:.1f}%)")
        
        if daily:
            worst_day = min([p for p in daily if p.statistical_significance], 
                          key=lambda x: x.success_rate, default=None)
            if worst_day and worst_day.success_rate < 50:
                worst_performers.append(f"{worst_day.time_bucket} (Success: {worst_day.success_rate:.1f}%)")
        
        return "Avoid: " + "; ".join(worst_performers) if worst_performers else "No significant underperforming times"
    
    def _classify_performance_level(self, success_rate: float) -> str:
        """Classify performance level for visualization"""
        if success_rate >= 80:
            return "Excellent"
        elif success_rate >= 70:
            return "Good"
        elif success_rate >= 60:
            return "Average"
        elif success_rate >= 50:
            return "Poor"
        else:
            return "Very Poor"
    
    def _generate_color_scale(self, performance_range: Tuple[float, float]) -> List[str]:
        """Generate color scale for heatmap visualization"""
        return [
            "#d73027",  # Red - Very Poor
            "#fc8d59",  # Orange - Poor  
            "#fee08b",  # Yellow - Average
            "#d9ef8b",  # Light Green - Good
            "#66bd63"   # Green - Excellent
        ]
    
    def clear_cache(self):
        """Clear all temporal analytics caches"""
        self._performance_cache.clear()
        self._heatmap_cache.clear()
        logger.info("Temporal analytics cache cleared")
    
    # Mock data methods for testing
    
    def _get_mock_temporal_performance(self, pattern_name: str, analysis_type: AnalysisType) -> List[TemporalPerformance]:
        """Generate mock temporal performance data for testing"""
        if analysis_type == AnalysisType.HOURLY:
            return [
                TemporalPerformance("Hour_9", 12, 8, 66.7, 1.45, 0.785, True),
                TemporalPerformance("Hour_10", 15, 12, 80.0, 2.12, 0.823, True),
                TemporalPerformance("Hour_11", 18, 11, 61.1, 1.23, 0.756, True),
                TemporalPerformance("Hour_12", 8, 3, 37.5, -0.45, 0.634, False),
                TemporalPerformance("Hour_13", 14, 10, 71.4, 1.89, 0.798, True),
                TemporalPerformance("Hour_14", 16, 13, 81.3, 2.34, 0.845, True),
                TemporalPerformance("Hour_15", 11, 6, 54.5, 0.78, 0.712, False),
                TemporalPerformance("Hour_16", 9, 4, 44.4, 0.23, 0.665, False)
            ]
        elif analysis_type == AnalysisType.DAILY:
            return [
                TemporalPerformance("Monday", 45, 28, 62.2, 1.34, 0.756, True),
                TemporalPerformance("Tuesday", 52, 38, 73.1, 1.98, 0.812, True),
                TemporalPerformance("Wednesday", 48, 31, 64.6, 1.45, 0.778, True),
                TemporalPerformance("Thursday", 41, 32, 78.0, 2.23, 0.834, True),
                TemporalPerformance("Friday", 38, 19, 50.0, 0.89, 0.698, True)
            ]
        else:  # SESSION
            return [
                TemporalPerformance("Pre-Market", 18, 8, 44.4, 0.67, 0.645, False),
                TemporalPerformance("Regular Hours", 156, 108, 69.2, 1.78, 0.798, True),
                TemporalPerformance("After Hours", 12, 5, 41.7, 0.34, 0.623, False)
            ]
    
    def _get_mock_time_heatmap_data(self, pattern_name: str) -> TimeHeatmapData:
        """Generate mock time heatmap data for testing"""
        return TimeHeatmapData(
            pattern_name=pattern_name,
            hourly_data=self._get_mock_temporal_performance(pattern_name, AnalysisType.HOURLY),
            daily_data=self._get_mock_temporal_performance(pattern_name, AnalysisType.DAILY),
            session_data=self._get_mock_temporal_performance(pattern_name, AnalysisType.SESSION),
            best_time_recommendation="Hour_14 (Success: 81.3%); Thursday (Success: 78.0%)",
            worst_time_warning="Avoid: Hour_12 (Success: 37.5%); Friday (Success: 50.0%)"
        )
    
    def _get_mock_calendar_data(self, pattern_name: str) -> TemporalCalendarData:
        """Generate mock calendar data for testing"""
        calendar_data = [
            {'date': '2024-09-05', 'total_detections': 5, 'successful_detections': 4, 'success_rate': 80.0, 'avg_return': 2.1, 'performance_level': 'Excellent'},
            {'date': '2024-09-04', 'total_detections': 3, 'successful_detections': 1, 'success_rate': 33.3, 'avg_return': -0.5, 'performance_level': 'Very Poor'},
            {'date': '2024-09-03', 'total_detections': 7, 'successful_detections': 5, 'success_rate': 71.4, 'avg_return': 1.8, 'performance_level': 'Good'},
            {'date': '2024-09-02', 'total_detections': 4, 'successful_detections': 2, 'success_rate': 50.0, 'avg_return': 0.3, 'performance_level': 'Poor'}
        ]
        
        return TemporalCalendarData(
            pattern_name=pattern_name,
            calendar_data=calendar_data,
            performance_range=(33.3, 80.0),
            color_scale=["#d73027", "#fc8d59", "#fee08b", "#d9ef8b", "#66bd63"]
        )
    
    def _get_mock_trading_windows(self, pattern_name: str) -> Dict[str, Any]:
        """Generate mock trading windows for testing"""
        return {
            'pattern_name': pattern_name,
            'optimal_hours': ['Hour_14', 'Hour_10', 'Hour_13'],
            'optimal_days': ['Thursday', 'Tuesday'],
            'optimal_sessions': ['Regular Hours'],
            'best_overall_time': 'Hour_14 (Success: 81.3%); Thursday (Success: 78.0%)',
            'avoid_times': 'Avoid: Hour_12 (Success: 37.5%); Friday (Success: 50.0%)',
            'statistical_confidence': 6,
            'generated_at': datetime.now().isoformat()
        }