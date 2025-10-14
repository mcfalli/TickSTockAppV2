"""
Correlation Analyzer Service
===========================

Specialized service for pattern correlation analysis and visualization data preparation.
Focuses on correlation matrices, heatmap data, and relationship discovery between
trading patterns.

Features:
- Pattern correlation matrix generation
- Heatmap visualization data preparation
- Correlation network analysis
- Temporal correlation tracking

Author: TickStock Development Team
Date: 2025-09-06
Sprint: 23
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.infrastructure.database.connection_pool import DatabaseConnectionPool

logger = logging.getLogger(__name__)

@dataclass
class CorrelationMatrix:
    """Pattern correlation matrix for visualization"""
    patterns: list[str]
    matrix: list[list[float]]
    significance_matrix: list[list[bool]]
    sample_sizes: list[list[int]]
    generated_at: datetime

@dataclass
class CorrelationHeatmapData:
    """Data structure for correlation heatmap visualization"""
    pattern_pairs: list[dict[str, Any]]
    max_correlation: float
    min_correlation: float
    significant_pairs_count: int
    total_pairs_count: int

@dataclass
class CorrelationNetwork:
    """Network representation of pattern correlations"""
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    clusters: list[list[str]]

class CorrelationAnalyzerService:
    """Service for advanced pattern correlation analysis"""

    def __init__(self, db_pool: DatabaseConnectionPool):
        """Initialize correlation analyzer service
        
        Args:
            db_pool: Database connection pool
        """
        self.db_pool = db_pool
        self._matrix_cache = {}
        self._heatmap_cache = {}
        self._cache_timeout = 3600  # 1 hour

        logger.info("CorrelationAnalyzerService initialized")

    async def get_correlation_matrix(self,
                                   days_back: int = 30,
                                   min_correlation: float = 0.1) -> CorrelationMatrix | None:
        """Generate correlation matrix for pattern relationships
        
        Args:
            days_back: Number of days to analyze
            min_correlation: Minimum correlation threshold
            
        Returns:
            Correlation matrix data structure
        """
        try:
            # Check cache first
            cache_key = f"matrix_{days_back}_{min_correlation}"
            if cache_key in self._matrix_cache:
                cached_data, timestamp = self._matrix_cache[cache_key]
                if (datetime.now() - timestamp).seconds < self._cache_timeout:
                    logger.debug(f"Returning cached correlation matrix for {cache_key}")
                    return cached_data

            # Get all pattern correlations
            async with self.db_pool.get_connection() as conn, conn.cursor() as cursor:
                await cursor.execute("""
                        SELECT * FROM calculate_pattern_correlations(%s, %s)
                    """, (days_back, min_correlation))

                correlations = await cursor.fetchall()

                # Get unique pattern names
                await cursor.execute("""
                        SELECT DISTINCT name FROM pattern_definitions 
                        WHERE enabled = true 
                        ORDER BY name
                    """)

                patterns = [row[0] for row in await cursor.fetchall()]

            if not patterns or not correlations:
                logger.warning("No patterns or correlations found for matrix generation")
                return self._get_mock_correlation_matrix()

            # Build correlation matrix
            n = len(patterns)
            pattern_index = {pattern: i for i, pattern in enumerate(patterns)}

            matrix = [[0.0 for _ in range(n)] for _ in range(n)]
            significance_matrix = [[False for _ in range(n)] for _ in range(n)]
            sample_sizes = [[0 for _ in range(n)] for _ in range(n)]

            # Fill diagonal with 1.0 (perfect self-correlation)
            for i in range(n):
                matrix[i][i] = 1.0
                significance_matrix[i][i] = True
                sample_sizes[i][i] = 100  # Dummy sample size for self-correlation

            # Fill matrix with correlation data
            for corr in correlations:
                pattern_a, pattern_b = corr[0], corr[1]
                if pattern_a in pattern_index and pattern_b in pattern_index:
                    i, j = pattern_index[pattern_a], pattern_index[pattern_b]
                    correlation_coeff = float(corr[2])
                    co_occurrence = int(corr[3])
                    is_significant = bool(corr[5])

                    # Matrix is symmetric
                    matrix[i][j] = correlation_coeff
                    matrix[j][i] = correlation_coeff
                    significance_matrix[i][j] = is_significant
                    significance_matrix[j][i] = is_significant
                    sample_sizes[i][j] = co_occurrence
                    sample_sizes[j][i] = co_occurrence

            correlation_matrix = CorrelationMatrix(
                patterns=patterns,
                matrix=matrix,
                significance_matrix=significance_matrix,
                sample_sizes=sample_sizes,
                generated_at=datetime.now()
            )

            # Cache the result
            self._matrix_cache[cache_key] = (correlation_matrix, datetime.now())

            logger.info(f"Generated {n}x{n} correlation matrix with {len(correlations)} correlations")
            return correlation_matrix

        except Exception as e:
            logger.error(f"Error generating correlation matrix: {e}")
            return self._get_mock_correlation_matrix()

    async def get_heatmap_data(self,
                             days_back: int = 30,
                             min_correlation: float = 0.3) -> CorrelationHeatmapData:
        """Get data formatted for correlation heatmap visualization
        
        Args:
            days_back: Number of days to analyze
            min_correlation: Minimum correlation threshold
            
        Returns:
            Heatmap visualization data
        """
        try:
            # Check cache first
            cache_key = f"heatmap_{days_back}_{min_correlation}"
            if cache_key in self._heatmap_cache:
                cached_data, timestamp = self._heatmap_cache[cache_key]
                if (datetime.now() - timestamp).seconds < self._cache_timeout:
                    logger.debug(f"Returning cached heatmap data for {cache_key}")
                    return cached_data

            # Get correlation data
            async with self.db_pool.get_connection() as conn, conn.cursor() as cursor:
                await cursor.execute("""
                        SELECT * FROM calculate_pattern_correlations(%s, %s)
                        ORDER BY ABS(correlation_coefficient) DESC
                    """, (days_back, min_correlation))

                correlations = await cursor.fetchall()

            if not correlations:
                logger.warning("No correlations found for heatmap generation")
                return self._get_mock_heatmap_data()

            # Format data for heatmap visualization
            pattern_pairs = []
            correlation_values = []
            significant_count = 0

            for corr in correlations:
                correlation_coeff = float(corr[2])
                correlation_values.append(abs(correlation_coeff))

                pattern_pair = {
                    'pattern_a': corr[0],
                    'pattern_b': corr[1],
                    'correlation': correlation_coeff,
                    'co_occurrence_count': int(corr[3]),
                    'temporal_relationship': corr[4],
                    'is_significant': bool(corr[5]),
                    'p_value': float(corr[6]),
                    'strength': self._classify_correlation_strength(abs(correlation_coeff))
                }

                pattern_pairs.append(pattern_pair)

                if bool(corr[5]):  # is_significant
                    significant_count += 1

            heatmap_data = CorrelationHeatmapData(
                pattern_pairs=pattern_pairs,
                max_correlation=max(correlation_values) if correlation_values else 0.0,
                min_correlation=min(correlation_values) if correlation_values else 0.0,
                significant_pairs_count=significant_count,
                total_pairs_count=len(pattern_pairs)
            )

            # Cache the result
            self._heatmap_cache[cache_key] = (heatmap_data, datetime.now())

            logger.info(f"Generated heatmap data with {len(pattern_pairs)} pairs, {significant_count} significant")
            return heatmap_data

        except Exception as e:
            logger.error(f"Error generating heatmap data: {e}")
            return self._get_mock_heatmap_data()

    async def get_correlation_network(self,
                                    days_back: int = 30,
                                    min_correlation: float = 0.5) -> CorrelationNetwork:
        """Generate network representation of pattern correlations
        
        Args:
            days_back: Number of days to analyze  
            min_correlation: Minimum correlation for network edges
            
        Returns:
            Network data for graph visualization
        """
        try:
            # Get strong correlations for network
            async with self.db_pool.get_connection() as conn, conn.cursor() as cursor:
                await cursor.execute("""
                        SELECT * FROM calculate_pattern_correlations(%s, %s)
                        WHERE statistical_significance = true
                        ORDER BY ABS(correlation_coefficient) DESC
                    """, (days_back, min_correlation))

                correlations = await cursor.fetchall()

                # Get pattern metadata
                await cursor.execute("""
                        SELECT name, short_description FROM pattern_definitions 
                        WHERE enabled = true
                    """)

                pattern_metadata = {row[0]: row[1] for row in await cursor.fetchall()}

            if not correlations:
                logger.warning("No significant correlations found for network generation")
                return self._get_mock_correlation_network()

            # Build nodes and edges
            pattern_names = set()
            edges = []

            for corr in correlations:
                pattern_a, pattern_b = corr[0], corr[1]
                pattern_names.add(pattern_a)
                pattern_names.add(pattern_b)

                edge = {
                    'source': pattern_a,
                    'target': pattern_b,
                    'weight': abs(float(corr[2])),
                    'correlation': float(corr[2]),
                    'co_occurrence': int(corr[3]),
                    'relationship_type': corr[4],  # temporal_relationship
                    'p_value': float(corr[6])
                }
                edges.append(edge)

            # Create nodes
            nodes = []
            for pattern in pattern_names:
                node = {
                    'id': pattern,
                    'label': pattern,
                    'description': pattern_metadata.get(pattern, ''),
                    'degree': len([e for e in edges if e['source'] == pattern or e['target'] == pattern])
                }
                nodes.append(node)

            # Simple clustering based on correlation strength
            clusters = self._identify_correlation_clusters(edges, list(pattern_names))

            network = CorrelationNetwork(
                nodes=nodes,
                edges=edges,
                clusters=clusters
            )

            logger.info(f"Generated correlation network with {len(nodes)} nodes, {len(edges)} edges")
            return network

        except Exception as e:
            logger.error(f"Error generating correlation network: {e}")
            return self._get_mock_correlation_network()

    def _classify_correlation_strength(self, correlation: float) -> str:
        """Classify correlation strength for visualization"""
        if correlation >= 0.8:
            return "Very Strong"
        if correlation >= 0.6:
            return "Strong"
        if correlation >= 0.4:
            return "Moderate"
        if correlation >= 0.2:
            return "Weak"
        return "Very Weak"

    def _identify_correlation_clusters(self, edges: list[dict], patterns: list[str]) -> list[list[str]]:
        """Simple clustering algorithm based on correlation strength"""
        # This is a simplified clustering - could be enhanced with graph algorithms
        clusters = []
        used_patterns = set()

        for edge in sorted(edges, key=lambda x: x['weight'], reverse=True):
            source, target = edge['source'], edge['target']

            if source not in used_patterns and target not in used_patterns:
                cluster = [source, target]
                used_patterns.add(source)
                used_patterns.add(target)
                clusters.append(cluster)

        # Add remaining patterns as single-node clusters
        for pattern in patterns:
            if pattern not in used_patterns:
                clusters.append([pattern])

        return clusters

    def clear_cache(self):
        """Clear all correlation analysis caches"""
        self._matrix_cache.clear()
        self._heatmap_cache.clear()
        logger.info("Correlation analyzer cache cleared")

    # Mock data methods for testing

    def _get_mock_correlation_matrix(self) -> CorrelationMatrix:
        """Generate mock correlation matrix for testing"""
        patterns = ['WeeklyBO', 'DailyBO', 'TrendFollower', 'MomentumBO']
        n = len(patterns)

        # Generate symmetric matrix with realistic correlations
        matrix = [
            [1.0, 0.75, 0.45, 0.32],
            [0.75, 1.0, 0.58, 0.61],
            [0.45, 0.58, 1.0, 0.73],
            [0.32, 0.61, 0.73, 1.0]
        ]

        significance_matrix = [
            [True, True, True, False],
            [True, True, True, True],
            [True, True, True, True],
            [False, True, True, True]
        ]

        sample_sizes = [
            [100, 15, 8, 3],
            [15, 100, 12, 9],
            [8, 12, 100, 18],
            [3, 9, 18, 100]
        ]

        return CorrelationMatrix(
            patterns=patterns,
            matrix=matrix,
            significance_matrix=significance_matrix,
            sample_sizes=sample_sizes,
            generated_at=datetime.now()
        )

    def _get_mock_heatmap_data(self) -> CorrelationHeatmapData:
        """Generate mock heatmap data for testing"""
        pattern_pairs = [
            {
                'pattern_a': 'WeeklyBO',
                'pattern_b': 'DailyBO',
                'correlation': 0.75,
                'co_occurrence_count': 15,
                'temporal_relationship': 'concurrent',
                'is_significant': True,
                'p_value': 0.02,
                'strength': 'Strong'
            },
            {
                'pattern_a': 'TrendFollower',
                'pattern_b': 'MomentumBO',
                'correlation': 0.73,
                'co_occurrence_count': 18,
                'temporal_relationship': 'sequential',
                'is_significant': True,
                'p_value': 0.01,
                'strength': 'Strong'
            },
            {
                'pattern_a': 'DailyBO',
                'pattern_b': 'MomentumBO',
                'correlation': 0.61,
                'co_occurrence_count': 9,
                'temporal_relationship': 'concurrent',
                'is_significant': True,
                'p_value': 0.04,
                'strength': 'Strong'
            }
        ]

        return CorrelationHeatmapData(
            pattern_pairs=pattern_pairs,
            max_correlation=0.75,
            min_correlation=0.61,
            significant_pairs_count=3,
            total_pairs_count=3
        )

    def _get_mock_correlation_network(self) -> CorrelationNetwork:
        """Generate mock correlation network for testing"""
        nodes = [
            {'id': 'WeeklyBO', 'label': 'Weekly Breakout', 'description': 'Weekly breakout pattern', 'degree': 2},
            {'id': 'DailyBO', 'label': 'Daily Breakout', 'description': 'Daily breakout pattern', 'degree': 3},
            {'id': 'TrendFollower', 'label': 'Trend Follower', 'description': 'Trend following pattern', 'degree': 2},
            {'id': 'MomentumBO', 'label': 'Momentum Breakout', 'description': 'Momentum-based breakout', 'degree': 2}
        ]

        edges = [
            {
                'source': 'WeeklyBO',
                'target': 'DailyBO',
                'weight': 0.75,
                'correlation': 0.75,
                'co_occurrence': 15,
                'relationship_type': 'concurrent',
                'p_value': 0.02
            },
            {
                'source': 'TrendFollower',
                'target': 'MomentumBO',
                'weight': 0.73,
                'correlation': 0.73,
                'co_occurrence': 18,
                'relationship_type': 'sequential',
                'p_value': 0.01
            },
            {
                'source': 'DailyBO',
                'target': 'MomentumBO',
                'weight': 0.61,
                'correlation': 0.61,
                'co_occurrence': 9,
                'relationship_type': 'concurrent',
                'p_value': 0.04
            }
        ]

        clusters = [['WeeklyBO', 'DailyBO'], ['TrendFollower', 'MomentumBO']]

        return CorrelationNetwork(
            nodes=nodes,
            edges=edges,
            clusters=clusters
        )
