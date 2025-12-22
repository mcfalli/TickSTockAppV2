"""
Relationship Validator for Sprint 58 Phase 5

Validates the integrity of ETF-stock relationships, sector mappings,
and theme definitions in cache_entries.

Usage:
    python validate_relationships.py              # Run all validations
    python validate_relationships.py --fix        # Fix broken relationships
    python validate_relationships.py --verbose    # Detailed output
"""

import os
import sys
import argparse
import logging
from typing import Dict, List, Set, Tuple
from collections import defaultdict

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import psycopg2
from urllib.parse import urlparse
from src.core.services.config_manager import get_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RelationshipValidator:
    """Validate ETF-stock relationship integrity"""

    def __init__(self, fix: bool = False, verbose: bool = False):
        """
        Initialize validator

        Args:
            fix: If True, attempt to fix broken relationships
            verbose: If True, show detailed output
        """
        self.fix = fix
        self.verbose = verbose
        self.config = get_config()
        self.db_uri = self.config.get('DATABASE_URI')
        self.conn = self._get_connection()
        self.environment = os.getenv('ENVIRONMENT', 'DEFAULT')  # Use DEFAULT (10 chars limit)
        self.validation_results = {}

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

    def validate_etf_holdings(self) -> Dict[str, any]:
        """
        Validate ETF holdings entries

        Returns:
            Dict with validation results
        """
        logger.info("\n[1/5] Validating ETF holdings...")

        cursor = self.conn.cursor()

        # Count ETF holdings entries from definition_groups
        cursor.execute("""
            SELECT COUNT(*)
            FROM definition_groups
            WHERE type = 'ETF'
            AND environment = %s
        """, (self.environment,))
        total_etfs = cursor.fetchone()[0]

        # Check for ETFs with no memberships (empty holdings)
        cursor.execute("""
            SELECT dg.name
            FROM definition_groups dg
            LEFT JOIN group_memberships gm ON dg.id = gm.group_id
            WHERE dg.type = 'ETF'
            AND dg.environment = %s
            GROUP BY dg.id, dg.name
            HAVING COUNT(gm.id) = 0
        """, (self.environment,))
        empty_holdings = [row[0] for row in cursor.fetchall()]

        # Get symbol counts from group_memberships
        cursor.execute("""
            SELECT
                dg.name as etf,
                COUNT(gm.id) as holding_count
            FROM definition_groups dg
            LEFT JOIN group_memberships gm ON dg.id = gm.group_id
            WHERE dg.type = 'ETF'
            AND dg.environment = %s
            GROUP BY dg.name
            ORDER BY holding_count DESC
        """, (self.environment,))
        symbol_counts = dict(cursor.fetchall())

        results = {
            'total_etfs': total_etfs,
            'empty_holdings': empty_holdings,
            'empty_holdings_count': len(empty_holdings),
            'symbol_counts': symbol_counts,
            'status': 'PASS' if len(empty_holdings) == 0 else 'FAIL'
        }

        logger.info(f"  Total ETFs: {total_etfs}")
        logger.info(f"  Empty holdings: {len(empty_holdings)} "
                   f"({'✓ PASS' if len(empty_holdings) == 0 else '✗ FAIL'})")

        if self.verbose and empty_holdings:
            logger.info(f"  ETFs with empty holdings: {empty_holdings}")

        return results

    def validate_stock_metadata(self) -> Dict[str, any]:
        """
        Validate stock-to-sector assignments in group_memberships

        Returns:
            Dict with validation results
        """
        logger.info("\n[2/5] Validating stock-to-sector assignments...")

        cursor = self.conn.cursor()

        # Count total stocks with sector assignments
        cursor.execute("""
            SELECT COUNT(DISTINCT gm.symbol)
            FROM group_memberships gm
            JOIN definition_groups dg ON gm.group_id = dg.id
            WHERE dg.type = 'SECTOR'
            AND dg.environment = %s
        """, (self.environment,))
        total_stocks = cursor.fetchone()[0]

        # Find stocks in ETFs but not assigned to any sector
        cursor.execute("""
            SELECT DISTINCT gm.symbol
            FROM group_memberships gm
            JOIN definition_groups dg ON gm.group_id = dg.id
            WHERE dg.type = 'ETF'
            AND dg.environment = %s
            AND NOT EXISTS (
                SELECT 1
                FROM group_memberships gm2
                JOIN definition_groups dg2 ON gm2.group_id = dg2.id
                WHERE gm2.symbol = gm.symbol
                AND dg2.type = 'SECTOR'
                AND dg2.environment = %s
            )
        """, (self.environment, self.environment))
        orphan_stocks = [row[0] for row in cursor.fetchall()]

        # Find stocks assigned to 'unknown' sector
        cursor.execute("""
            SELECT gm.symbol
            FROM group_memberships gm
            JOIN definition_groups dg ON gm.group_id = dg.id
            WHERE dg.type = 'SECTOR'
            AND dg.name = 'unknown'
            AND dg.environment = %s
        """, (self.environment,))
        no_sector_stocks = [row[0] for row in cursor.fetchall()]

        results = {
            'total_stocks': total_stocks,
            'orphan_stocks': orphan_stocks,
            'orphan_stocks_count': len(orphan_stocks),
            'no_sector_stocks': no_sector_stocks,
            'no_sector_count': len(no_sector_stocks),
            'status': 'PASS' if len(orphan_stocks) == 0 else 'FAIL'
        }

        logger.info(f"  Total stocks: {total_stocks}")
        logger.info(f"  Orphan stocks: {len(orphan_stocks)} "
                   f"({'✓ PASS' if len(orphan_stocks) == 0 else '✗ FAIL'})")
        logger.info(f"  Missing sector: {len(no_sector_stocks)}")

        if self.verbose and orphan_stocks:
            logger.info(f"  Orphan stocks: {orphan_stocks[:20]}")

        return results

    def validate_bidirectional_relationships(self) -> Dict[str, any]:
        """
        Validate bidirectional ETF ↔ stock relationships

        Returns:
            Dict with validation results
        """
        logger.info("\n[3/5] Validating bidirectional relationships...")

        cursor = self.conn.cursor()

        # Build ETF → stocks mapping from group_memberships
        etf_to_stocks = {}
        cursor.execute("""
            SELECT dg.name, gm.symbol
            FROM definition_groups dg
            JOIN group_memberships gm ON dg.id = gm.group_id
            WHERE dg.type = 'ETF'
            AND dg.environment = %s
            ORDER BY dg.name, gm.symbol
        """, (self.environment,))

        for row in cursor.fetchall():
            etf = row[0]
            stock = row[1]
            if etf not in etf_to_stocks:
                etf_to_stocks[etf] = set()
            etf_to_stocks[etf].add(stock)

        # Build stock → ETFs mapping (reverse of above)
        stock_to_etfs = {}
        cursor.execute("""
            SELECT gm.symbol, dg.name
            FROM group_memberships gm
            JOIN definition_groups dg ON gm.group_id = dg.id
            WHERE dg.type = 'ETF'
            AND dg.environment = %s
            ORDER BY gm.symbol, dg.name
        """, (self.environment,))

        for row in cursor.fetchall():
            stock = row[0]
            etf = row[1]
            if stock not in stock_to_etfs:
                stock_to_etfs[stock] = set()
            stock_to_etfs[stock].add(etf)

        # Validate forward direction (ETF → stock → ETF)
        forward_errors = []
        for etf, stocks in etf_to_stocks.items():
            for stock in stocks:
                if stock not in stock_to_etfs:
                    forward_errors.append((etf, stock, 'stock_metadata_missing'))
                elif etf not in stock_to_etfs[stock]:
                    forward_errors.append((etf, stock, 'etf_not_in_member_of_etfs'))

        # Validate reverse direction (stock → ETF → stock)
        reverse_errors = []
        for stock, etfs in stock_to_etfs.items():
            for etf in etfs:
                if etf not in etf_to_stocks:
                    reverse_errors.append((stock, etf, 'etf_holdings_missing'))
                elif stock not in etf_to_stocks[etf]:
                    reverse_errors.append((stock, etf, 'stock_not_in_holdings'))

        total_relationships = sum(len(stocks) for stocks in etf_to_stocks.values())
        error_count = len(forward_errors) + len(reverse_errors)

        results = {
            'total_relationships': total_relationships,
            'forward_errors': forward_errors,
            'forward_error_count': len(forward_errors),
            'reverse_errors': reverse_errors,
            'reverse_error_count': len(reverse_errors),
            'integrity_percentage': ((total_relationships - error_count) / total_relationships * 100)
                                   if total_relationships > 0 else 0,
            'status': 'PASS' if error_count == 0 else 'FAIL'
        }

        logger.info(f"  Total relationships: {total_relationships}")
        logger.info(f"  Forward errors: {len(forward_errors)}")
        logger.info(f"  Reverse errors: {len(reverse_errors)}")
        logger.info(f"  Integrity: {results['integrity_percentage']:.2f}% "
                   f"({'✓ PASS' if error_count == 0 else '✗ FAIL'})")

        if self.verbose and (forward_errors or reverse_errors):
            if forward_errors:
                logger.info(f"  Sample forward errors: {forward_errors[:5]}")
            if reverse_errors:
                logger.info(f"  Sample reverse errors: {reverse_errors[:5]}")

        return results

    def validate_sector_mappings(self) -> Dict[str, any]:
        """
        Validate sector/industry mappings

        Returns:
            Dict with validation results
        """
        logger.info("\n[4/5] Validating sector/industry mappings...")

        cursor = self.conn.cursor()

        # Count sector entries from definition_groups
        cursor.execute("""
            SELECT COUNT(*)
            FROM definition_groups
            WHERE type = 'SECTOR'
            AND environment = %s
        """, (self.environment,))
        total_sectors = cursor.fetchone()[0]

        # Get industry counts from definition_groups metadata
        cursor.execute("""
            SELECT
                name,
                jsonb_array_length(metadata->'industries') as industry_count,
                metadata->>'stock_count' as stock_count
            FROM definition_groups
            WHERE type = 'SECTOR'
            AND environment = %s
            ORDER BY name
        """, (self.environment,))

        sector_details = []
        total_industries = 0
        for row in cursor.fetchall():
            sector_key = row[0]
            industry_count = row[1]
            stock_count = int(row[2]) if row[2] else 0
            sector_details.append((sector_key, industry_count, stock_count))
            total_industries += industry_count

        results = {
            'total_sectors': total_sectors,
            'expected_sectors': 11,
            'total_industries': total_industries,
            'sector_details': sector_details,
            'status': 'PASS' if total_sectors == 11 else 'FAIL'
        }

        logger.info(f"  Total sectors: {total_sectors}/11 "
                   f"({'✓ PASS' if total_sectors == 11 else '✗ FAIL'})")
        logger.info(f"  Total industries: {total_industries}")

        if self.verbose:
            for sector, industries, stocks in sector_details:
                logger.info(f"    {sector}: {industries} industries, {stocks} stocks")

        return results

    def validate_theme_definitions(self) -> Dict[str, any]:
        """
        Validate theme definitions

        Returns:
            Dict with validation results
        """
        logger.info("\n[5/5] Validating theme definitions...")

        cursor = self.conn.cursor()

        # Count theme entries from definition_groups
        cursor.execute("""
            SELECT COUNT(*)
            FROM definition_groups
            WHERE type = 'THEME'
            AND environment = %s
        """, (self.environment,))
        total_themes = cursor.fetchone()[0]

        # Check for themes with no memberships (empty symbol lists)
        cursor.execute("""
            SELECT dg.name
            FROM definition_groups dg
            LEFT JOIN group_memberships gm ON dg.id = gm.group_id
            WHERE dg.type = 'THEME'
            AND dg.environment = %s
            GROUP BY dg.id, dg.name
            HAVING COUNT(gm.id) = 0
        """, (self.environment,))
        empty_themes = [row[0] for row in cursor.fetchall()]

        # Get symbol counts from group_memberships
        cursor.execute("""
            SELECT
                dg.name,
                COUNT(gm.id) as symbol_count
            FROM definition_groups dg
            LEFT JOIN group_memberships gm ON dg.id = gm.group_id
            WHERE dg.type = 'THEME'
            AND dg.environment = %s
            GROUP BY dg.name
            ORDER BY symbol_count DESC
        """, (self.environment,))
        theme_counts = dict(cursor.fetchall())

        results = {
            'total_themes': total_themes,
            'empty_themes': empty_themes,
            'empty_themes_count': len(empty_themes),
            'theme_counts': theme_counts,
            'status': 'PASS' if len(empty_themes) == 0 else 'FAIL'
        }

        logger.info(f"  Total themes: {total_themes}")
        logger.info(f"  Empty themes: {len(empty_themes)} "
                   f"({'✓ PASS' if len(empty_themes) == 0 else '✗ FAIL'})")

        if self.verbose and theme_counts:
            logger.info(f"  Theme symbol counts:")
            for theme, count in sorted(theme_counts.items(),
                                      key=lambda x: x[1], reverse=True)[:10]:
                logger.info(f"    {theme}: {count} symbols")

        return results

    def run_all_validations(self):
        """Run all validation checks"""
        logger.info("="*60)
        logger.info("RELATIONSHIP VALIDATION REPORT")
        logger.info("="*60)

        # Run validations
        self.validation_results['etf_holdings'] = self.validate_etf_holdings()
        self.validation_results['stock_metadata'] = self.validate_stock_metadata()
        self.validation_results['bidirectional'] = self.validate_bidirectional_relationships()
        self.validation_results['sectors'] = self.validate_sector_mappings()
        self.validation_results['themes'] = self.validate_theme_definitions()

        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print validation summary"""
        logger.info("\n" + "="*60)
        logger.info("VALIDATION SUMMARY")
        logger.info("="*60)

        all_passed = all(
            result.get('status') == 'PASS'
            for result in self.validation_results.values()
        )

        logger.info(f"ETF Holdings:       {self.validation_results['etf_holdings']['status']}")
        logger.info(f"Stock Metadata:     {self.validation_results['stock_metadata']['status']}")
        logger.info(f"Bidirectional:      {self.validation_results['bidirectional']['status']}")
        logger.info(f"Sectors:            {self.validation_results['sectors']['status']}")
        logger.info(f"Themes:             {self.validation_results['themes']['status']}")
        logger.info("="*60)
        logger.info(f"Overall Status:     {'✓ ALL PASSED' if all_passed else '✗ SOME FAILED'}")
        logger.info("="*60)

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Validate ETF-stock relationship integrity'
    )
    parser.add_argument('--fix', action='store_true',
                       help='Attempt to fix broken relationships')
    parser.add_argument('--verbose', action='store_true',
                       help='Show detailed validation output')

    args = parser.parse_args()

    # Create validator
    validator = RelationshipValidator(fix=args.fix, verbose=args.verbose)

    try:
        validator.run_all_validations()
    finally:
        validator.close()


if __name__ == '__main__':
    main()
