"""
Data Migration Script: cache_entries → definition_groups + group_memberships

Migrates Sprint 58 data from JSONB-based cache_entries to relational structure.

Usage:
    python migrate_to_new_tables.py --dry-run   # Preview migration
    python migrate_to_new_tables.py             # Execute migration
    python migrate_to_new_tables.py --rollback  # Delete migrated data
"""

import os
import sys
import argparse
import logging
import json
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


class CacheEntriesMigration:
    """Migrate cache_entries to definition_groups + group_memberships"""

    def __init__(self, dry_run=False):
        """Initialize migration"""
        self.config = get_config()
        self.db_uri = self.config.get('DATABASE_URI')
        self.conn = self._get_connection()
        self.dry_run = dry_run
        self.environment = 'DEFAULT'

        # Migration stats
        self.stats = {
            'groups_created': 0,
            'memberships_created': 0,
            'etfs_migrated': 0,
            'themes_migrated': 0,
            'sectors_migrated': 0,
            'errors': []
        }

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

    def migrate_etf_holdings(self):
        """Migrate etf_holdings → definition_groups (type='ETF')"""
        logger.info("Migrating ETF holdings...")

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT
                key,
                name,
                value->'holdings' as holdings,
                value->>'total_holdings' as total_holdings,
                value->>'market_cap_threshold' as threshold,
                value->>'data_source' as source,
                value->>'last_updated' as last_updated
            FROM cache_entries
            WHERE type = 'etf_holdings'
            AND environment = %s
        """, (self.environment,))

        etfs = cursor.fetchall()
        logger.info(f"Found {len(etfs)} ETFs to migrate")

        for etf_key, etf_name, holdings_json, total_holdings, threshold, source, last_updated in etfs:
            try:
                # Parse holdings array from JSONB
                if isinstance(holdings_json, str):
                    holdings = json.loads(holdings_json)
                elif isinstance(holdings_json, list):
                    holdings = holdings_json
                else:
                    # Already parsed JSONB
                    holdings = holdings_json if holdings_json else []

                if not holdings:
                    logger.warning(f"Skipping {etf_key}: no holdings")
                    continue

                # Create metadata JSON
                metadata = {
                    'total_holdings': int(total_holdings) if total_holdings else len(holdings),
                    'data_source': source,
                    'last_updated': last_updated
                }

                # Create liquidity filter JSON
                liquidity_filter = {
                    'market_cap_threshold': float(threshold) if threshold else None
                }

                if self.dry_run:
                    logger.info(f"[DRY-RUN] Would create ETF: {etf_key} with {len(holdings)} holdings")
                else:
                    # Insert into definition_groups
                    cursor.execute("""
                        INSERT INTO definition_groups
                            (name, type, description, metadata, liquidity_filter, environment)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (name, type, environment) DO UPDATE
                        SET metadata = EXCLUDED.metadata,
                            liquidity_filter = EXCLUDED.liquidity_filter,
                            updated_at = CURRENT_TIMESTAMP
                        RETURNING id
                    """, (
                        etf_key,
                        'ETF',
                        etf_name,
                        json.dumps(metadata),
                        json.dumps(liquidity_filter),
                        self.environment
                    ))

                    group_id = cursor.fetchone()[0]
                    self.stats['groups_created'] += 1

                    # Insert holdings into group_memberships
                    for symbol in holdings:
                        cursor.execute("""
                            INSERT INTO group_memberships (group_id, symbol)
                            VALUES (%s, %s)
                            ON CONFLICT (group_id, symbol) DO NOTHING
                        """, (group_id, symbol))
                        self.stats['memberships_created'] += 1

                    logger.info(f"✓ Migrated ETF: {etf_key} ({len(holdings)} holdings)")

                self.stats['etfs_migrated'] += 1

            except Exception as e:
                logger.error(f"Error migrating ETF {etf_key}: {e}")
                self.stats['errors'].append(f"ETF {etf_key}: {str(e)}")

        if not self.dry_run:
            self.conn.commit()

    def migrate_theme_definitions(self):
        """Migrate theme_definition → definition_groups (type='THEME')"""
        logger.info("Migrating theme definitions...")

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT
                key,
                name,
                value->'symbols' as symbols,
                value->>'description' as description,
                value->>'selection_criteria' as criteria,
                value->'related_themes' as related_themes
            FROM cache_entries
            WHERE type = 'theme_definition'
            AND environment = %s
        """, (self.environment,))

        themes = cursor.fetchall()
        logger.info(f"Found {len(themes)} themes to migrate")

        for theme_key, theme_name, symbols_json, description, criteria, related_themes in themes:
            try:
                # Parse symbols array
                if isinstance(symbols_json, str):
                    symbols = json.loads(symbols_json)
                elif isinstance(symbols_json, list):
                    symbols = symbols_json
                else:
                    symbols = symbols_json if symbols_json else []

                if not symbols:
                    logger.warning(f"Skipping {theme_key}: no symbols")
                    continue

                metadata = {
                    'selection_criteria': criteria,
                    'related_themes': related_themes
                }

                if self.dry_run:
                    logger.info(f"[DRY-RUN] Would create theme: {theme_key} with {len(symbols)} symbols")
                else:
                    cursor.execute("""
                        INSERT INTO definition_groups
                            (name, type, description, metadata, environment)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (name, type, environment) DO UPDATE
                        SET description = EXCLUDED.description,
                            metadata = EXCLUDED.metadata,
                            updated_at = CURRENT_TIMESTAMP
                        RETURNING id
                    """, (
                        theme_key,
                        'THEME',
                        description,
                        json.dumps(metadata),
                        self.environment
                    ))

                    group_id = cursor.fetchone()[0]
                    self.stats['groups_created'] += 1

                    for symbol in symbols:
                        cursor.execute("""
                            INSERT INTO group_memberships (group_id, symbol)
                            VALUES (%s, %s)
                            ON CONFLICT (group_id, symbol) DO NOTHING
                        """, (group_id, symbol))
                        self.stats['memberships_created'] += 1

                    logger.info(f"✓ Migrated theme: {theme_key} ({len(symbols)} symbols)")

                self.stats['themes_migrated'] += 1

            except Exception as e:
                logger.error(f"Error migrating theme {theme_key}: {e}")
                self.stats['errors'].append(f"Theme {theme_key}: {str(e)}")

        if not self.dry_run:
            self.conn.commit()

    def migrate_sector_definitions(self):
        """Migrate sector_industry_map → definition_groups (type='SECTOR')"""
        logger.info("Migrating sector definitions...")

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT
                key,
                name,
                value->'industries' as industries,
                value->'representative_stocks' as rep_stocks,
                value->>'description' as description
            FROM cache_entries
            WHERE type = 'sector_industry_map'
            AND environment = %s
        """, (self.environment,))

        sectors = cursor.fetchall()
        logger.info(f"Found {len(sectors)} sectors to migrate")

        for sector_key, sector_name, industries_json, rep_stocks_json, description in sectors:
            try:
                # Parse arrays
                if isinstance(industries_json, str):
                    industries = json.loads(industries_json)
                elif isinstance(industries_json, list):
                    industries = industries_json
                else:
                    industries = industries_json if industries_json else []

                if isinstance(rep_stocks_json, str):
                    rep_stocks = json.loads(rep_stocks_json)
                elif isinstance(rep_stocks_json, list):
                    rep_stocks = rep_stocks_json
                else:
                    rep_stocks = rep_stocks_json if rep_stocks_json else []

                metadata = {
                    'industries': industries,
                    'representative_stocks': rep_stocks
                }

                if self.dry_run:
                    logger.info(f"[DRY-RUN] Would create sector: {sector_key}")
                else:
                    cursor.execute("""
                        INSERT INTO definition_groups
                            (name, type, description, metadata, environment)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (name, type, environment) DO UPDATE
                        SET description = EXCLUDED.description,
                            metadata = EXCLUDED.metadata,
                            updated_at = CURRENT_TIMESTAMP
                        RETURNING id
                    """, (
                        sector_key,
                        'SECTOR',
                        description,
                        json.dumps(metadata),
                        self.environment
                    ))

                    self.stats['groups_created'] += 1
                    logger.info(f"✓ Migrated sector: {sector_key}")

                self.stats['sectors_migrated'] += 1

            except Exception as e:
                logger.error(f"Error migrating sector {sector_key}: {e}")
                self.stats['errors'].append(f"Sector {sector_key}: {str(e)}")

        if not self.dry_run:
            self.conn.commit()

    def print_summary(self):
        """Print migration summary"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("MIGRATION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"ETFs migrated:        {self.stats['etfs_migrated']}")
        logger.info(f"Themes migrated:      {self.stats['themes_migrated']}")
        logger.info(f"Sectors migrated:     {self.stats['sectors_migrated']}")
        logger.info(f"Groups created:       {self.stats['groups_created']}")
        logger.info(f"Memberships created:  {self.stats['memberships_created']}")
        logger.info(f"Errors:               {len(self.stats['errors'])}")

        if self.stats['errors']:
            logger.error("\nErrors encountered:")
            for error in self.stats['errors']:
                logger.error(f"  - {error}")

        logger.info("=" * 60)

    def validate_migration(self):
        """Validate migrated data"""
        logger.info("\nValidating migration...")

        cursor = self.conn.cursor()

        # Count groups by type
        cursor.execute("""
            SELECT type, COUNT(*)
            FROM definition_groups
            WHERE environment = %s
            GROUP BY type
        """, (self.environment,))

        logger.info("\nGroups by type:")
        for group_type, count in cursor.fetchall():
            logger.info(f"  {group_type}: {count}")

        # Count total memberships
        cursor.execute("""
            SELECT COUNT(*) FROM group_memberships gm
            JOIN definition_groups dg ON gm.group_id = dg.id
            WHERE dg.environment = %s
        """, (self.environment,))

        total_memberships = cursor.fetchone()[0]
        logger.info(f"\nTotal memberships: {total_memberships}")

        # Count unique symbols
        cursor.execute("""
            SELECT COUNT(DISTINCT gm.symbol) FROM group_memberships gm
            JOIN definition_groups dg ON gm.group_id = dg.id
            WHERE dg.environment = %s
        """, (self.environment,))

        unique_symbols = cursor.fetchone()[0]
        logger.info(f"Unique symbols: {unique_symbols}")

    def rollback(self):
        """Delete all migrated data"""
        logger.warning("Rolling back migration...")

        cursor = self.conn.cursor()

        if self.dry_run:
            logger.info("[DRY-RUN] Would delete all migrated data")
        else:
            # Delete all groups for this environment (cascade will delete memberships)
            cursor.execute("""
                DELETE FROM definition_groups
                WHERE environment = %s
            """, (self.environment,))

            deleted = cursor.rowcount
            self.conn.commit()
            logger.info(f"✓ Deleted {deleted} groups (and their memberships)")


def main():
    parser = argparse.ArgumentParser(description='Migrate cache_entries to new relational tables')
    parser.add_argument('--dry-run', action='store_true', help='Preview migration without changes')
    parser.add_argument('--rollback', action='store_true', help='Delete migrated data')
    parser.add_argument('--validate-only', action='store_true', help='Only run validation')
    args = parser.parse_args()

    migration = CacheEntriesMigration(dry_run=args.dry_run)

    if args.rollback:
        migration.rollback()
        return

    if args.validate_only:
        migration.validate_migration()
        return

    mode = "[DRY-RUN] " if args.dry_run else ""
    logger.info(f"{mode}Starting migration...")

    # Run migrations
    migration.migrate_etf_holdings()
    migration.migrate_theme_definitions()
    migration.migrate_sector_definitions()

    # Print summary
    migration.print_summary()

    # Validate if not dry-run
    if not args.dry_run:
        migration.validate_migration()

    logger.info("\n✅ Migration complete!")


if __name__ == '__main__':
    main()
