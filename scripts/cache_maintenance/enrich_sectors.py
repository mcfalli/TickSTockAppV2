"""
Sector Enrichment - Sprint 60 Phase 1.3

Enriches stock sector classifications using sector ETF holdings data.
Maps stocks to GICS sectors based on their membership in sector-specific ETFs.

Strategy:
- Uses 11 sector ETFs (XLK, XLF, XLV, XLE, XLI, XLY, XLP, XLU, XLB, XLC, XLRE)
- Each sector ETF contains stocks from a specific GICS sector
- Stocks found in sector ETFs are mapped to corresponding sectors
- Provides before/after coverage report

Usage:
    python enrich_sectors.py --dry-run         # Preview sector mappings
    python enrich_sectors.py --mode full       # Apply all sector mappings
    python enrich_sectors.py --rebuild         # Alias for --mode full
"""

import os
import sys
import json
import argparse
import logging
from typing import Dict, List, Set
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import psycopg2
from urllib.parse import urlparse
from src.core.services.config_manager import get_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SectorEnricher:
    """Enrich stock sector classifications using sector ETF data"""

    # Sector ETF to GICS sector mapping
    SECTOR_ETF_MAPPING = {
        'XLK': 'information_technology',
        'XLF': 'financials',
        'XLV': 'health_care',
        'XLE': 'energy',
        'XLI': 'industrials',
        'XLY': 'consumer_discretionary',
        'XLP': 'consumer_staples',
        'XLU': 'utilities',
        'XLB': 'materials',
        'XLC': 'communication_services',
        'XLRE': 'real_estate'
    }

    def __init__(self, mode: str = 'full'):
        """
        Initialize enricher

        Args:
            mode: Enrichment mode ('full', 'dry-run')
        """
        self.mode = mode
        self.dry_run = (mode == 'dry-run')
        self.config = get_config()
        self.db_uri = self.config.get('DATABASE_URI')
        self.conn = None if self.dry_run else self._get_connection()
        self.environment = os.getenv('ENVIRONMENT', 'DEFAULT')

        logger.info(f"SectorEnricher initialized in {mode.upper()} mode")

    def _get_connection(self):
        """Get database connection"""
        parsed = urlparse(self.db_uri)
        return psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            database=parsed.path.lstrip('/'),
            user=parsed.username,
            password=parsed.password
        )

    def get_current_coverage(self) -> Dict[str, int]:
        """
        Get current sector coverage statistics

        Returns:
            Dict with sector name -> stock count
        """
        if self.dry_run:
            # For dry-run, query is read-only so it's safe
            conn = self._get_connection()
            cursor = conn.cursor()
        else:
            cursor = self.conn.cursor()

        query = """
            SELECT dg.name as sector, COUNT(DISTINCT gm.symbol) as stock_count
            FROM definition_groups dg
            LEFT JOIN group_memberships gm ON dg.id = gm.group_id
            WHERE dg.type = 'SECTOR' AND dg.environment = %s
            GROUP BY dg.name
            ORDER BY stock_count DESC
        """
        cursor.execute(query, (self.environment,))
        results = cursor.fetchall()

        if self.dry_run:
            conn.close()

        coverage = {row[0]: row[1] for row in results}
        return coverage

    def get_sector_etf_holdings(self) -> Dict[str, List[str]]:
        """
        Get holdings for all sector ETFs from database

        Returns:
            Dict mapping ETF symbol -> list of stock symbols
        """
        if self.dry_run:
            conn = self._get_connection()
            cursor = conn.cursor()
        else:
            cursor = self.conn.cursor()

        etf_symbols = list(self.SECTOR_ETF_MAPPING.keys())

        query = """
            SELECT dg.name, array_agg(gm.symbol) as holdings
            FROM definition_groups dg
            JOIN group_memberships gm ON dg.id = gm.group_id
            WHERE dg.type = 'ETF' AND dg.name = ANY(%s) AND dg.environment = %s
            GROUP BY dg.name
        """
        cursor.execute(query, (etf_symbols, self.environment))
        results = cursor.fetchall()

        if self.dry_run:
            conn.close()

        etf_holdings = {row[0]: row[1] for row in results}
        return etf_holdings

    def build_sector_mapping(self) -> Dict[str, str]:
        """
        Build symbol -> sector mapping from sector ETF holdings

        Returns:
            Dict mapping stock symbol -> sector key
        """
        etf_holdings = self.get_sector_etf_holdings()
        symbol_to_sector = {}

        for etf_symbol, holdings in etf_holdings.items():
            sector_key = self.SECTOR_ETF_MAPPING.get(etf_symbol)
            if not sector_key:
                continue

            logger.info(f"{etf_symbol} ({sector_key}): {len(holdings)} stocks")

            for stock_symbol in holdings:
                # If symbol already mapped, keep first mapping (some stocks may be in multiple sector ETFs)
                if stock_symbol not in symbol_to_sector:
                    symbol_to_sector[stock_symbol] = sector_key

        logger.info(f"Built mapping for {len(symbol_to_sector)} unique stocks")
        return symbol_to_sector

    def apply_sector_mappings(self, symbol_to_sector: Dict[str, str]) -> Dict[str, int]:
        """
        Apply sector mappings to database

        Args:
            symbol_to_sector: Dict mapping stock symbol -> sector key

        Returns:
            Dict with statistics (updated, skipped, errors)
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would update sectors for {len(symbol_to_sector)} stocks")
            return {'updated': len(symbol_to_sector), 'skipped': 0, 'errors': 0}

        cursor = self.conn.cursor()

        # Get all sector group IDs
        cursor.execute("""
            SELECT name, id FROM definition_groups
            WHERE type = 'SECTOR' AND environment = %s
        """, (self.environment,))
        sector_groups = {row[0]: row[1] for row in cursor.fetchall()}

        # Get unknown sector ID
        unknown_sector_id = sector_groups.get('unknown')
        if not unknown_sector_id:
            logger.error("No 'unknown' sector group found")
            return {'updated': 0, 'skipped': 0, 'errors': 1}

        stats = {'updated': 0, 'skipped': 0, 'errors': 0}

        for symbol, sector_key in symbol_to_sector.items():
            sector_group_id = sector_groups.get(sector_key)
            if not sector_group_id:
                logger.warning(f"{symbol}: Sector '{sector_key}' not found in database")
                stats['errors'] += 1
                continue

            try:
                # Delete existing membership in unknown sector
                cursor.execute("""
                    DELETE FROM group_memberships
                    WHERE group_id = %s AND symbol = %s
                """, (unknown_sector_id, symbol))

                # Insert/update membership in correct sector
                cursor.execute("""
                    INSERT INTO group_memberships (group_id, symbol, metadata)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (group_id, symbol) DO NOTHING
                """, (sector_group_id, symbol, json.dumps({'source': 'sector_etf_enrichment'})))

                stats['updated'] += 1

                if stats['updated'] % 100 == 0:
                    logger.info(f"Progress: {stats['updated']} stocks updated...")

            except Exception as e:
                logger.error(f"Error updating {symbol}: {e}")
                stats['errors'] += 1
                self.conn.rollback()
                continue

        self.conn.commit()
        return stats

    def run_enrichment(self):
        """Run sector enrichment workflow"""
        logger.info("="*60)
        logger.info("SECTOR ENRICHMENT - Sprint 60 Phase 1.3")
        logger.info("="*60)

        # Get before coverage
        logger.info("\n📊 BEFORE Enrichment:")
        before_coverage = self.get_current_coverage()
        total_stocks_before = sum(before_coverage.values())
        unknown_before = before_coverage.get('unknown', 0)
        known_before = total_stocks_before - unknown_before

        logger.info(f"  Total stocks: {total_stocks_before:,}")
        logger.info(f"  Known sectors: {known_before:,} ({known_before/total_stocks_before*100:.2f}%)")
        logger.info(f"  Unknown sector: {unknown_before:,} ({unknown_before/total_stocks_before*100:.2f}%)")

        # Build sector mapping
        logger.info("\n🔍 Building sector mappings from ETF holdings...")
        symbol_to_sector = self.build_sector_mapping()

        # Calculate potential improvement
        stocks_to_update = len(symbol_to_sector)
        unknown_after_estimate = unknown_before - stocks_to_update
        known_after_estimate = known_before + stocks_to_update

        logger.info(f"\n📈 ESTIMATED After Enrichment:")
        logger.info(f"  Stocks to update: {stocks_to_update:,}")
        logger.info(f"  Known sectors: {known_after_estimate:,} ({known_after_estimate/total_stocks_before*100:.2f}%)")
        logger.info(f"  Unknown sector: {unknown_after_estimate:,} ({unknown_after_estimate/total_stocks_before*100:.2f}%)")

        # Check if target is met
        target_unknown = 500
        if unknown_after_estimate <= target_unknown:
            logger.info(f"  ✅ Target met: {unknown_after_estimate:,} <= {target_unknown}")
        else:
            logger.info(f"  ⚠️  Target not met: {unknown_after_estimate:,} > {target_unknown}")
            logger.info(f"  Still need to classify {unknown_after_estimate - target_unknown:,} more stocks")

        # Apply mappings
        logger.info(f"\n🚀 Applying sector mappings...")
        stats = self.apply_sector_mappings(symbol_to_sector)

        logger.info(f"\n📊 Update Statistics:")
        logger.info(f"  Updated: {stats['updated']:,}")
        logger.info(f"  Skipped: {stats['skipped']:,}")
        logger.info(f"  Errors: {stats['errors']:,}")

        # Get after coverage (only if not dry-run)
        if not self.dry_run:
            logger.info("\n📊 AFTER Enrichment:")
            after_coverage = self.get_current_coverage()
            total_stocks_after = sum(after_coverage.values())
            unknown_after = after_coverage.get('unknown', 0)
            known_after = total_stocks_after - unknown_after

            logger.info(f"  Total stocks: {total_stocks_after:,}")
            logger.info(f"  Known sectors: {known_after:,} ({known_after/total_stocks_after*100:.2f}%)")
            logger.info(f"  Unknown sector: {unknown_after:,} ({unknown_after/total_stocks_after*100:.2f}%)")

            improvement = known_after - known_before
            logger.info(f"\n✨ Improvement:")
            logger.info(f"  Added {improvement:,} sector classifications")
            logger.info(f"  Coverage increased by {improvement/total_stocks_after*100:.2f}%")

            # Show top sectors
            logger.info(f"\n🏆 Top Sectors by Stock Count:")
            sorted_sectors = sorted(after_coverage.items(), key=lambda x: x[1], reverse=True)
            for sector, count in sorted_sectors[:10]:
                percentage = count / total_stocks_after * 100
                logger.info(f"  {sector:30s}: {count:5,} ({percentage:5.2f}%)")

        logger.info("\n" + "="*60)
        logger.info("Sector Enrichment Complete!")
        logger.info("="*60)

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Enrich stock sector classifications using sector ETF data'
    )
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview without applying changes')
    parser.add_argument('--mode', type=str, choices=['full', 'dry-run'],
                       default='full',
                       help='Enrichment mode: full (apply), dry-run (preview)')
    parser.add_argument('--rebuild', action='store_true',
                       help='Force full enrichment (alias for --mode full)')

    args = parser.parse_args()

    # Handle --rebuild flag (overrides --mode)
    if args.rebuild:
        args.mode = 'full'

    # Handle --dry-run flag (overrides --mode)
    if args.dry_run:
        args.mode = 'dry-run'

    # Create enricher and run
    enricher = SectorEnricher(mode=args.mode)

    try:
        enricher.run_enrichment()
    finally:
        enricher.close()


if __name__ == '__main__':
    main()
