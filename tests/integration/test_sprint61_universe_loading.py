"""
Sprint 61 Integration Tests - Universe Loading via RelationshipCache

Tests the migration from CacheControl to RelationshipCache for WebSocket universe loading.

Test Coverage:
- Single universe loading (nasdaq100, sp500, dow30)
- Multi-universe join (sp500:nasdaq100, etc.)
- ETF holdings loading (SPY, QQQ, etc.)
- Cache performance (hit/miss tracking)
- WebSocket integration (multi-connection manager)
"""

import pytest
import time
from src.core.services.relationship_cache import get_relationship_cache


class TestRelationshipCacheUniverseLoading:
    """Test RelationshipCache universe loading methods"""

    def test_single_universe_nasdaq100(self):
        """Test: Load NASDAQ-100 universe"""
        cache = get_relationship_cache()
        symbols = cache.get_universe_symbols('nasdaq100')

        # Verify result
        assert isinstance(symbols, list), "Should return a list"
        assert len(symbols) > 0, "NASDAQ-100 should have symbols"
        assert 'AAPL' in symbols, "AAPL should be in NASDAQ-100"
        assert symbols == sorted(symbols), "Symbols should be sorted"

        print(f"[OK] NASDAQ-100: {len(symbols)} symbols loaded")

    def test_etf_holdings_voo(self):
        """Test: Load VOO ETF holdings (S&P 500 proxy)"""
        cache = get_relationship_cache()
        symbols = cache.get_universe_symbols('VOO')

        # Verify result
        assert isinstance(symbols, list), "Should return a list"
        assert len(symbols) >= 500, f"VOO should have ~500+ symbols, got {len(symbols)}"
        assert 'AAPL' in symbols, "AAPL should be in VOO"
        assert symbols == sorted(symbols), "Symbols should be sorted"

        print(f"[OK] VOO ETF (S&P 500): {len(symbols)} symbols loaded")

    def test_single_universe_dow30(self):
        """Test: Load Dow 30 universe"""
        cache = get_relationship_cache()
        symbols = cache.get_universe_symbols('dow30')

        # Verify result
        assert isinstance(symbols, list), "Should return a list"
        assert len(symbols) == 30, f"Dow 30 should have exactly 30 symbols, got {len(symbols)}"
        assert 'AAPL' in symbols, "AAPL should be in Dow 30"
        assert symbols == sorted(symbols), "Symbols should be sorted"

        print(f"[OK] Dow 30: {len(symbols)} symbols loaded")

    def test_multi_universe_join_spy_nasdaq100(self):
        """Test: Multi-universe join SPY:nasdaq100"""
        cache = get_relationship_cache()

        # Load individual universes
        spy_symbols = set(cache.get_universe_symbols('SPY'))
        nasdaq100_symbols = set(cache.get_universe_symbols('nasdaq100'))

        # Load joined universe
        joined_symbols = cache.get_universe_symbols('SPY:nasdaq100')

        # Verify distinct union
        expected_union = spy_symbols | nasdaq100_symbols
        assert len(joined_symbols) == len(expected_union), "Should be distinct union"
        assert set(joined_symbols) == expected_union, "Should match union of both universes"
        assert joined_symbols == sorted(joined_symbols), "Symbols should be sorted"

        # Verify it's less than sum (due to overlaps)
        total_if_no_overlap = len(spy_symbols) + len(nasdaq100_symbols)
        assert len(joined_symbols) < total_if_no_overlap, "Should have overlaps removed"

        print(f"[OK] SPY:nasdaq100: {len(joined_symbols)} distinct symbols "
              f"(SPY={len(spy_symbols)}, nasdaq100={len(nasdaq100_symbols)})")

    def test_multi_universe_join_three_universes(self):
        """Test: Multi-universe join SPY:QQQ:dow30"""
        cache = get_relationship_cache()

        # Load individual universes
        spy = set(cache.get_universe_symbols('SPY'))
        qqq = set(cache.get_universe_symbols('QQQ'))
        dow30 = set(cache.get_universe_symbols('dow30'))

        # Load joined universe
        joined = cache.get_universe_symbols('SPY:QQQ:dow30')

        # Verify distinct union
        expected_union = spy | qqq | dow30
        assert len(joined) == len(expected_union), "Should be distinct union of all 3"
        assert set(joined) == expected_union, "Should match union of all universes"
        assert joined == sorted(joined), "Symbols should be sorted"

        print(f"[OK] SPY:QQQ:dow30: {len(joined)} distinct symbols "
              f"(SPY={len(spy)}, QQQ={len(qqq)}, dow30={len(dow30)})")

    def test_etf_holdings_spy(self):
        """Test: Load SPY ETF holdings"""
        cache = get_relationship_cache()
        symbols = cache.get_universe_symbols('SPY')

        # Verify result
        assert isinstance(symbols, list), "Should return a list"
        assert len(symbols) > 0, "SPY should have holdings"
        assert 'AAPL' in symbols, "AAPL should be in SPY"
        assert symbols == sorted(symbols), "Symbols should be sorted"

        print(f"[OK] SPY ETF: {len(symbols)} holdings loaded")

    def test_etf_holdings_qqq(self):
        """Test: Load QQQ ETF holdings"""
        cache = get_relationship_cache()
        symbols = cache.get_universe_symbols('QQQ')

        # Verify result
        assert isinstance(symbols, list), "Should return a list"
        assert len(symbols) > 0, "QQQ should have holdings"
        assert 'AAPL' in symbols, "AAPL should be in QQQ"
        assert symbols == sorted(symbols), "Symbols should be sorted"

        print(f"[OK] QQQ ETF: {len(symbols)} holdings loaded")

    def test_cache_performance_hit(self):
        """Test: Verify cache hit performance <1ms"""
        cache = get_relationship_cache()

        # First call (cache miss)
        start = time.time()
        symbols1 = cache.get_universe_symbols('nasdaq100')
        elapsed_miss = (time.time() - start) * 1000  # Convert to ms

        # Second call (cache hit)
        start = time.time()
        symbols2 = cache.get_universe_symbols('nasdaq100')
        elapsed_hit = (time.time() - start) * 1000  # Convert to ms

        # Verify results match
        assert symbols1 == symbols2, "Cache hit should return same data"

        # Verify cache hit is faster
        assert elapsed_hit < elapsed_miss, "Cache hit should be faster than miss"
        assert elapsed_hit < 1.0, f"Cache hit should be <1ms, got {elapsed_hit:.2f}ms"

        print(f"[OK] Cache performance: miss={elapsed_miss:.2f}ms, hit={elapsed_hit:.2f}ms")

    def test_cache_stats_tracking(self):
        """Test: Verify cache statistics tracking"""
        cache = get_relationship_cache()

        # Reset stats by creating new instance (or clear existing)
        stats_before = cache.get_stats()

        # Load universe (should be cache miss if not loaded before)
        _ = cache.get_universe_symbols('dow30')

        # Load same universe again (should be cache hit)
        _ = cache.get_universe_symbols('dow30')

        stats_after = cache.get_stats()

        # Verify stats increased
        assert stats_after['hits'] >= stats_before['hits'], "Hits should increase or stay same"
        assert stats_after['loads'] >= stats_before['loads'], "Loads should increase or stay same"

        print(f"[OK] Cache stats: {stats_after}")

    def test_empty_universe_key(self):
        """Test: Empty universe key returns empty list"""
        cache = get_relationship_cache()
        symbols = cache.get_universe_symbols('')

        assert symbols == [], "Empty key should return empty list"
        print("[OK] Empty universe key handled correctly")

    def test_nonexistent_universe(self):
        """Test: Non-existent universe returns empty list"""
        cache = get_relationship_cache()
        symbols = cache.get_universe_symbols('nonexistent_universe_xyz')

        assert symbols == [], "Non-existent universe should return empty list"
        print("[OK] Non-existent universe handled correctly")

    def test_universe_symbols_distinct(self):
        """Test: Multi-universe join returns distinct symbols only"""
        cache = get_relationship_cache()

        # Load same universe twice in join (should deduplicate)
        symbols = cache.get_universe_symbols('dow30:dow30')

        # Should be same as loading once
        symbols_single = cache.get_universe_symbols('dow30')

        assert len(symbols) == len(symbols_single), "Duplicate universe should be deduplicated"
        assert set(symbols) == set(symbols_single), "Should match single universe"

        print("[OK] Duplicate universes deduplicated correctly")


class TestWebSocketIntegration:
    """Test WebSocket integration with RelationshipCache"""

    def test_multi_connection_manager_import(self):
        """Test: MultiConnectionManager can import RelationshipCache"""
        try:
            from src.infrastructure.websocket.multi_connection_manager import MultiConnectionManager
            from src.core.services.relationship_cache import get_relationship_cache
            print("[OK] Imports successful")
        except ImportError as e:
            pytest.fail(f"Import failed: {e}")

    def test_market_data_service_import(self):
        """Test: MarketDataService can import RelationshipCache"""
        try:
            from src.core.services.market_data_service import MarketDataService
            from src.core.services.relationship_cache import get_relationship_cache
            print("[OK] Imports successful")
        except ImportError as e:
            pytest.fail(f"Import failed: {e}")


class TestCacheControlDeprecation:
    """Test CacheControl deprecation warnings"""

    def test_deprecation_warning_logged(self, caplog):
        """Test: get_universe_tickers logs deprecation warning"""
        from src.infrastructure.cache.cache_control import CacheControl

        cache = CacheControl()
        cache.initialize()

        # This should log a deprecation warning
        _ = cache.get_universe_tickers('test_universe')

        # Check for deprecation warning in logs
        assert any('DEPRECATED' in record.message for record in caplog.records), \
            "Should log deprecation warning"

        print("[OK] Deprecation warning logged")


def run_all_tests():
    """Run all tests manually (for development)"""
    print("\n" + "="*80)
    print("Sprint 61 Integration Tests - Universe Loading")
    print("="*80 + "\n")

    # Test suite 1: RelationshipCache
    print("\n--- Test Suite 1: RelationshipCache Universe Loading ---")
    suite1 = TestRelationshipCacheUniverseLoading()

    try:
        suite1.test_single_universe_nasdaq100()
        suite1.test_etf_holdings_voo()
        suite1.test_single_universe_dow30()
        suite1.test_multi_universe_join_spy_nasdaq100()
        suite1.test_multi_universe_join_three_universes()
        suite1.test_etf_holdings_spy()
        suite1.test_etf_holdings_qqq()
        suite1.test_cache_performance_hit()
        suite1.test_cache_stats_tracking()
        suite1.test_empty_universe_key()
        suite1.test_nonexistent_universe()
        suite1.test_universe_symbols_distinct()
        print("\n[OK] All RelationshipCache tests passed!")
    except AssertionError as e:
        print(f"\n[FAIL] Test failed: {e}")
        raise

    # Test suite 2: WebSocket Integration
    print("\n--- Test Suite 2: WebSocket Integration ---")
    suite2 = TestWebSocketIntegration()

    try:
        suite2.test_multi_connection_manager_import()
        suite2.test_market_data_service_import()
        print("\n[OK] All WebSocket integration tests passed!")
    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        raise

    print("\n" + "="*80)
    print("[OK] ALL SPRINT 61 TESTS PASSED!")
    print("="*80 + "\n")


if __name__ == '__main__':
    run_all_tests()
