"""
Universe Loader - Sprint 60 Phase 1.2

Loads stock universe definitions (NASDAQ-100, S&P 500, Dow 30, Russell 3000)
into definition_groups and group_memberships tables.
Includes smart update logic with change detection via checksums.

Usage:
    python load_universes.py --mode dry-run         # Preview without inserting
    python load_universes.py --mode full            # Full reload (TRUNCATE+INSERT)
    python load_universes.py --mode incremental     # Update changed universes only
    python load_universes.py --rebuild              # Alias for --mode full
    python load_universes.py --universe nasdaq100   # Load specific universe only
"""

import os
import sys
import csv
import json
import argparse
import logging
import hashlib
from typing import List, Dict, Optional
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


class UniverseLoader:
    """Load stock universe definitions into relational structure"""

    # Universe definitions
    UNIVERSE_DEFINITIONS = {
        'nasdaq100': {
            'name': 'NASDAQ-100',
            'description': 'NASDAQ-100 Index - 100 largest non-financial companies on NASDAQ',
            'filename': 'nasdaq100.csv'
        },
        'sp500': {
            'name': 'S&P 500',
            'description': 'S&P 500 Index - 500 largest US publicly traded companies',
            'filename': 'sp500.csv'
        },
        'dow30': {
            'name': 'Dow Jones 30',
            'description': 'Dow Jones Industrial Average - 30 prominent US companies',
            'filename': 'dow30.csv'
        },
        'russell3000': {
            'name': 'Russell 3000',
            'description': 'Russell 3000 Index - 3000 largest US stocks',
            'filename': 'russell3000.csv'
        }
    }

    def __init__(self, universes_dir: str, mode: str = 'full'):
        """
        Initialize loader

        Args:
            universes_dir: Path to directory containing universe CSV files
            mode: Load mode ('full', 'incremental', 'dry-run')
        """
        self.universes_dir = universes_dir
        self.mode = mode
        self.dry_run = (mode == 'dry-run')
        self.config = get_config()
        self.db_uri = self.config.get('DATABASE_URI')
        self.conn = None if self.dry_run else self._get_connection()
        self.environment = os.getenv('ENVIRONMENT', 'DEFAULT')

        logger.info(f"UniverseLoader initialized in {mode.upper()} mode")

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

    def calculate_csv_checksum(self, csv_path: str) -> str:
        """
        Calculate MD5 checksum of CSV file for change detection

        Args:
            csv_path: Path to CSV file

        Returns:
            MD5 checksum as hex string
        """
        md5 = hashlib.md5()
        with open(csv_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5.update(chunk)
        return md5.hexdigest()

    def get_universe_metadata_from_db(self, universe_key: str) -> Optional[Dict[str, any]]:
        """
        Get existing universe metadata from database

        Args:
            universe_key: Universe key (e.g., 'nasdaq100')

        Returns:
            Metadata dict or None if not found
        """
        if self.dry_run:
            return None

        try:
            cursor = self.conn.cursor()
            query = """
                SELECT metadata, updated_at
                FROM definition_groups
                WHERE name = %s AND type = 'UNIVERSE' AND environment = %s
            """
            cursor.execute(query, (universe_key, self.environment))
            result = cursor.fetchone()

            if result:
                return {
                    'metadata': result[0],
                    'updated_at': result[1]
                }
            return None

        except Exception as e:
            logger.warning(f"Error reading metadata for {universe_key}: {e}")
            return None

    def has_universe_changed(self, universe_key: str, universe_data: Dict[str, any]) -> bool:
        """
        Check if universe has changed since last load

        Args:
            universe_key: Universe key
            universe_data: New universe data with checksum

        Returns:
            True if changed or new, False if unchanged
        """
        # Always reload in full mode
        if self.mode == 'full':
            return True

        # Get existing metadata from database
        db_metadata = self.get_universe_metadata_from_db(universe_key)

        if not db_metadata:
            logger.info(f"{universe_key}: New universe (not in database)")
            return True

        # Compare checksums
        old_checksum = db_metadata['metadata'].get('checksum', '')
        new_checksum = universe_data.get('checksum', '')

        if old_checksum != new_checksum:
            logger.info(f"{universe_key}: Changed (checksum mismatch)")
            logger.debug(f"  Old: {old_checksum[:8]}... | New: {new_checksum[:8]}...")
            return True

        logger.info(f"{universe_key}: Unchanged (skipping)")
        return False

    def validate_universe_data(self, universe_data: Dict[str, any]) -> tuple[bool, List[str]]:
        """
        Pre-load validation: Check for data quality issues

        Args:
            universe_data: Universe data to validate

        Returns:
            Tuple of (is_valid, list of warnings)
        """
        warnings = []

        # Check for empty symbols
        if not universe_data.get('symbols'):
            warnings.append(f"Universe has no symbols")
            return False, warnings

        symbols = universe_data['symbols']

        # Check for duplicate symbols
        seen = set()
        duplicates = []
        for symbol in symbols:
            if symbol in seen:
                duplicates.append(symbol)
            seen.add(symbol)

        if duplicates:
            warnings.append(f"Duplicate symbols found: {', '.join(duplicates[:5])}")
            if len(duplicates) > 5:
                warnings.append(f"  ... and {len(duplicates) - 5} more duplicates")

        # Check for invalid symbols
        invalid_symbols = [s for s in symbols if not s or len(s) > 10 or not s.replace('-', '').replace('.', '').isalnum()]
        if invalid_symbols:
            warnings.append(f"Invalid symbols: {', '.join(invalid_symbols[:5])}")
            if len(invalid_symbols) > 5:
                warnings.append(f"  ... and {len(invalid_symbols) - 5} more invalid")

        # Determine if critical errors exist
        is_valid = len(duplicates) == 0 and len(invalid_symbols) == 0

        return is_valid, warnings

    def load_universe_csv(self, universe_key: str) -> Optional[Dict[str, any]]:
        """
        Load symbols for a single universe from CSV

        Args:
            universe_key: Universe key (e.g., 'nasdaq100')

        Returns:
            Dict with universe data or None if not found
        """
        universe_def = self.UNIVERSE_DEFINITIONS.get(universe_key)
        if not universe_def:
            logger.error(f"Unknown universe: {universe_key}")
            return None

        csv_filename = universe_def['filename']
        csv_path = os.path.join(self.universes_dir, csv_filename)

        if not os.path.exists(csv_path):
            logger.warning(f"Universe CSV not found: {csv_path}")
            return None

        # Read CSV file
        symbols = []
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                # Peek at first line to detect if header exists
                first_line = f.readline().strip()
                f.seek(0)

                # If first line is "ticker" or "symbol", use DictReader
                if first_line.lower() in ['ticker', 'symbol']:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # Handle both lowercase and capitalized column names
                        symbol = (row.get('ticker') or row.get('Ticker') or
                                 row.get('symbol') or row.get('Symbol') or '').strip()
                        if symbol:
                            symbols.append(symbol)
                else:
                    # No header, just read symbols line by line
                    for line in f:
                        symbol = line.strip()
                        if symbol:
                            symbols.append(symbol)

        except Exception as e:
            logger.error(f"Error reading {csv_filename}: {e}")
            return None

        # Calculate checksum for change detection
        checksum = self.calculate_csv_checksum(csv_path)

        logger.info(f"Loaded {len(symbols)} symbols for {universe_key} from {csv_filename}")

        return {
            'universe_key': universe_key,
            'name': universe_def['name'],
            'description': universe_def['description'],
            'symbols': symbols,
            'total_symbols': len(symbols),
            'last_updated': datetime.now().isoformat(),
            'data_source': csv_filename,
            'checksum': checksum
        }

    def insert_universe(self, universe_data: Dict[str, any]) -> bool:
        """
        Insert universe into definition_groups and group_memberships

        Args:
            universe_data: Universe data dict

        Returns:
            True if successful, False otherwise
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would insert {universe_data['universe_key']} "
                       f"with {universe_data['total_symbols']} symbols")
            return True

        try:
            cursor = self.conn.cursor()

            # Prepare metadata JSON
            metadata = {
                'total_symbols': universe_data['total_symbols'],
                'data_source': universe_data['data_source'],
                'last_updated': universe_data['last_updated'],
                'checksum': universe_data.get('checksum', '')
            }

            # Insert into definition_groups (or update if exists)
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
                universe_data['universe_key'],
                'UNIVERSE',
                universe_data['description'],
                json.dumps(metadata),
                self.environment
            ))

            group_id = cursor.fetchone()[0]

            # Delete existing memberships for this group (for clean reload)
            cursor.execute("""
                DELETE FROM group_memberships
                WHERE group_id = %s
            """, (group_id,))

            # Insert new memberships
            for symbol in universe_data['symbols']:
                cursor.execute("""
                    INSERT INTO group_memberships (group_id, symbol)
                    VALUES (%s, %s)
                    ON CONFLICT (group_id, symbol) DO NOTHING
                """, (group_id, symbol))

            self.conn.commit()

            logger.info(f"✓ Inserted {universe_data['universe_key']} "
                       f"(group_id: {group_id}, symbols: {universe_data['total_symbols']})")
            return True

        except Exception as e:
            logger.error(f"Error inserting {universe_data['universe_key']}: {e}")
            if self.conn:
                self.conn.rollback()
            return False

    def load_all_universes(self, specific_universe: Optional[str] = None):
        """
        Load all universes or a specific one

        Args:
            specific_universe: If provided, load only this universe
        """
        if specific_universe:
            universe_keys = [specific_universe.lower()]
        else:
            universe_keys = list(self.UNIVERSE_DEFINITIONS.keys())

        logger.info(f"Loading {len(universe_keys)} universe(s): {universe_keys}")

        success_count = 0
        failed_count = 0
        skipped_count = 0
        validation_failed_count = 0

        for universe_key in universe_keys:
            universe_data = self.load_universe_csv(universe_key)

            if universe_data:
                # Pre-load validation
                is_valid, warnings = self.validate_universe_data(universe_data)
                if warnings:
                    for warning in warnings:
                        logger.warning(f"{universe_key}: {warning}")

                if not is_valid:
                    logger.error(f"{universe_key}: Pre-load validation failed, skipping")
                    validation_failed_count += 1
                    failed_count += 1
                    continue

                # In incremental mode, check if universe has changed
                if self.mode == 'incremental' and not self.has_universe_changed(universe_key, universe_data):
                    skipped_count += 1
                    continue

                if self.insert_universe(universe_data):
                    success_count += 1
                else:
                    failed_count += 1
            else:
                failed_count += 1

        logger.info(f"\n{'='*60}")
        logger.info(f"Load Summary ({self.mode.upper()} mode):")
        logger.info(f"  Success: {success_count}")
        logger.info(f"  Failed:  {failed_count}")
        if validation_failed_count > 0:
            logger.info(f"    - Validation failed: {validation_failed_count}")
        if self.mode == 'incremental':
            logger.info(f"  Skipped: {skipped_count} (unchanged)")
        logger.info(f"  Total:   {len(universe_keys)}")
        logger.info(f"{'='*60}")

        # Post-load validation (run if any universes were loaded)
        if success_count > 0 and not self.dry_run:
            logger.info("")
            if not self.run_post_load_validation():
                logger.warning("Post-load validation failed - see errors above")
                return False

        return True

    def run_post_load_validation(self) -> bool:
        """
        Post-load validation: Run validate_relationships.py

        Returns:
            True if validation passed, False otherwise
        """
        try:
            import subprocess
            script_path = os.path.join(os.path.dirname(__file__), 'validate_relationships.py')

            logger.info("Running post-load validation...")
            result = subprocess.run(
                ['python', script_path],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                logger.info("✓ Post-load validation passed")
                return True
            else:
                logger.error(f"✗ Post-load validation failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("✗ Post-load validation timed out (>60s)")
            return False
        except Exception as e:
            logger.error(f"✗ Error running post-load validation: {e}")
            return False

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Load stock universe definitions into definition_groups and group_memberships'
    )
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview without inserting into database')
    parser.add_argument('--universe', type=str,
                       help='Load specific universe only (nasdaq100, sp500, dow30, russell3000)')
    parser.add_argument('--mode', type=str, choices=['full', 'incremental', 'dry-run'],
                       default='full',
                       help='Load mode: full (TRUNCATE+INSERT), incremental (update changed only), dry-run (preview)')
    parser.add_argument('--rebuild', action='store_true',
                       help='Force full rebuild (alias for --mode full)')

    args = parser.parse_args()

    # Handle --rebuild flag (overrides --mode)
    if args.rebuild:
        args.mode = 'full'

    # Handle --dry-run flag (overrides --mode)
    if args.dry_run:
        args.mode = 'dry-run'

    # Determine universes directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    universes_dir = os.path.join(script_dir, 'holdings')  # Universe CSV files are in holdings/

    if not os.path.exists(universes_dir):
        logger.error(f"Holdings directory not found: {universes_dir}")
        return

    # Create loader and run
    loader = UniverseLoader(universes_dir, mode=args.mode)

    try:
        loader.load_all_universes(specific_universe=args.universe)
    finally:
        loader.close()


if __name__ == '__main__':
    main()
