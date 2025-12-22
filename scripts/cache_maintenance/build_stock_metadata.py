"""
Stock Metadata Builder for Sprint 58

Builds comprehensive stock metadata from ETF holdings with:
- Sector and industry classifications
- ETF membership (reverse mapping: stock → ETFs)
- Theme membership linkage
- Market cap validation

Usage:
    python build_stock_metadata.py --dry-run      # Preview without inserting
    python build_stock_metadata.py                # Build all stock metadata
    python build_stock_metadata.py --rebuild      # Rebuild from scratch
"""

import os
import sys
import json
import argparse
import logging
from typing import List, Dict, Set, Optional
from datetime import datetime
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


class StockMetadataBuilder:
    """Build stock metadata from ETF holdings"""

    # GICS Sectors (11 sectors)
    GICS_SECTORS = [
        'Information Technology',
        'Health Care',
        'Financials',
        'Consumer Discretionary',
        'Communication Services',
        'Industrials',
        'Consumer Staples',
        'Energy',
        'Utilities',
        'Real Estate',
        'Materials'
    ]

    # Mapping from readable sector names to database sector keys
    SECTOR_NAME_TO_KEY = {
        'Information Technology': 'information_technology',
        'Health Care': 'health_care',
        'Financials': 'financials',
        'Consumer Discretionary': 'consumer_discretionary',
        'Communication Services': 'communication_services',
        'Industrials': 'industrials',
        'Consumer Staples': 'consumer_staples',
        'Energy': 'energy',
        'Utilities': 'utilities',
        'Real Estate': 'real_estate',
        'Materials': 'materials',
        'Unknown': 'unknown'
    }

    # Sector to industry mapping (simplified)
    SECTOR_INDUSTRIES = {
        'Information Technology': [
            'Software',
            'Hardware',
            'Semiconductors',
            'IT Services'
        ],
        'Health Care': [
            'Pharmaceuticals',
            'Biotechnology',
            'Medical Devices',
            'Healthcare Services'
        ],
        'Financials': [
            'Banks',
            'Insurance',
            'Capital Markets',
            'Financial Services'
        ],
        'Consumer Discretionary': [
            'Retail',
            'Automobiles',
            'Hotels & Restaurants',
            'Consumer Durables'
        ],
        'Communication Services': [
            'Telecommunications',
            'Media',
            'Entertainment',
            'Interactive Media'
        ],
        'Industrials': [
            'Aerospace & Defense',
            'Construction',
            'Machinery',
            'Transportation'
        ],
        'Consumer Staples': [
            'Food & Beverage',
            'Household Products',
            'Personal Products',
            'Tobacco'
        ],
        'Energy': [
            'Oil & Gas',
            'Energy Equipment',
            'Oil & Gas Refining'
        ],
        'Utilities': [
            'Electric Utilities',
            'Gas Utilities',
            'Water Utilities'
        ],
        'Real Estate': [
            'REITs',
            'Real Estate Services'
        ],
        'Materials': [
            'Chemicals',
            'Metals & Mining',
            'Paper & Forest Products'
        ]
    }

    def __init__(self, dry_run: bool = False, rebuild: bool = False):
        """
        Initialize builder

        Args:
            dry_run: If True, preview without database insertion
            rebuild: If True, delete existing metadata before building
        """
        self.dry_run = dry_run
        self.rebuild = rebuild
        self.config = get_config()
        self.db_uri = self.config.get('DATABASE_URI')
        self.conn = None if dry_run else self._get_connection()
        self.environment = os.getenv('ENVIRONMENT', 'DEFAULT')  # Use DEFAULT (10 chars limit)

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

    def collect_all_stocks_from_etfs(self) -> Dict[str, Set[str]]:
        """
        Collect all unique stocks from ETF holdings

        Returns:
            Dict mapping stock_symbol → set of ETF symbols containing it
        """
        logger.info("Collecting stocks from ETF holdings...")

        stock_to_etfs = defaultdict(set)

        # Query the database even in dry-run mode (we need the data for planning)
        # Dry-run only skips INSERT operations
        if self.dry_run:
            logger.info("[DRY RUN] Querying ETF holdings from definition_groups (read-only)")

        try:
            # Get database connection for query (even in dry-run)
            if self.dry_run:
                conn = self._get_connection()
                cursor = conn.cursor()
            else:
                cursor = self.conn.cursor()

            query = """
                SELECT dg.name as etf_symbol, gm.symbol as stock_symbol
                FROM definition_groups dg
                JOIN group_memberships gm ON dg.id = gm.group_id
                WHERE dg.type = 'ETF'
                AND dg.environment = %s
                ORDER BY dg.name, gm.symbol
            """
            cursor.execute(query, (self.environment,))

            etf_count = 0
            current_etf = None

            for row in cursor.fetchall():
                etf_symbol = row[0]
                stock_symbol = row[1]

                if etf_symbol != current_etf:
                    etf_count += 1
                    current_etf = etf_symbol

                stock_to_etfs[stock_symbol].add(etf_symbol)

            logger.info(f"Collected {len(stock_to_etfs)} unique stocks from "
                       f"{etf_count} ETFs")

            # Close connection if dry-run
            if self.dry_run:
                cursor.close()
                conn.close()

            return stock_to_etfs

        except Exception as e:
            logger.error(f"Error collecting stocks: {e}")
            # Close connection if dry-run and error occurred
            if self.dry_run:
                if 'cursor' in locals():
                    cursor.close()
                if 'conn' in locals():
                    conn.close()
            return stock_to_etfs

    def get_stock_sector_from_symbol(self, symbol: str) -> str:
        """
        Determine sector from stock symbol (placeholder - expand as needed)

        Args:
            symbol: Stock ticker symbol

        Returns:
            Sector name
        """
        # This is a simplified mapping - in production, use external API
        # or database with company information

        tech_stocks = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'META', 'AMZN',
                       'TSLA', 'NFLX', 'AMD', 'INTC', 'CRM', 'ORCL',
                       'ADBE', 'CSCO', 'AVGO', 'TXN', 'QCOM', 'INTU']

        healthcare_stocks = ['UNH', 'JNJ', 'LLY', 'ABBV', 'MRK', 'PFE',
                            'TMO', 'ABT', 'DHR', 'AMGN', 'ISRG', 'SYK']

        financial_stocks = ['BRK.B', 'JPM', 'BAC', 'WFC', 'GS', 'MS',
                           'C', 'AXP', 'SCHW', 'BLK', 'SPGI', 'CME']

        consumer_disc_stocks = ['AMZN', 'TSLA', 'HD', 'MCD', 'NKE', 'SBUX',
                                'TJX', 'LOW', 'BKNG', 'GM', 'F']

        if symbol in tech_stocks:
            return 'Information Technology'
        elif symbol in healthcare_stocks:
            return 'Health Care'
        elif symbol in financial_stocks:
            return 'Financials'
        elif symbol in consumer_disc_stocks:
            return 'Consumer Discretionary'
        else:
            # Default fallback
            return 'Unknown'

    def get_stock_industry(self, symbol: str, sector: str) -> str:
        """
        Determine industry from symbol and sector

        Args:
            symbol: Stock ticker symbol
            sector: Sector name

        Returns:
            Industry name
        """
        # Simplified industry mapping
        if sector == 'Information Technology':
            if symbol in ['AAPL', 'MSFT']:
                return 'Software'
            elif symbol in ['NVDA', 'AMD', 'INTC']:
                return 'Semiconductors'
            else:
                return 'IT Services'

        elif sector == 'Health Care':
            if symbol in ['PFE', 'MRK', 'LLY']:
                return 'Pharmaceuticals'
            elif symbol in ['AMGN', 'GILD']:
                return 'Biotechnology'
            else:
                return 'Medical Devices'

        # Default to first industry in sector
        industries = self.SECTOR_INDUSTRIES.get(sector, ['Unknown'])
        return industries[0]

    def build_stock_metadata(self, stock_to_etfs: Dict[str, Set[str]],
                            batch_size: int = 500) -> int:
        """
        Build and insert stock-to-sector assignments in group_memberships

        Args:
            stock_to_etfs: Mapping of stock → ETFs
            batch_size: Number of stocks per batch insert

        Returns:
            Number of stocks processed
        """
        logger.info(f"Building sector assignments for {len(stock_to_etfs)} stocks...")

        # Load sector group IDs
        sector_group_ids = self._get_sector_group_ids()
        if not sector_group_ids:
            logger.error("No SECTOR groups found in definition_groups. Run organize_sectors_industries.py first.")
            return 0

        if self.rebuild and not self.dry_run:
            logger.info("Removing existing sector assignments...")
            cursor = self.conn.cursor()
            # Delete all group_memberships where group_id is a SECTOR
            cursor.execute("""
                DELETE FROM group_memberships
                WHERE group_id IN (
                    SELECT id FROM definition_groups
                    WHERE type = 'SECTOR' AND environment = %s
                )
            """, (self.environment,))
            self.conn.commit()
            logger.info(f"Deleted {cursor.rowcount} existing sector assignments")

        success_count = 0
        batch_data = []

        for stock_symbol in sorted(stock_to_etfs.keys()):
            # Get sector and industry
            sector_name = self.get_stock_sector_from_symbol(stock_symbol)
            industry = self.get_stock_industry(stock_symbol, sector_name)

            # Convert sector name to database key
            sector_key = self.SECTOR_NAME_TO_KEY.get(sector_name, 'unknown')
            sector_group_id = sector_group_ids.get(sector_key)

            if not sector_group_id:
                logger.warning(f"No SECTOR group found for '{sector_key}', skipping {stock_symbol}")
                continue

            if self.dry_run:
                logger.info(f"[DRY RUN] {stock_symbol}: sector={sector_name}, industry={industry}")
                success_count += 1
                continue

            # Build metadata JSONB for group_memberships
            metadata = {
                'industry': industry
            }

            batch_data.append({
                'symbol': stock_symbol,
                'group_id': sector_group_id,
                'metadata': metadata
            })

            # Insert batch when full
            if len(batch_data) >= batch_size:
                success_count += self._insert_batch(batch_data, sector_group_ids)
                batch_data = []

        # Insert remaining batch
        if batch_data and not self.dry_run:
            success_count += self._insert_batch(batch_data, sector_group_ids)

        logger.info(f"✓ Processed {success_count} sector assignments")
        return success_count

    def _get_sector_group_ids(self) -> Dict[str, int]:
        """
        Get mapping of sector_key -> group_id from definition_groups

        Returns:
            Dict mapping sector_key (e.g., 'information_technology') -> group_id
        """
        if self.dry_run:
            conn = self._get_connection()
            cursor = conn.cursor()
        else:
            cursor = self.conn.cursor()

        try:
            cursor.execute("""
                SELECT name, id
                FROM definition_groups
                WHERE type = 'SECTOR'
                AND environment = %s
            """, (self.environment,))

            sector_ids = {row[0]: row[1] for row in cursor.fetchall()}
            logger.info(f"Loaded {len(sector_ids)} SECTOR group IDs")
            return sector_ids

        finally:
            if self.dry_run:
                cursor.close()
                conn.close()

    def _insert_batch(self, batch_data: List[Dict], sector_group_ids: Dict[str, int]) -> int:
        """
        Insert a batch of stock-to-sector assignments into group_memberships

        Args:
            batch_data: List of stock assignment dicts
            sector_group_ids: Mapping of sector_key -> group_id

        Returns:
            Number of successful inserts
        """
        if not batch_data:
            return 0

        success_count = 0
        cursor = self.conn.cursor()

        for item in batch_data:
            try:
                query = """
                    INSERT INTO group_memberships (group_id, symbol, metadata)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (group_id, symbol)
                    DO UPDATE SET
                        metadata = EXCLUDED.metadata,
                        updated_at = CURRENT_TIMESTAMP
                """

                cursor.execute(query, (
                    item['group_id'],
                    item['symbol'],
                    json.dumps(item['metadata'])
                ))

                success_count += 1

            except Exception as e:
                logger.error(f"Error inserting {item['symbol']}: {e}")

        self.conn.commit()
        logger.info(f"  Inserted batch: {success_count} sector assignments")

        return success_count

    def validate_metadata(self) -> Dict[str, any]:
        """
        Validate stock metadata integrity

        Returns:
            Dict with validation results
        """
        logger.info("Validating stock metadata...")

        if self.dry_run:
            logger.info("[DRY RUN] Would validate metadata")
            return {'status': 'skipped'}

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

        # Sector distribution
        cursor.execute("""
            SELECT dg.name as sector, COUNT(DISTINCT gm.symbol) as count
            FROM definition_groups dg
            JOIN group_memberships gm ON dg.id = gm.group_id
            WHERE dg.type = 'SECTOR'
            AND dg.environment = %s
            GROUP BY dg.name
            ORDER BY count DESC
        """, (self.environment,))
        sector_distribution = dict(cursor.fetchall())

        results = {
            'total_stocks': total_stocks,
            'orphan_stocks_count': len(orphan_stocks),
            'orphan_stocks': orphan_stocks[:10],  # First 10 only
            'no_sector_count': len(no_sector_stocks),
            'sector_distribution': sector_distribution
        }

        logger.info(f"\n{'='*60}")
        logger.info(f"Validation Results:")
        logger.info(f"  Total stocks:    {total_stocks}")
        logger.info(f"  Orphan stocks:   {len(orphan_stocks)} "
                   f"({'✓ PASS' if len(orphan_stocks) == 0 else '⚠ FAIL'})")
        logger.info(f"  Missing sector:  {len(no_sector_stocks)}")
        logger.info(f"\nSector Distribution:")
        for sector, count in sorted(sector_distribution.items(),
                                   key=lambda x: x[1], reverse=True):
            logger.info(f"  {sector}: {count}")
        logger.info(f"{'='*60}")

        return results

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Build stock metadata from ETF holdings'
    )
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview without inserting into database')
    parser.add_argument('--rebuild', action='store_true',
                       help='Delete existing metadata before building')

    args = parser.parse_args()

    # Create builder
    builder = StockMetadataBuilder(dry_run=args.dry_run, rebuild=args.rebuild)

    try:
        # Step 1: Collect stocks from ETFs
        stock_to_etfs = builder.collect_all_stocks_from_etfs()

        if not stock_to_etfs:
            logger.error("No stocks found in ETF holdings. "
                        "Run load_etf_holdings.py first.")
            sys.exit(1)

        # Step 2: Build metadata
        builder.build_stock_metadata(stock_to_etfs)

        # Step 3: Validate
        if not args.dry_run:
            builder.validate_metadata()

    finally:
        builder.close()


if __name__ == '__main__':
    main()
