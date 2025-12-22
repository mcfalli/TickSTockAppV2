"""
Sector & Industry Organizer for Sprint 58

Creates hierarchical sector/industry mappings in cache_entries.
Defines 11 GICS sectors with industry classifications and representative stocks.

Usage:
    python organize_sectors_industries.py --dry-run    # Preview without inserting
    python organize_sectors_industries.py              # Create sector mappings
"""

import os
import sys
import json
import argparse
import logging
from typing import List, Dict
from datetime import datetime

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


class SectorIndustryOrganizer:
    """Organize GICS sectors and industries"""

    # 11 GICS Sectors with industries and representative stocks
    SECTOR_DEFINITIONS = {
        'information_technology': {
            'name': 'Information Technology',
            'industries': [
                'Software',
                'Hardware',
                'Semiconductors',
                'IT Services',
                'Electronic Equipment'
            ],
            'representative_stocks': ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'META'],
            'description': 'Technology hardware, software, and IT services'
        },
        'health_care': {
            'name': 'Health Care',
            'industries': [
                'Pharmaceuticals',
                'Biotechnology',
                'Medical Devices',
                'Healthcare Services',
                'Healthcare Equipment'
            ],
            'representative_stocks': ['UNH', 'JNJ', 'LLY', 'ABBV', 'MRK'],
            'description': 'Healthcare providers, pharmaceuticals, and biotechnology'
        },
        'financials': {
            'name': 'Financials',
            'industries': [
                'Banks',
                'Insurance',
                'Capital Markets',
                'Financial Services',
                'Consumer Finance'
            ],
            'representative_stocks': ['BRK.B', 'JPM', 'BAC', 'WFC', 'GS'],
            'description': 'Banking, insurance, and financial services'
        },
        'consumer_discretionary': {
            'name': 'Consumer Discretionary',
            'industries': [
                'Retail',
                'Automobiles',
                'Hotels & Restaurants',
                'Consumer Durables',
                'Leisure Products'
            ],
            'representative_stocks': ['AMZN', 'TSLA', 'HD', 'MCD', 'NKE'],
            'description': 'Non-essential goods and services'
        },
        'communication_services': {
            'name': 'Communication Services',
            'industries': [
                'Telecommunications',
                'Media',
                'Entertainment',
                'Interactive Media',
                'Wireless Services'
            ],
            'representative_stocks': ['GOOGL', 'META', 'NFLX', 'DIS', 'CMCSA'],
            'description': 'Telecommunications, media, and entertainment'
        },
        'industrials': {
            'name': 'Industrials',
            'industries': [
                'Aerospace & Defense',
                'Construction',
                'Machinery',
                'Transportation',
                'Commercial Services'
            ],
            'representative_stocks': ['BA', 'HON', 'UNP', 'CAT', 'GE'],
            'description': 'Manufacturing, construction, and transportation'
        },
        'consumer_staples': {
            'name': 'Consumer Staples',
            'industries': [
                'Food & Beverage',
                'Household Products',
                'Personal Products',
                'Tobacco',
                'Food Retail'
            ],
            'representative_stocks': ['PG', 'KO', 'PEP', 'WMT', 'COST'],
            'description': 'Essential consumer goods'
        },
        'energy': {
            'name': 'Energy',
            'industries': [
                'Oil & Gas Exploration',
                'Oil & Gas Refining',
                'Energy Equipment',
                'Integrated Oil & Gas'
            ],
            'representative_stocks': ['XOM', 'CVX', 'COP', 'SLB', 'EOG'],
            'description': 'Oil, gas, and energy equipment'
        },
        'utilities': {
            'name': 'Utilities',
            'industries': [
                'Electric Utilities',
                'Gas Utilities',
                'Water Utilities',
                'Multi-Utilities',
                'Renewable Energy'
            ],
            'representative_stocks': ['NEE', 'DUK', 'SO', 'D', 'AEP'],
            'description': 'Electric, gas, and water utilities'
        },
        'real_estate': {
            'name': 'Real Estate',
            'industries': [
                'REITs - Residential',
                'REITs - Commercial',
                'Real Estate Services',
                'Real Estate Development'
            ],
            'representative_stocks': ['PLD', 'AMT', 'CCI', 'EQIX', 'PSA'],
            'description': 'Real estate investment trusts and services'
        },
        'materials': {
            'name': 'Materials',
            'industries': [
                'Chemicals',
                'Metals & Mining',
                'Paper & Forest Products',
                'Construction Materials',
                'Containers & Packaging'
            ],
            'representative_stocks': ['LIN', 'APD', 'SHW', 'FCX', 'NEM'],
            'description': 'Basic materials and chemicals'
        }
    }

    def __init__(self, dry_run: bool = False):
        """
        Initialize organizer

        Args:
            dry_run: If True, preview without database insertion
        """
        self.dry_run = dry_run
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

    def get_stock_counts_by_sector(self) -> Dict[str, int]:
        """
        Query actual stock counts per sector from group_memberships

        Returns:
            Dict mapping sector_key → stock count
        """
        if self.dry_run:
            logger.info("[DRY RUN] Would query stock counts by sector")
            return {}

        try:
            cursor = self.conn.cursor()
            query = """
                SELECT
                    dg.name as sector_key,
                    COUNT(DISTINCT gm.symbol) as stock_count
                FROM definition_groups dg
                JOIN group_memberships gm ON dg.id = gm.group_id
                WHERE dg.type = 'SECTOR'
                AND dg.environment = %s
                GROUP BY dg.name
            """
            cursor.execute(query, (self.environment,))

            sector_counts = {}
            for row in cursor.fetchall():
                sector_key = row[0]
                count = row[1]
                sector_counts[sector_key] = count

            return sector_counts

        except Exception as e:
            logger.error(f"Error querying stock counts: {e}")
            return {}

    def create_sector_entries(self) -> int:
        """
        Create sector_industry_map entries in cache_entries

        Returns:
            Number of sectors created
        """
        logger.info(f"Creating sector/industry mappings for "
                   f"{len(self.SECTOR_DEFINITIONS)} sectors...")

        # Get actual stock counts
        stock_counts = self.get_stock_counts_by_sector()

        success_count = 0

        for sector_key, sector_data in self.SECTOR_DEFINITIONS.items():
            sector_name = sector_data['name']

            # Get actual stock count for this sector (by sector_key)
            stock_count = stock_counts.get(sector_key, 0)

            # Build value JSON
            value_json = {
                'industries': sector_data['industries'],
                'representative_stocks': sector_data['representative_stocks'],
                'description': sector_data['description'],
                'stock_count': stock_count,
                'last_updated': datetime.now().isoformat()
            }

            if self.dry_run:
                logger.info(f"[DRY RUN] {sector_key}: {len(sector_data['industries'])} "
                           f"industries, {stock_count} stocks")
                success_count += 1
                continue

            # Insert into database
            try:
                cursor = self.conn.cursor()

                # Build metadata JSON for definition_groups
                metadata = {
                    'industries': value_json['industries'],
                    'representative_stocks': value_json['representative_stocks'],
                    'stock_count': value_json['stock_count'],
                    'last_updated': value_json['last_updated']
                }

                query = """
                    INSERT INTO definition_groups
                        (name, type, description, metadata, environment)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (name, type, environment)
                    DO UPDATE SET
                        description = EXCLUDED.description,
                        metadata = EXCLUDED.metadata,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING id
                """

                cursor.execute(query, (
                    sector_key,                  # name
                    'SECTOR',                    # type
                    sector_data['description'],  # description
                    json.dumps(metadata),        # metadata JSONB
                    self.environment
                ))

                result = cursor.fetchone()
                self.conn.commit()

                logger.info(f"✓ {sector_name}: {len(sector_data['industries'])} "
                           f"industries, {stock_count} stocks (id: {result[0]})")
                success_count += 1

            except Exception as e:
                logger.error(f"Error inserting {sector_name}: {e}")
                if self.conn:
                    self.conn.rollback()

        logger.info(f"\n{'='*60}")
        logger.info(f"Created {success_count} sector entries")
        logger.info(f"{'='*60}")

        return success_count

    def validate_sector_mappings(self):
        """Validate sector/industry mappings"""
        logger.info("Validating sector mappings...")

        if self.dry_run:
            logger.info("[DRY RUN] Would validate sector mappings")
            return

        try:
            cursor = self.conn.cursor()

            # Count sector entries in definition_groups
            cursor.execute("""
                SELECT COUNT(*)
                FROM definition_groups
                WHERE type = 'SECTOR'
                AND environment = %s
            """, (self.environment,))
            sector_count = cursor.fetchone()[0]

            # Get total industries across all sectors
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

            total_industries = 0
            logger.info(f"\n{'='*60}")
            logger.info(f"Sector Validation:")
            logger.info(f"  Total sectors: {sector_count}/11 "
                       f"({'✓ PASS' if sector_count == 11 else '⚠ FAIL'})")
            logger.info(f"\nIndustries per sector:")

            for row in cursor.fetchall():
                sector_key = row[0]
                industry_count = row[1]
                stock_count = row[2]
                total_industries += industry_count
                logger.info(f"  {sector_key}: {industry_count} industries, "
                           f"{stock_count} stocks")

            logger.info(f"\n  Total industries: {total_industries}")
            logger.info(f"{'='*60}")

        except Exception as e:
            logger.error(f"Error validating sectors: {e}")

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Organize GICS sectors and industries in cache_entries'
    )
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview without inserting into database')

    args = parser.parse_args()

    # Create organizer
    organizer = SectorIndustryOrganizer(dry_run=args.dry_run)

    try:
        # Create sector entries
        organizer.create_sector_entries()

        # Validate
        if not args.dry_run:
            organizer.validate_sector_mappings()

    finally:
        organizer.close()


if __name__ == '__main__':
    main()
