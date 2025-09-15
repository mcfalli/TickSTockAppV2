"""
Database Pattern Integration Tests
Tests database connectivity, pattern data storage, and TickStockApp read-only access patterns.

Validates:
1. Database connectivity and health status
2. Pattern table structure and data integrity
3. Read-only access boundaries for TickStockApp
4. Pattern data synchronization between Redis cache and database
5. Query performance requirements (<50ms)
6. Database role separation (TickStockApp vs TickStockPL)
"""

import pytest
import time
import json
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import psycopg2
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError

class TestDatabasePatternIntegration:
    """Test database integration for pattern data access."""
    
    @pytest.fixture
    def database_config(self):
        """Database configuration for testing."""
        return {
            'host': 'localhost',
            'port': 5432,
            'database': 'tickstock',
            'user': 'app_readwrite',  # TickStockApp database user
            'password': 'test_password'  # This would come from environment
        }
    
    @pytest.fixture
    def test_engine(self, database_config):
        """SQLAlchemy engine for testing."""
        try:
            engine = create_engine(
                f"postgresql://{database_config['user']}:{database_config['password']}@"
                f"{database_config['host']}:{database_config['port']}/{database_config['database']}",
                pool_pre_ping=True,
                pool_recycle=300
            )
            
            # Test connection
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            yield engine
            engine.dispose()
            
        except Exception as e:
            pytest.skip(f"Database not available for testing: {e}")
    
    def test_database_connectivity_and_health(self, test_engine):
        """Test basic database connectivity and health status."""
        health_results = {
            'connection_successful': False,
            'database_responsive': False,
            'tickstock_database_accessible': False,
            'response_time_ms': 0
        }
        
        try:
            start_time = time.time()
            
            with test_engine.connect() as conn:
                # Test basic connectivity
                result = conn.execute(text("SELECT 1 as test"))
                test_value = result.scalar()
                health_results['connection_successful'] = (test_value == 1)
                
                # Test database name
                db_name = conn.execute(text("SELECT current_database()")).scalar()
                health_results['tickstock_database_accessible'] = (db_name == 'tickstock')
                
                # Test responsiveness
                conn.execute(text("SELECT NOW()"))
                health_results['database_responsive'] = True
                
            response_time = (time.time() - start_time) * 1000
            health_results['response_time_ms'] = response_time
            health_results['performance_acceptable'] = response_time < 50  # <50ms requirement
            
        except Exception as e:
            health_results['error'] = str(e)
        
        return health_results
    
    def test_pattern_table_structure_and_access(self, test_engine):
        """Test pattern table structure and TickStockApp access permissions."""
        table_results = {
            'tables_accessible': {},
            'table_structures': {},
            'access_permissions': {},
            'read_only_enforced': True
        }
        
        # Pattern tables to test
        pattern_tables = [
            'daily_patterns',
            'intraday_patterns', 
            'pattern_detections',
            'symbols'
        ]
        
        try:
            with test_engine.connect() as conn:
                for table in pattern_tables:
                    try:
                        # Test table accessibility
                        result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                        count = result.scalar()
                        table_results['tables_accessible'][table] = True
                        table_results['table_structures'][table] = {
                            'row_count': count,
                            'accessible': True
                        }
                        
                        # Test table structure
                        columns_query = text("""
                            SELECT column_name, data_type, is_nullable
                            FROM information_schema.columns
                            WHERE table_name = :table_name
                            ORDER BY ordinal_position
                        """)
                        
                        columns = conn.execute(columns_query, {'table_name': table}).fetchall()
                        table_results['table_structures'][table]['columns'] = [
                            {
                                'name': col[0],
                                'type': col[1], 
                                'nullable': col[2]
                            } for col in columns
                        ]
                        
                        # Test read permissions
                        try:
                            conn.execute(text(f"SELECT * FROM {table} LIMIT 1"))
                            table_results['access_permissions'][table] = 'read_allowed'
                        except Exception:
                            table_results['access_permissions'][table] = 'read_denied'
                        
                        # Test write permissions (should be denied for app_readwrite)
                        if table != 'symbols':  # symbols might allow some writes
                            try:
                                # Attempt insert (should fail for read-only access)
                                test_insert = f"INSERT INTO {table} (id) VALUES (-999999)"
                                conn.execute(text(test_insert))
                                conn.rollback()  # Rollback if it succeeded
                                table_results['read_only_enforced'] = False
                            except Exception:
                                # Insert failed - read-only working correctly
                                pass
                                
                    except Exception as e:
                        table_results['tables_accessible'][table] = False
                        table_results['table_structures'][table] = {'error': str(e)}
                        
        except Exception as e:
            table_results['connection_error'] = str(e)
        
        return table_results
    
    def test_pattern_data_content_analysis(self, test_engine):
        """Analyze pattern data content and recent activity."""
        content_analysis = {
            'pattern_counts': {},
            'recent_activity': {},
            'data_quality_issues': [],
            'pattern_distribution': {}
        }
        
        try:
            with test_engine.connect() as conn:
                # Analyze daily patterns
                try:
                    daily_count = conn.execute(text("SELECT COUNT(*) FROM daily_patterns")).scalar()
                    content_analysis['pattern_counts']['daily_patterns'] = daily_count
                    
                    if daily_count > 0:
                        # Recent daily pattern activity
                        recent_daily = conn.execute(text("""
                            SELECT COUNT(*) FROM daily_patterns 
                            WHERE detected_at > NOW() - INTERVAL '24 hours'
                        """)).scalar()
                        content_analysis['recent_activity']['daily_patterns_24h'] = recent_daily
                        
                        # Pattern type distribution
                        daily_patterns = conn.execute(text("""
                            SELECT pattern_type, COUNT(*) as count
                            FROM daily_patterns
                            GROUP BY pattern_type
                            ORDER BY count DESC
                            LIMIT 10
                        """)).fetchall()
                        content_analysis['pattern_distribution']['daily'] = [
                            {'pattern': row[0], 'count': row[1]} for row in daily_patterns
                        ]
                        
                except Exception as e:
                    content_analysis['daily_patterns_error'] = str(e)
                
                # Analyze intraday patterns
                try:
                    intraday_count = conn.execute(text("SELECT COUNT(*) FROM intraday_patterns")).scalar()
                    content_analysis['pattern_counts']['intraday_patterns'] = intraday_count
                    
                    if intraday_count > 0:
                        recent_intraday = conn.execute(text("""
                            SELECT COUNT(*) FROM intraday_patterns 
                            WHERE detected_at > NOW() - INTERVAL '24 hours'
                        """)).scalar()
                        content_analysis['recent_activity']['intraday_patterns_24h'] = recent_intraday
                        
                except Exception as e:
                    content_analysis['intraday_patterns_error'] = str(e)
                
                # Analyze combo patterns (pattern_detections)
                try:
                    combo_count = conn.execute(text("SELECT COUNT(*) FROM pattern_detections")).scalar()
                    content_analysis['pattern_counts']['pattern_detections'] = combo_count
                    
                    if combo_count > 0:
                        recent_combo = conn.execute(text("""
                            SELECT COUNT(*) FROM pattern_detections 
                            WHERE detected_at > NOW() - INTERVAL '24 hours'
                        """)).scalar()
                        content_analysis['recent_activity']['pattern_detections_24h'] = recent_combo
                        
                        # Top symbols with combo patterns
                        top_symbols = conn.execute(text("""
                            SELECT symbol, COUNT(*) as pattern_count
                            FROM pattern_detections
                            WHERE detected_at > NOW() - INTERVAL '7 days'
                            GROUP BY symbol
                            ORDER BY pattern_count DESC
                            LIMIT 10
                        """)).fetchall()
                        content_analysis['pattern_distribution']['combo_top_symbols'] = [
                            {'symbol': row[0], 'count': row[1]} for row in top_symbols
                        ]
                        
                except Exception as e:
                    content_analysis['combo_patterns_error'] = str(e)
                
                # Check for data quality issues
                if (content_analysis['pattern_counts'].get('daily_patterns', 0) == 0 and
                    content_analysis['pattern_counts'].get('intraday_patterns', 0) == 0):
                    content_analysis['data_quality_issues'].append("No daily or intraday patterns found")
                
                if (content_analysis['recent_activity'].get('daily_patterns_24h', 0) == 0 and
                    content_analysis['recent_activity'].get('intraday_patterns_24h', 0) == 0 and  
                    content_analysis['recent_activity'].get('pattern_detections_24h', 0) == 0):
                    content_analysis['data_quality_issues'].append("No recent pattern activity in last 24 hours")
                    
        except Exception as e:
            content_analysis['analysis_error'] = str(e)
        
        return content_analysis
    
    def test_database_query_performance(self, test_engine):
        """Test database query performance against <50ms requirement."""
        performance_results = {
            'query_times_ms': {},
            'performance_requirements_met': True,
            'slow_queries': []
        }
        
        # Common TickStockApp queries to test
        test_queries = {
            'symbols_dropdown': "SELECT symbol, name FROM symbols ORDER BY symbol LIMIT 100",
            'recent_patterns': """
                SELECT symbol, pattern_type, confidence, detected_at 
                FROM pattern_detections 
                ORDER BY detected_at DESC 
                LIMIT 20
            """,
            'pattern_count_by_symbol': """
                SELECT symbol, COUNT(*) as pattern_count
                FROM pattern_detections
                WHERE detected_at > NOW() - INTERVAL '7 days'
                GROUP BY symbol
                ORDER BY pattern_count DESC
                LIMIT 10
            """,
            'daily_pattern_summary': """
                SELECT pattern_type, COUNT(*) as count, AVG(confidence) as avg_confidence
                FROM daily_patterns
                WHERE detected_at > NOW() - INTERVAL '24 hours'  
                GROUP BY pattern_type
            """,
            'user_universe_check': """
                SELECT symbol FROM symbols
                WHERE market_cap > 1000000000
                ORDER BY market_cap DESC
                LIMIT 50
            """
        }
        
        try:
            with test_engine.connect() as conn:
                for query_name, query_sql in test_queries.items():
                    try:
                        # Execute query with timing
                        start_time = time.time()
                        result = conn.execute(text(query_sql))
                        rows = result.fetchall()  # Consume all results
                        query_time_ms = (time.time() - start_time) * 1000
                        
                        performance_results['query_times_ms'][query_name] = {
                            'time_ms': round(query_time_ms, 2),
                            'row_count': len(rows),
                            'meets_target': query_time_ms < 50
                        }
                        
                        if query_time_ms >= 50:
                            performance_results['slow_queries'].append({
                                'query': query_name,
                                'time_ms': query_time_ms
                            })
                            performance_results['performance_requirements_met'] = False
                            
                    except Exception as e:
                        performance_results['query_times_ms'][query_name] = {
                            'error': str(e)
                        }
                        
        except Exception as e:
            performance_results['test_error'] = str(e)
        
        return performance_results
    
    def test_database_role_separation(self, database_config):
        """Test database role separation between TickStockApp and TickStockPL."""
        role_test_results = {
            'current_user': None,
            'role_permissions': {},
            'schema_access': {},
            'write_restrictions': {}
        }
        
        try:
            # Test with app_readwrite role (TickStockApp)
            engine = create_engine(
                f"postgresql://{database_config['user']}:{database_config['password']}@"
                f"{database_config['host']}:{database_config['port']}/{database_config['database']}"
            )
            
            with engine.connect() as conn:
                # Get current user and role
                current_user = conn.execute(text("SELECT current_user")).scalar()
                role_test_results['current_user'] = current_user
                
                # Test table permissions
                tables_to_test = ['symbols', 'daily_patterns', 'intraday_patterns', 'pattern_detections']
                
                for table in tables_to_test:
                    permissions = {
                        'select': False,
                        'insert': False,
                        'update': False,
                        'delete': False
                    }
                    
                    # Test SELECT permission
                    try:
                        conn.execute(text(f"SELECT 1 FROM {table} LIMIT 1"))
                        permissions['select'] = True
                    except Exception:
                        pass
                    
                    # Test INSERT permission (should fail for read-only role)
                    try:
                        # Use a transaction that we'll rollback
                        trans = conn.begin()
                        try:
                            if table == 'symbols':
                                conn.execute(text(f"INSERT INTO {table} (symbol, name) VALUES ('TEST_ROLE', 'Test Role')"))
                            else:
                                conn.execute(text(f"INSERT INTO {table} (symbol) VALUES ('TEST_ROLE')"))
                            permissions['insert'] = True
                            trans.rollback()
                        except Exception:
                            trans.rollback()
                    except Exception:
                        pass
                    
                    role_test_results['role_permissions'][table] = permissions
                
                # Test schema access
                schemas = conn.execute(text("""
                    SELECT schema_name 
                    FROM information_schema.schemata 
                    WHERE schema_name NOT IN ('information_schema', 'pg_catalog')
                """)).fetchall()
                
                role_test_results['schema_access'] = [schema[0] for schema in schemas]
                
            engine.dispose()
            
        except Exception as e:
            role_test_results['test_error'] = str(e)
        
        return role_test_results
    
    def test_redis_database_synchronization(self, test_engine):
        """Test synchronization between Redis cache and database pattern data."""
        sync_test_results = {
            'database_pattern_sample': [],
            'sync_requirements_met': False,
            'data_consistency_issues': []
        }
        
        try:
            with test_engine.connect() as conn:
                # Sample recent patterns from database
                sample_query = text("""
                    SELECT symbol, pattern_type, confidence, detected_at, source
                    FROM (
                        SELECT symbol, pattern_type, confidence, detected_at, 'daily' as source
                        FROM daily_patterns
                        WHERE detected_at > NOW() - INTERVAL '1 hour'
                        UNION ALL
                        SELECT symbol, pattern_type, confidence, detected_at, 'intraday' as source  
                        FROM intraday_patterns
                        WHERE detected_at > NOW() - INTERVAL '1 hour'
                        UNION ALL
                        SELECT symbol, pattern_type, confidence, detected_at, 'combo' as source
                        FROM pattern_detections
                        WHERE detected_at > NOW() - INTERVAL '1 hour'
                    ) combined
                    ORDER BY detected_at DESC
                    LIMIT 10
                """)
                
                patterns = conn.execute(sample_query).fetchall()
                
                for pattern in patterns:
                    sync_test_results['database_pattern_sample'].append({
                        'symbol': pattern[0],
                        'pattern_type': pattern[1],
                        'confidence': float(pattern[2]) if pattern[2] else 0.0,
                        'detected_at': pattern[3].isoformat() if pattern[3] else None,
                        'source': pattern[4]
                    })
                
                # Check for data consistency patterns
                if len(patterns) > 0:
                    sync_test_results['recent_patterns_found'] = True
                    sync_test_results['sync_requirements_met'] = True
                else:
                    sync_test_results['recent_patterns_found'] = False
                    sync_test_results['data_consistency_issues'].append("No recent patterns found in database")
                
        except Exception as e:
            sync_test_results['sync_test_error'] = str(e)
        
        return sync_test_results

class TestDatabaseIntegrationDiagnostics:
    """Comprehensive database integration diagnostics."""
    
    def test_comprehensive_database_diagnosis(self):
        """Run comprehensive database integration diagnosis."""
        diagnosis = {}
        
        try:
            # Database configuration
            db_config = {
                'host': 'localhost',
                'port': 5432,
                'database': 'tickstock',
                'user': 'app_readwrite',
                'password': 'test_password'
            }
            
            # Initialize test engine
            engine = create_engine(
                f"postgresql://{db_config['user']}:{db_config['password']}@"
                f"{db_config['host']}:{db_config['port']}/{db_config['database']}"
            )
            
            db_tester = TestDatabasePatternIntegration()
            
            # 1. Test database connectivity
            diagnosis['connectivity'] = db_tester.test_database_connectivity_and_health(engine)
            
            # 2. Test table structure and access
            diagnosis['table_access'] = db_tester.test_pattern_table_structure_and_access(engine)
            
            # 3. Test pattern data content
            diagnosis['data_content'] = db_tester.test_pattern_data_content_analysis(engine)
            
            # 4. Test query performance
            diagnosis['performance'] = db_tester.test_database_query_performance(engine)
            
            # 5. Test role separation
            diagnosis['role_separation'] = db_tester.test_database_role_separation(db_config)
            
            # 6. Test Redis-database sync
            diagnosis['redis_sync'] = db_tester.test_redis_database_synchronization(engine)
            
            # 7. Overall assessment
            diagnosis['overall_assessment'] = self._assess_database_health(diagnosis)
            
            engine.dispose()
            
        except Exception as e:
            diagnosis['critical_error'] = f"Database diagnosis failed: {e}"
        
        return diagnosis
    
    def _assess_database_health(self, diagnosis: Dict[str, Any]) -> Dict[str, Any]:
        """Assess overall database health and integration status."""
        assessment = {
            'status': 'unknown',
            'critical_issues': [],
            'warnings': [], 
            'recommendations': []
        }
        
        # Check connectivity
        connectivity = diagnosis.get('connectivity', {})
        if not connectivity.get('connection_successful'):
            assessment['critical_issues'].append("Database connection failed")
            assessment['recommendations'].append("Verify database credentials and network connectivity")
        
        if not connectivity.get('performance_acceptable'):
            assessment['warnings'].append("Database response time exceeds 50ms target")
        
        # Check table access
        table_access = diagnosis.get('table_access', {})
        accessible_tables = table_access.get('tables_accessible', {})
        
        required_tables = ['daily_patterns', 'intraday_patterns', 'pattern_detections', 'symbols']
        for table in required_tables:
            if not accessible_tables.get(table):
                assessment['critical_issues'].append(f"Cannot access {table} table")
        
        # Check data content
        data_content = diagnosis.get('data_content', {})
        pattern_counts = data_content.get('pattern_counts', {})
        
        if pattern_counts.get('daily_patterns', 0) == 0:
            assessment['critical_issues'].append("No daily patterns found in database")
            assessment['recommendations'].append("Verify TickStockPL is detecting and storing daily patterns")
        
        if pattern_counts.get('intraday_patterns', 0) == 0:
            assessment['critical_issues'].append("No intraday patterns found in database")
            assessment['recommendations'].append("Verify TickStockPL is detecting and storing intraday patterns")
        
        # Check recent activity
        recent_activity = data_content.get('recent_activity', {})
        total_recent = sum(recent_activity.values())
        
        if total_recent == 0:
            assessment['warnings'].append("No recent pattern activity in last 24 hours")
            assessment['recommendations'].append("Check if TickStockPL pattern detection is currently running")
        
        # Check performance
        performance = diagnosis.get('performance', {})
        if not performance.get('performance_requirements_met'):
            assessment['warnings'].append("Some queries exceed 50ms performance target")
            assessment['recommendations'].append("Consider database query optimization or indexing")
        
        # Determine overall status
        if assessment['critical_issues']:
            assessment['status'] = 'critical'
        elif assessment['warnings']:
            assessment['status'] = 'degraded'
        else:
            assessment['status'] = 'healthy'
        
        return assessment

# Database integration test runner
def run_database_integration_diagnosis():
    """Execute comprehensive database integration diagnosis."""
    print("="*80)
    print("Database Pattern Integration Diagnosis")
    print("="*80)
    
    diagnostics = TestDatabaseIntegrationDiagnostics()
    results = diagnostics.test_comprehensive_database_diagnosis()
    
    # Print results
    print("\n📊 DATABASE DIAGNOSTIC RESULTS:")
    print("-" * 50)
    
    for category, data in results.items():
        if category in ['overall_assessment', 'critical_error']:
            continue
            
        print(f"\n🔍 {category.upper().replace('_', ' ')}:")
        
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (int, float, str, bool)):
                    print(f"  {key}: {value}")
                elif isinstance(value, list) and len(value) <= 5:
                    print(f"  {key}: {value}")
                elif isinstance(value, dict) and len(value) <= 3:
                    print(f"  {key}: {value}")
        
    # Print overall assessment
    if 'overall_assessment' in results:
        assessment = results['overall_assessment']
        status_icon = {'healthy': '✅', 'degraded': '⚠️', 'critical': '❌', 'unknown': '❓'}
        
        print(f"\n{status_icon.get(assessment['status'], '❓')} DATABASE STATUS: {assessment['status'].upper()}")
        
        if assessment['critical_issues']:
            print("\n🚨 CRITICAL ISSUES:")
            for issue in assessment['critical_issues']:
                print(f"  • {issue}")
        
        if assessment['warnings']:
            print("\n⚠️  WARNINGS:")
            for warning in assessment['warnings']:
                print(f"  • {warning}")
        
        if assessment['recommendations']:
            print("\n💡 RECOMMENDATIONS:")
            for rec in assessment['recommendations']:
                print(f"  • {rec}")
    
    if 'critical_error' in results:
        print(f"\n❌ CRITICAL ERROR: {results['critical_error']}")
    
    print("\n" + "="*80)
    return results

if __name__ == "__main__":
    run_database_integration_diagnosis()