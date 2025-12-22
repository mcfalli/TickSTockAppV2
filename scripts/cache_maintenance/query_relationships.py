"""
Relationship Query Helper for Sprint 58 Phase 5

Provides convenient query functions for ETF-stock relationships,
sector mappings, and theme definitions.

Usage:
    python query_relationships.py --etf SPY              # Get SPY holdings
    python query_relationships.py --stock AAPL           # Get AAPL's ETFs
    python query_relationships.py --sector technology    # Get tech stocks
    python query_relationships.py --theme crypto_miners  # Get crypto miners
    python query_relationships.py --stats                # Show statistics
"""

import os
import sys
import argparse
import json
import logging
from typing import List, Dict, Optional

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import psycopg2
from urllib.parse import urlparse
from src.core.services.config_manager import get_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


class RelationshipQuery:
    """Query helper for ETF-stock relationships"""

    def __init__(self):
        """Initialize query helper"""
        self.config = get_config()
        self.db_uri = self.config.get('DATABASE_URI')
        self.conn = self._get_connection()
        self.environment = os.getenv('ENVIRONMENT', 'DEFAULT')

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

    def get_etf_holdings(self, etf_symbol: str) -> Optional[Dict[str, any]]:
        """
        Get holdings for an ETF from definition_groups + group_memberships

        Args:
            etf_symbol: ETF ticker symbol

        Returns:
            Dict with holdings data or None if not found
        """
        cursor = self.conn.cursor()
        
        # Get ETF definition
        cursor.execute("""
            SELECT
                dg.name,
                dg.description,
                dg.metadata->>'total_holdings' as total_holdings,
                dg.liquidity_filter->>'market_cap_threshold' as threshold,
                dg.metadata->>'last_updated' as last_updated,
                dg.id
            FROM definition_groups dg
            WHERE dg.type = 'ETF'
            AND dg.name = %s
            AND dg.environment = %s
        """, (etf_symbol.upper(), self.environment))

        row = cursor.fetchone()
        if not row:
            return None

        group_id = row[5]
        
        # Get holdings from group_memberships
        cursor.execute("""
            SELECT symbol
            FROM group_memberships
            WHERE group_id = %s
            ORDER BY symbol
        """, (group_id,))
        
        holdings = [r[0] for r in cursor.fetchall()]

        return {
            'etf_symbol': row[0],
            'name': row[1],
            'holdings': holdings,
            'total_holdings': int(row[2]) if row[2] else len(holdings),
            'market_cap_threshold': float(row[3]) if row[3] else 0,
            'last_updated': row[4]
        }

    def get_stock_etfs(self, stock_symbol: str) -> Optional[Dict[str, any]]:
        """
        Get ETFs containing a stock

        Args:
            stock_symbol: Stock ticker symbol

        Returns:
            Dict with stock data or None if not found
        """
        cursor = self.conn.cursor()
        
        # Get ETF memberships
        cursor.execute("""
            SELECT dg.name
            FROM group_memberships gm
            JOIN definition_groups dg ON gm.group_id = dg.id
            WHERE gm.symbol = %s
            AND dg.type = 'ETF'
            AND dg.environment = %s
            ORDER BY dg.name
        """, (stock_symbol.upper(), self.environment))
        etf_memberships = [row[0] for row in cursor.fetchall()]
        
        # Get sector and industry
        cursor.execute("""
            SELECT dg.name, gm.metadata->>'industry'
            FROM group_memberships gm
            JOIN definition_groups dg ON gm.group_id = dg.id
            WHERE gm.symbol = %s
            AND dg.type = 'SECTOR'
            AND dg.environment = %s
            LIMIT 1
        """, (stock_symbol.upper(), self.environment))
        sector_row = cursor.fetchone()
        sector = sector_row[0] if sector_row else None
        industry = sector_row[1] if sector_row else None
        
        # Get theme memberships
        cursor.execute("""
            SELECT dg.name
            FROM group_memberships gm
            JOIN definition_groups dg ON gm.group_id = dg.id
            WHERE gm.symbol = %s
            AND dg.type = 'THEME'
            AND dg.environment = %s
            ORDER BY dg.name
        """, (stock_symbol.upper(), self.environment))
        theme_memberships = [row[0] for row in cursor.fetchall()]
        
        # Return None if stock not found in any group
        if not etf_memberships and not sector and not theme_memberships:
            return None
        
        return {
            'stock_symbol': stock_symbol.upper(),
            'name': stock_symbol.upper(),  # Name not available in new structure
            'member_of_etfs': etf_memberships,
            'sector': sector,
            'industry': industry,
            'member_of_themes': theme_memberships
        }

    def get_stocks_by_sector(self, sector_name: str) -> List[Dict[str, any]]:
        """
        Get all stocks in a sector

        Args:
            sector_name: Sector name or key (e.g., 'information_technology')

        Returns:
            List of stock dicts
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT
                gm.symbol,
                dg.name as sector,
                gm.metadata->>'industry' as industry,
                (
                    SELECT COUNT(*)
                    FROM group_memberships gm2
                    JOIN definition_groups dg2 ON gm2.group_id = dg2.id
                    WHERE gm2.symbol = gm.symbol
                    AND dg2.type = 'ETF'
                    AND dg2.environment = %s
                ) as etf_count
            FROM group_memberships gm
            JOIN definition_groups dg ON gm.group_id = dg.id
            WHERE dg.type = 'SECTOR'
            AND dg.environment = %s
            AND dg.name ILIKE %s
            ORDER BY gm.symbol
        """, (self.environment, self.environment, f'%{sector_name}%'))

        stocks = []
        for row in cursor.fetchall():
            stocks.append({
                'symbol': row[0],
                'sector': row[1],
                'industry': row[2],
                'etf_count': row[3]
            })

        return stocks

    def get_stocks_by_industry(self, industry_name: str) -> List[Dict[str, any]]:
        """
        Get all stocks in an industry

        Args:
            industry_name: Industry name (e.g., 'Software')

        Returns:
            List of stock dicts
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT
                gm.symbol,
                dg.name as sector,
                gm.metadata->>'industry' as industry,
                (
                    SELECT COUNT(*)
                    FROM group_memberships gm2
                    JOIN definition_groups dg2 ON gm2.group_id = dg2.id
                    WHERE gm2.symbol = gm.symbol
                    AND dg2.type = 'ETF'
                    AND dg2.environment = %s
                ) as etf_count
            FROM group_memberships gm
            JOIN definition_groups dg ON gm.group_id = dg.id
            WHERE dg.type = 'SECTOR'
            AND dg.environment = %s
            AND gm.metadata->>'industry' ILIKE %s
            ORDER BY gm.symbol
        """, (self.environment, self.environment, f'%{industry_name}%'))

        stocks = []
        for row in cursor.fetchall():
            stocks.append({
                'symbol': row[0],
                'sector': row[1],
                'industry': row[2],
                'etf_count': row[3]
            })

        return stocks

    def get_stocks_by_theme(self, theme_key: str) -> Optional[Dict[str, any]]:
        """
        Get stocks in a theme from definition_groups + group_memberships

        Args:
            theme_key: Theme key (e.g., 'crypto_miners')

        Returns:
            Dict with theme data or None if not found
        """
        cursor = self.conn.cursor()
        
        # Get theme definition
        cursor.execute("""
            SELECT
                dg.name,
                dg.description,
                dg.metadata->>'selection_criteria' as criteria,
                dg.metadata->'related_themes' as related_themes,
                dg.id
            FROM definition_groups dg
            WHERE dg.type = 'THEME'
            AND dg.name = %s
            AND dg.environment = %s
        """, (theme_key, self.environment))

        row = cursor.fetchone()
        if not row:
            return None

        group_id = row[4]
        
        # Get symbols from group_memberships
        cursor.execute("""
            SELECT symbol
            FROM group_memberships
            WHERE group_id = %s
            ORDER BY symbol
        """, (group_id,))
        
        symbols = [r[0] for r in cursor.fetchall()]

        return {
            'theme_key': row[0],
            'name': row[1],
            'symbols': symbols,
            'description': row[1],  # description is stored in description column
            'selection_criteria': row[2],
            'related_themes': row[3] or []
        }

    def get_stock_metadata(self, stock_symbol: str) -> Optional[Dict[str, any]]:
        """
        Get full metadata for a stock

        Args:
            stock_symbol: Stock ticker symbol

        Returns:
            Dict with complete metadata or None if not found
        """
        return self.get_stock_etfs(stock_symbol)

    def get_statistics(self) -> Dict[str, any]:
        """
        Get relationship statistics

        Returns:
            Dict with statistics
        """
        cursor = self.conn.cursor()

        stats = {}

        # ETF count from definition_groups
        cursor.execute("""
            SELECT COUNT(*) FROM definition_groups
            WHERE type = 'ETF' AND environment = %s
        """, (self.environment,))
        stats['total_etfs'] = cursor.fetchone()[0]

        # Stock count from group_memberships (distinct symbols with sector assignments)
        cursor.execute("""
            SELECT COUNT(DISTINCT gm.symbol)
            FROM group_memberships gm
            JOIN definition_groups dg ON gm.group_id = dg.id
            WHERE dg.type = 'SECTOR' AND dg.environment = %s
        """, (self.environment,))
        stats['total_stocks'] = cursor.fetchone()[0]

        # Sector count from definition_groups
        cursor.execute("""
            SELECT COUNT(*) FROM definition_groups
            WHERE type = 'SECTOR' AND environment = %s
        """, (self.environment,))
        stats['total_sectors'] = cursor.fetchone()[0]

        # Theme count from definition_groups
        cursor.execute("""
            SELECT COUNT(*) FROM definition_groups
            WHERE type = 'THEME' AND environment = %s
        """, (self.environment,))
        stats['total_themes'] = cursor.fetchone()[0]

        # Sector distribution
        cursor.execute("""
            SELECT
                dg.name as sector,
                COUNT(DISTINCT gm.symbol) as count
            FROM definition_groups dg
            JOIN group_memberships gm ON dg.id = gm.group_id
            WHERE dg.type = 'SECTOR' AND dg.environment = %s
            GROUP BY dg.name
            ORDER BY count DESC
        """, (self.environment,))
        stats['sector_distribution'] = dict(cursor.fetchall())

        # Top ETFs by holdings count (from group_memberships)
        cursor.execute("""
            SELECT
                dg.name,
                COUNT(gm.id) as holdings_count
            FROM definition_groups dg
            LEFT JOIN group_memberships gm ON dg.id = gm.group_id
            WHERE dg.type = 'ETF' AND dg.environment = %s
            GROUP BY dg.name
            ORDER BY holdings_count DESC
            LIMIT 10
        """, (self.environment,))
        stats['top_etfs'] = dict(cursor.fetchall())

        return stats

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Query ETF-stock relationships'
    )
    parser.add_argument('--etf', type=str,
                       help='Get holdings for ETF symbol')
    parser.add_argument('--stock', type=str,
                       help='Get ETF memberships for stock symbol')
    parser.add_argument('--sector', type=str,
                       help='Get stocks in sector')
    parser.add_argument('--industry', type=str,
                       help='Get stocks in industry')
    parser.add_argument('--theme', type=str,
                       help='Get stocks in theme')
    parser.add_argument('--stats', action='store_true',
                       help='Show relationship statistics')
    parser.add_argument('--json', action='store_true',
                       help='Output as JSON')

    args = parser.parse_args()

    # Create query helper
    query = RelationshipQuery()

    try:
        result = None

        if args.etf:
            result = query.get_etf_holdings(args.etf)
            if result:
                if args.json:
                    print(json.dumps(result, indent=2))
                else:
                    logger.info(f"\nETF: {result['etf_symbol']} - {result['name']}")
                    logger.info(f"Total Holdings: {result['total_holdings']}")
                    logger.info(f"Market Cap Threshold: ${result['market_cap_threshold']:,.0f}")
                    logger.info(f"Last Updated: {result['last_updated']}")
                    logger.info(f"\nHoldings ({len(result['holdings'])}):")
                    for i, symbol in enumerate(result['holdings'][:50], 1):
                        print(f"  {i:3d}. {symbol}")
                    if len(result['holdings']) > 50:
                        logger.info(f"  ... and {len(result['holdings']) - 50} more")
            else:
                logger.error(f"ETF not found: {args.etf}")

        elif args.stock:
            result = query.get_stock_etfs(args.stock)
            if result:
                if args.json:
                    print(json.dumps(result, indent=2))
                else:
                    logger.info(f"\nStock: {result['stock_symbol']} - {result['name']}")
                    logger.info(f"Sector: {result['sector']}")
                    logger.info(f"Industry: {result['industry']}")
                    logger.info(f"\nMember of {len(result['member_of_etfs'])} ETFs:")
                    for etf in result['member_of_etfs']:
                        print(f"  - {etf}")
                    if result['member_of_themes']:
                        logger.info(f"\nMember of {len(result['member_of_themes'])} themes:")
                        for theme in result['member_of_themes']:
                            print(f"  - {theme}")
            else:
                logger.error(f"Stock not found: {args.stock}")

        elif args.sector:
            result = query.get_stocks_by_sector(args.sector)
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                logger.info(f"\nStocks in sector '{args.sector}': {len(result)}")
                for stock in result[:50]:
                    logger.info(f"  {stock['symbol']:6s} | {stock['industry']:30s} | {stock['etf_count']} ETFs")
                if len(result) > 50:
                    logger.info(f"  ... and {len(result) - 50} more")

        elif args.industry:
            result = query.get_stocks_by_industry(args.industry)
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                logger.info(f"\nStocks in industry '{args.industry}': {len(result)}")
                for stock in result:
                    logger.info(f"  {stock['symbol']:6s} | {stock['sector']:30s} | {stock['etf_count']} ETFs")

        elif args.theme:
            result = query.get_stocks_by_theme(args.theme)
            if result:
                if args.json:
                    print(json.dumps(result, indent=2))
                else:
                    logger.info(f"\nTheme: {result['name']}")
                    logger.info(f"Description: {result['description']}")
                    logger.info(f"Criteria: {result['selection_criteria']}")
                    logger.info(f"\nSymbols ({len(result['symbols'])}):")
                    for symbol in result['symbols']:
                        print(f"  - {symbol}")
                    if result['related_themes']:
                        logger.info(f"\nRelated themes:")
                        for theme in result['related_themes']:
                            print(f"  - {theme}")
            else:
                logger.error(f"Theme not found: {args.theme}")

        elif args.stats:
            stats = query.get_statistics()
            if args.json:
                print(json.dumps(stats, indent=2))
            else:
                logger.info("\n" + "="*60)
                logger.info("RELATIONSHIP STATISTICS")
                logger.info("="*60)
                logger.info(f"Total ETFs:    {stats['total_etfs']}")
                logger.info(f"Total Stocks:  {stats['total_stocks']}")
                logger.info(f"Total Sectors: {stats['total_sectors']}")
                logger.info(f"Total Themes:  {stats['total_themes']}")

                logger.info(f"\nSector Distribution:")
                for sector, count in sorted(stats['sector_distribution'].items(),
                                           key=lambda x: x[1], reverse=True):
                    logger.info(f"  {sector}: {count}")

                logger.info(f"\nTop 10 ETFs by Holdings:")
                for etf, count in sorted(stats['top_etfs'].items(),
                                        key=lambda x: x[1], reverse=True):
                    logger.info(f"  {etf}: {count} holdings")
                logger.info("="*60)

        else:
            parser.print_help()

    finally:
        query.close()


if __name__ == '__main__':
    main()
