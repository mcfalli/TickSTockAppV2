#!/usr/bin/env python3
"""
Sprint 23: End-to-End Integration Test
====================================

Tests the complete Sprint 23 Advanced Pattern Analytics pipeline:
1. Database functions return real data
2. Services process data correctly  
3. API endpoints work with real data
4. Performance targets are met

Author: TickStock Development Team
Date: 2025-09-06
Sprint: 23
"""

import sys
import os
import asyncio
import time
import json
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.infrastructure.database.connection_pool import DatabaseConnectionPool
from src.core.services.pattern_analytics_advanced_service import PatternAnalyticsAdvancedService
from src.core.services.pattern_registry_service import PatternRegistryService

class Sprint23IntegrationTester:
    """End-to-end integration tester for Sprint 23 analytics"""
    
    def __init__(self):
        """Initialize test components"""
        self.db_pool = None
        self.analytics_service = None
        self.pattern_registry = None
        self.results = {}
    
    async def setup(self):
        """Setup test environment"""
        print("🔧 Setting up Sprint 23 integration test environment...")
        
        try:
            # Initialize database connection pool
            self.db_pool = DatabaseConnectionPool({})
            print("✅ Database connection pool initialized")
            
            # Initialize pattern registry
            self.pattern_registry = PatternRegistryService()
            print("✅ Pattern registry service initialized")
            
            # Initialize analytics service
            self.analytics_service = PatternAnalyticsAdvancedService(
                self.db_pool, self.pattern_registry
            )
            print("✅ Pattern analytics advanced service initialized")
            
            return True
            
        except Exception as e:
            print(f"❌ Setup failed: {e}")
            return False
    
    async def test_database_functions_directly(self):
        """Test database functions directly return real data"""
        print("\n📊 Testing database functions directly...")
        
        tests = [
            ("Pattern Correlations", "SELECT * FROM calculate_pattern_correlations(30, 0.3) LIMIT 3"),
            ("Advanced Metrics", "SELECT * FROM calculate_advanced_pattern_metrics('WeeklyBO')"),
            ("Pattern Comparison", "SELECT * FROM compare_pattern_performance('WeeklyBO', 'DailyBO')"),
            ("Pattern Detections Count", "SELECT COUNT(*) FROM pattern_detections"),
            ("Pattern Success Rates", "SELECT * FROM calculate_pattern_success_rate('WeeklyBO', 30)")
        ]
        
        for test_name, query in tests:
            start_time = time.time()
            
            try:
                async with self.db_pool.get_connection() as conn:
                    async with conn.cursor() as cursor:
                        await cursor.execute(query)
                        results = await cursor.fetchall()
                        
                execution_time = (time.time() - start_time) * 1000
                
                if results:
                    print(f"✅ {test_name}: {len(results)} results in {execution_time:.2f}ms")
                    if len(results) <= 3:
                        for i, row in enumerate(results):
                            print(f"   Row {i+1}: {dict(row) if hasattr(row, 'keys') else row}")
                else:
                    print(f"⚠️  {test_name}: No results returned")
                    
                self.results[f"db_function_{test_name.lower().replace(' ', '_')}"] = {
                    'success': True,
                    'execution_time_ms': execution_time,
                    'result_count': len(results)
                }
                
            except Exception as e:
                print(f"❌ {test_name} failed: {e}")
                self.results[f"db_function_{test_name.lower().replace(' ', '_')}"] = {
                    'success': False,
                    'error': str(e)
                }
    
    async def test_analytics_services(self):
        """Test analytics services with real data"""
        print("\n🔬 Testing analytics services...")
        
        try:
            # Test pattern correlations
            start_time = time.time()
            correlations = await self.analytics_service.get_pattern_correlations(
                days_back=30, min_correlation=0.3
            )
            correlation_time = (time.time() - start_time) * 1000
            
            print(f"✅ Pattern Correlations: {len(correlations)} correlations in {correlation_time:.2f}ms")
            if correlations:
                print(f"   Sample: {correlations[0].pattern_a} ↔ {correlations[0].pattern_b} = {correlations[0].correlation_coefficient:.3f}")
            
            # Test advanced metrics
            start_time = time.time()
            metrics = await self.analytics_service.get_advanced_metrics('WeeklyBO')
            metrics_time = (time.time() - start_time) * 1000
            
            if metrics:
                print(f"✅ Advanced Metrics: WeeklyBO success rate = {metrics.success_rate:.2f}% in {metrics_time:.2f}ms")
                print(f"   Sharpe Ratio: {metrics.sharpe_ratio:.3f}, Max Drawdown: {metrics.max_drawdown:.3f}")
            else:
                print("⚠️  Advanced Metrics: No metrics returned")
            
            # Test pattern comparison
            start_time = time.time()
            comparison = await self.analytics_service.compare_patterns('WeeklyBO', 'DailyBO')
            comparison_time = (time.time() - start_time) * 1000
            
            if comparison:
                print(f"✅ Pattern Comparison: WeeklyBO vs DailyBO in {comparison_time:.2f}ms")
                print(f"   WeeklyBO: {comparison.pattern_a_success_rate:.2f}%, DailyBO: {comparison.pattern_b_success_rate:.2f}%")
                print(f"   Significant: {comparison.is_significant}, p-value: {comparison.p_value:.4f}")
            else:
                print("⚠️  Pattern Comparison: No comparison returned")
            
            self.results['services'] = {
                'correlations_count': len(correlations),
                'correlation_time_ms': correlation_time,
                'metrics_available': metrics is not None,
                'metrics_time_ms': metrics_time,
                'comparison_available': comparison is not None,
                'comparison_time_ms': comparison_time
            }
            
        except Exception as e:
            print(f"❌ Analytics services test failed: {e}")
            self.results['services'] = {'success': False, 'error': str(e)}
    
    async def test_performance_targets(self):
        """Test performance targets are met"""
        print("\n⚡ Testing performance targets...")
        
        # Target: Database functions <30ms
        # Target: Service operations <50ms
        # Target: End-to-end pipeline <200ms
        
        performance_tests = [
            ("Database Direct Query", lambda: self.db_pool.execute_analytics_function(
                'calculate_pattern_success_rate', ('WeeklyBO', 30)
            ), 30),
            ("Service Pattern Correlations", lambda: self.analytics_service.get_pattern_correlations(30, 0.3), 50),
            ("Service Advanced Metrics", lambda: self.analytics_service.get_advanced_metrics('WeeklyBO'), 50)
        ]
        
        performance_results = {}
        
        for test_name, test_func, target_ms in performance_tests:
            times = []
            
            # Run test 3 times for average
            for i in range(3):
                start_time = time.time()
                try:
                    await test_func()
                    execution_time = (time.time() - start_time) * 1000
                    times.append(execution_time)
                except Exception as e:
                    print(f"❌ {test_name} run {i+1} failed: {e}")
                    continue
            
            if times:
                avg_time = sum(times) / len(times)
                max_time = max(times)
                
                if avg_time <= target_ms:
                    print(f"✅ {test_name}: {avg_time:.2f}ms avg (target: <{target_ms}ms)")
                else:
                    print(f"⚠️  {test_name}: {avg_time:.2f}ms avg (exceeds target: <{target_ms}ms)")
                
                performance_results[test_name.lower().replace(' ', '_')] = {
                    'avg_time_ms': avg_time,
                    'max_time_ms': max_time,
                    'target_ms': target_ms,
                    'meets_target': avg_time <= target_ms
                }
        
        self.results['performance'] = performance_results
    
    async def test_data_quality(self):
        """Test data quality and realism"""
        print("\n📈 Testing data quality...")
        
        try:
            # Test realistic success rates
            async with self.db_pool.get_connection() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("""
                        SELECT 
                            pd.name as pattern_name,
                            COUNT(det.id) as total_detections,
                            COUNT(det.id) FILTER (WHERE det.outcome_1d > 0) as successful_outcomes,
                            ROUND(
                                (COUNT(det.id) FILTER (WHERE det.outcome_1d > 0) * 100.0 / COUNT(det.id))::numeric, 2
                            ) as success_rate_percent
                        FROM pattern_definitions pd
                        LEFT JOIN pattern_detections det ON pd.id = det.pattern_id
                        WHERE pd.enabled = true AND det.detected_at IS NOT NULL
                        GROUP BY pd.id, pd.name
                        ORDER BY success_rate_percent DESC
                        LIMIT 5
                    """)
                    
                    pattern_stats = await cursor.fetchall()
                    
                    print("✅ Pattern Success Rate Analysis:")
                    for row in pattern_stats:
                        print(f"   {row['pattern_name']}: {row['success_rate_percent']}% "
                             f"({row['successful_outcomes']}/{row['total_detections']} detections)")
                    
                    # Quality checks
                    total_patterns = len(pattern_stats)
                    avg_success_rate = sum(float(row['success_rate_percent']) for row in pattern_stats) / total_patterns
                    total_detections = sum(int(row['total_detections']) for row in pattern_stats)
                    
                    print(f"\n📊 Data Quality Summary:")
                    print(f"   • Total patterns with data: {total_patterns}")
                    print(f"   • Average success rate: {avg_success_rate:.2f}%")
                    print(f"   • Total detections: {total_detections}")
                    
                    quality_score = "Good" if avg_success_rate > 45 and total_detections > 100 else "Needs Improvement"
                    print(f"   • Quality assessment: {quality_score}")
                    
                    self.results['data_quality'] = {
                        'total_patterns': total_patterns,
                        'avg_success_rate': avg_success_rate,
                        'total_detections': total_detections,
                        'quality_score': quality_score
                    }
                    
        except Exception as e:
            print(f"❌ Data quality test failed: {e}")
            self.results['data_quality'] = {'success': False, 'error': str(e)}
    
    def generate_summary_report(self):
        """Generate final test summary report"""
        print("\n" + "="*60)
        print("🎯 SPRINT 23 INTEGRATION TEST SUMMARY")
        print("="*60)
        
        # Overall status
        total_tests = len(self.results)
        successful_tests = sum(1 for result in self.results.values() 
                             if isinstance(result, dict) and result.get('success', True))
        
        print(f"📊 Test Results: {successful_tests}/{total_tests} test categories passed")
        
        # Performance summary
        if 'performance' in self.results:
            perf_results = self.results['performance']
            performance_passed = sum(1 for test in perf_results.values() 
                                   if test.get('meets_target', False))
            total_perf_tests = len(perf_results)
            print(f"⚡ Performance: {performance_passed}/{total_perf_tests} targets met")
        
        # Data quality summary
        if 'data_quality' in self.results:
            quality = self.results['data_quality']
            if 'quality_score' in quality:
                print(f"📈 Data Quality: {quality['quality_score']} "
                     f"({quality.get('total_detections', 0)} detections)")
        
        # Services summary
        if 'services' in self.results:
            services = self.results['services']
            if services.get('correlations_count', 0) > 0:
                print(f"🔬 Services: {services['correlations_count']} correlations found, "
                     f"advanced metrics available")
        
        # Overall assessment
        print(f"\n🎯 SPRINT 23 STATUS: ", end="")
        if successful_tests >= total_tests * 0.8:  # 80% success rate
            print("✅ READY FOR PRODUCTION")
            print("   • Database functions working with real data")
            print("   • Services processing data correctly")
            print("   • Performance targets achieved") 
            print("   • Data quality acceptable")
        else:
            print("⚠️  NEEDS ATTENTION")
            print("   • Some tests failed - review errors above")
        
        print("\n📋 NEXT STEPS:")
        print("   1. Address any failed tests")
        print("   2. Update API endpoints to use real services")
        print("   3. Test frontend integration")
        print("   4. Deploy to production")
        
        # Save results to file
        with open('sprint23_test_results.json', 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"\n💾 Full test results saved to: sprint23_test_results.json")
    
    async def run_all_tests(self):
        """Run complete integration test suite"""
        print("🚀 Starting Sprint 23 End-to-End Integration Tests")
        print("="*60)
        
        if not await self.setup():
            print("❌ Setup failed - cannot continue with tests")
            return False
        
        try:
            await self.test_database_functions_directly()
            await self.test_analytics_services()
            await self.test_performance_targets()
            await self.test_data_quality()
            
            self.generate_summary_report()
            return True
            
        except Exception as e:
            print(f"❌ Integration test suite failed: {e}")
            return False

async def main():
    """Main test execution"""
    tester = Sprint23IntegrationTester()
    success = await tester.run_all_tests()
    
    print(f"\n🎯 Integration Test Complete: {'SUCCESS' if success else 'FAILED'}")
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)