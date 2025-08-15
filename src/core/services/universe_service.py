import logging
import time
from typing import Dict, List, Set, Any, Optional
from config.logging_config import get_domain_logger, LogDomain

logger = get_domain_logger(LogDomain.CORE, 'tickstock_universe_manager')

class TickStockUniverseManager:
    """
    Manages the TickStock Core Universe (~2800 stocks) built dynamically from existing cache entries.
    Provides fast membership checks and flexible universe construction.
    """
    
    def __init__(self, cache_control):
        """
        Initialize the TickStock Universe Manager.
        
        Args:
            cache_control: CacheControl instance for accessing cached data
        """
        self.cache_control = cache_control
        self.core_universe_set = set()
        self.core_universe_list = []
        self.universe_metadata = {}
        self.build_timestamp = None
        self.build_criteria = {}
        
        # Configuration for universe building (can be adjusted)
        self.universe_config = {
            'target_size': 2800,
            'min_size': 2000,
            'max_size': 3500,
            'criteria_weights': {
                'sp500': 100,           # All S&P 500 stocks (priority 1)
                'russell1000': 80,      # Russell 1000 components  
                'mega_cap': 95,         # All mega cap stocks
                'large_cap': 75,        # Large cap stocks
                'high_volume': 70,      # High volume leaders
                'sector_leaders': 85,   # Top performers from each sector
                'thematic_leaders': 60, # Key thematic stocks (AI, cloud, etc.)
                'market_leaders': 90,   # Top market leaders
                'mid_cap_leaders': 50   # Select mid-cap leaders
            }
        }
        
    
    def build_core_universe(self) -> bool:
        """
        Build the TickStock Core Universe dynamically from existing cache entries.
        
        Returns:
            bool: True if successful, False otherwise
        """
        start_time = time.time()
        logger.info("CORE-UNIVERSE-MANAGER: Building TickStock Core Universe from cache entries...")
        
        # Get available stock groups from cache
        stock_groups = self.cache_control.get_cache('stock_groups')
        if not stock_groups:
            raise RuntimeError("No stock groups available in cache")
        
        # Build universe using comprehensive approach to maximize stocks
        core_tickers = set()
        build_stats = {}
        
        # Priority 1: Start with ALL market leaders (best foundation)
        market_leader_count = 0
        if 'market_leaders' in stock_groups:
            for key in ['top_1000', 'top_500', 'top_250']:  # Try largest first
                if key in stock_groups['market_leaders']:
                    market_leaders = self._get_tickers_from_group('market_leaders', key, stock_groups)
                    if market_leaders:
                        new_tickers = set(market_leaders) - core_tickers
                        core_tickers.update(new_tickers)
                        market_leader_count = len(market_leaders)
                        logger.debug(f"CORE-UNIVERSE-MANAGER: Added {len(new_tickers)} market leaders from {key}")
                        break
        build_stats['market_leaders'] = market_leader_count
        
        # Priority 2: Add ALL market cap categories
        market_cap_count = 0
        if 'market_cap' in stock_groups:
            for cap_type in ['mega_cap', 'large_cap', 'mid_cap', 'small_cap']:
                if cap_type in stock_groups['market_cap']:
                    cap_tickers = self._get_tickers_from_group('market_cap', cap_type, stock_groups)
                    if cap_tickers:
                        new_tickers = set(cap_tickers) - core_tickers
                        core_tickers.update(new_tickers)
                        market_cap_count += len(new_tickers)
                        logger.debug(f"CORE-UNIVERSE-MANAGER: Added {len(new_tickers)} new {cap_type} stocks")
        build_stats['market_cap_all'] = market_cap_count
        
        # Priority 3: Add ALL sector leaders (comprehensive sector coverage)
        sector_leader_count = 0
        if 'sector_leaders' in stock_groups:
            for sector_key, sector_data in stock_groups['sector_leaders'].items():
                sector_tickers = self._get_tickers_from_group('sector_leaders', sector_key, stock_groups)
                if sector_tickers:
                    new_tickers = set(sector_tickers) - core_tickers
                    core_tickers.update(new_tickers)
                    sector_leader_count += len(new_tickers)
                    logger.debug(f"CORE-UNIVERSE-MANAGER: Added {len(new_tickers)} stocks from {sector_key}")
        build_stats['sector_leaders'] = sector_leader_count
        
        # Priority 4: Add ALL thematic stocks (modern market representation)
        thematic_count = 0
        if 'themes' in stock_groups:
            for theme_key, theme_data in stock_groups['themes'].items():
                theme_tickers = self._get_tickers_from_group('themes', theme_key, stock_groups)
                if theme_tickers:
                    new_tickers = set(theme_tickers) - core_tickers
                    core_tickers.update(new_tickers)
                    thematic_count += len(new_tickers)
                    logger.debug(f"CORE-UNIVERSE-MANAGER: Added {len(new_tickers)} stocks from theme {theme_key}")
        
        # Add thematic category too
        if 'thematic' in stock_groups:
            for thematic_key, thematic_data in stock_groups['thematic'].items():
                thematic_tickers = self._get_tickers_from_group('thematic', thematic_key, stock_groups)
                if thematic_tickers:
                    new_tickers = set(thematic_tickers) - core_tickers
                    core_tickers.update(new_tickers)
                    thematic_count += len(new_tickers)
                    logger.debug(f"CORE-UNIVERSE-MANAGER: Added {len(new_tickers)} stocks from thematic {thematic_key}")
        build_stats['thematic_leaders'] = thematic_count
        
        # Priority 5: Add ALL industry groups for even more coverage
        industry_count = 0
        if 'industry' in stock_groups:
            for industry_key, industry_data in stock_groups['industry'].items():
                industry_tickers = self._get_tickers_from_group('industry', industry_key, stock_groups)
                if industry_tickers:
                    new_tickers = set(industry_tickers) - core_tickers
                    core_tickers.update(new_tickers)
                    industry_count += len(new_tickers)
                    logger.debug(f"CORE-UNIVERSE-MANAGER: Added {len(new_tickers)} stocks from industry {industry_key}")
        build_stats['industry_groups'] = industry_count
            
    def build_core_universe(self) -> bool:
        """
        Build the TickStock Core Universe dynamically from existing cache entries.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            start_time = time.time()
            logger.info("CORE-UNIVERSE-MANAGER: Building TickStock Core Universe from cache entries...")
            
            # Get available stock groups from cache
            stock_groups = self.cache_control.get_cache('stock_groups')
            if not stock_groups:
                raise RuntimeError("No stock groups available in cache")
            
            # Build universe systematically to reach ~2800 stocks
            core_tickers = set()
            build_stats = {}
            
            # Foundation: Start with top 500 market leaders (best quality base)
            market_leader_count = 0
            if 'market_leaders' in stock_groups and 'top_500' in stock_groups['market_leaders']:
                market_leaders = self._get_tickers_from_group('market_leaders', 'top_500', stock_groups)
                if market_leaders:
                    core_tickers.update(market_leaders)
                    market_leader_count = len(market_leaders)
                    logger.debug(f"CORE-UNIVERSE-MANAGER: Foundation: Added {market_leader_count} top market leaders")
            build_stats['market_leaders'] = market_leader_count
            
            # Layer 1: Add ALL market cap categories for size diversity
            market_cap_count = 0
            if 'market_cap' in stock_groups:
                # Add in order of quality: mega -> large -> mid -> small
                for cap_type in ['mega_cap', 'large_cap', 'mid_cap', 'small_cap']:
                    if cap_type in stock_groups['market_cap']:
                        cap_tickers = self._get_tickers_from_group('market_cap', cap_type, stock_groups)
                        if cap_tickers:
                            new_tickers = set(cap_tickers) - core_tickers
                            core_tickers.update(new_tickers)
                            market_cap_count += len(new_tickers)
                            logger.debug(f"CORE-UNIVERSE-MANAGER: Added {len(new_tickers)} new {cap_type} stocks")
            build_stats['market_cap_tiers'] = market_cap_count
            
            # Layer 2: Add ALL sector leaders for complete sector coverage
            sector_leader_count = 0
            if 'sector_leaders' in stock_groups:
                for sector_key in stock_groups['sector_leaders'].keys():
                    sector_tickers = self._get_tickers_from_group('sector_leaders', sector_key, stock_groups)
                    if sector_tickers:
                        new_tickers = set(sector_tickers) - core_tickers
                        core_tickers.update(new_tickers)
                        sector_leader_count += len(new_tickers)
                        logger.debug(f"CORE-UNIVERSE-MANAGER: Added {len(new_tickers)} new stocks from {sector_key}")
            build_stats['sector_leaders'] = sector_leader_count
            
            # Layer 3: Add ALL industry groups for deep industry coverage
            industry_count = 0
            if 'industry' in stock_groups:
                for industry_key in stock_groups['industry'].keys():
                    industry_tickers = self._get_tickers_from_group('industry', industry_key, stock_groups)
                    if industry_tickers:
                        new_tickers = set(industry_tickers) - core_tickers
                        core_tickers.update(new_tickers)
                        industry_count += len(new_tickers)
                        logger.debug(f"CORE-UNIVERSE-MANAGER: Added {len(new_tickers)} new stocks from industry {industry_key}")
            build_stats['industry_groups'] = industry_count
            
            # Layer 4: Add ALL thematic stocks for modern market exposure
            thematic_count = 0
            
            # Add all themes
            if 'themes' in stock_groups:
                for theme_key in stock_groups['themes'].keys():
                    theme_tickers = self._get_tickers_from_group('themes', theme_key, stock_groups)
                    if theme_tickers:
                        new_tickers = set(theme_tickers) - core_tickers
                        core_tickers.update(new_tickers)
                        thematic_count += len(new_tickers)
                        logger.debug(f"CORE-UNIVERSE-MANAGER: Added {len(new_tickers)} new stocks from theme {theme_key}")
            
            # Add thematic category
            if 'thematic' in stock_groups:
                for thematic_key in stock_groups['thematic'].keys():
                    thematic_tickers = self._get_tickers_from_group('thematic', thematic_key, stock_groups)
                    if thematic_tickers:
                        new_tickers = set(thematic_tickers) - core_tickers
                        core_tickers.update(new_tickers)
                        thematic_count += len(new_tickers)
                        logger.debug(f"CORE-UNIVERSE-MANAGER: Added {len(new_tickers)} new stocks from thematic {thematic_key}")
            
            build_stats['thematic_all'] = thematic_count
            
            # Check if we need more stocks to reach target
            current_size = len(core_tickers)
            target_size = self.universe_config['target_size']
            
            logger.info(f"CORE-UNIVERSE-MANAGER: Current universe size: {current_size}, target: {target_size}")
            
            # Layer 5: Add micro cap if we need more stocks (but limit to avoid too much risk)
            micro_cap_count = 0
            if current_size < target_size and 'market_cap' in stock_groups and 'micro_cap' in stock_groups['market_cap']:
                remaining_needed = target_size - current_size
                micro_cap_limit = min(remaining_needed, 300)  # Limit micro cap exposure
                
                micro_cap_tickers = self._get_tickers_from_group('market_cap', 'micro_cap', stock_groups)
                if micro_cap_tickers:
                    new_micro_cap = [t for t in micro_cap_tickers if t not in core_tickers]
                    selected_micro_cap = new_micro_cap[:micro_cap_limit]
                    core_tickers.update(selected_micro_cap)
                    micro_cap_count = len(selected_micro_cap)
                    logger.debug(f"CORE-UNIVERSE-MANAGER: Added {micro_cap_count} micro cap stocks (limited for risk management)")
            
            build_stats['micro_cap_limited'] = micro_cap_count
            
            # Final adjustment: If still short, add from complete list (high quality filter)
            final_adjustment_count = 0
            current_size = len(core_tickers)
            
            if current_size < self.universe_config['min_size'] and 'complete' in stock_groups and 'all_stocks' in stock_groups['complete']:
                remaining_needed = self.universe_config['target_size'] - current_size
                
                complete_tickers = self._get_tickers_from_group('complete', 'all_stocks', stock_groups)
                if complete_tickers:
                    # Get stocks not already included
                    remaining_stocks = [t for t in complete_tickers if t not in core_tickers]
                    
                    # Add remaining stocks up to target (prioritize those likely to be higher quality)
                    selected_remaining = remaining_stocks[:remaining_needed]
                    core_tickers.update(selected_remaining)
                    final_adjustment_count = len(selected_remaining)
                    logger.debug(f"CORE-UNIVERSE-MANAGER: Final adjustment: Added {final_adjustment_count} additional stocks to reach target")
            
            build_stats['final_adjustment'] = final_adjustment_count
            
            # Finalize the universe
            self.core_universe_list = sorted(list(core_tickers))
            self.core_universe_set = core_tickers
            self.build_timestamp = time.time()
            self.build_criteria = build_stats
            
            # Create metadata
            final_size = len(core_tickers)
            self.universe_metadata = {
                'total_stocks': final_size,
                'build_timestamp': self.build_timestamp,
                'build_duration_ms': round((time.time() - start_time) * 1000, 2),
                'criteria_breakdown': build_stats,
                'target_size': self.universe_config['target_size'],
                'cache_sources_used': list(build_stats.keys()),
                'build_method': 'comprehensive_layered_aggregation',
                'quality_metrics': {
                    'market_leader_percentage': round((market_leader_count / final_size) * 100, 1) if final_size > 0 else 0,
                    'sector_diversity': len(stock_groups.get('sector_leaders', {})),
                    'industry_diversity': len(stock_groups.get('industry', {})),
                    'thematic_coverage': len(stock_groups.get('themes', {})) + len(stock_groups.get('thematic', {}))
                }
            }
            
            # Validate universe size
            universe_size = len(core_tickers)
            if universe_size < self.universe_config['min_size']:
                logger.warning(f"CORE-UNIVERSE-MANAGER: Core universe size ({universe_size}) below minimum ({self.universe_config['min_size']})")
            elif universe_size > self.universe_config['max_size']:
                logger.warning(f"CORE-UNIVERSE-MANAGER: Core universe size ({universe_size}) above maximum ({self.universe_config['max_size']})")
            else:
                logger.info(f"CORE-UNIVERSE-MANAGER: Core universe size ({universe_size}) within target range")
            
            logger.info(f"TCORE-UNIVERSE-MANAGER: ickStock Core Universe built successfully: {universe_size} stocks in {self.universe_metadata['build_duration_ms']}ms")
            
            # Log detailed breakdown
            logger.info(f"CORE-UNIVERSE-MANAGER: Universe composition breakdown:")
            total_added = 0
            for component, count in build_stats.items():
                percentage = round((count / universe_size) * 100, 1) if universe_size > 0 else 0
                logger.info(f"  - {component}: {count} stocks ({percentage}%)")
                total_added += count
            
            # Calculate quality score
            quality_score = 0
            if market_leader_count >= 400:  # Good market leader base
                quality_score += 25
            if sector_leader_count >= 100:  # Good sector coverage
                quality_score += 25
            if industry_count >= 300:  # Good industry diversity
                quality_score += 25
            if universe_size >= 2000:  # Adequate size
                quality_score += 25
            
            self.universe_metadata['quality_score'] = quality_score
            logger.info(f"CORE-UNIVERSE-MANAGER: Universe quality score: {quality_score}/100")
            
            return True
            
        except Exception as e:
            logger.error(f"CORE-UNIVERSE-MANAGER: Failed to build TickStock Core Universe: {e}", exc_info=True)
            self.core_universe_set = set()
            self.core_universe_list = []
            self.universe_metadata = {}
            return False
            
        except Exception as e:
            logger.error(f"CORE-UNIVERSE-MANAGER: Failed to build TickStock Core Universe: {e}", exc_info=True)
            self.core_universe_set = set()
            self.core_universe_list = []
            self.universe_metadata = {}
            return False
            
        except Exception as e:
            logger.error(f"CORE-UNIVERSE-MANAGER: Failed to build TickStock Core Universe: {e}", exc_info=True)
            self.core_universe_set = set()
            self.core_universe_list = []
            self.universe_metadata = {}
            return False
    
    def _get_tickers_from_group(self, group_name: str, key: str, stock_groups: Dict) -> List[str]:
        """
        Extract ticker list from a specific stock group.
        
        Args:
            group_name: Name of the stock group (e.g., 'market_cap', 'sector_leaders')
            key: Key within the group (e.g., 'mega_cap', 'top_10_technology')
            stock_groups: Stock groups from cache
            
        Returns:
            List[str]: List of ticker symbols, empty if not found
        """
        try:
            if group_name not in stock_groups:
                logger.debug(f"CORE-UNIVERSE-MANAGER: Group '{group_name}' not found in stock_groups")
                return []
            
            if key not in stock_groups[group_name]:
                logger.debug(f"CORE-UNIVERSE-MANAGER: Key '{key}' not found in group '{group_name}'")
                return []
            
            group_data = stock_groups[group_name][key]
            if 'stocks' in group_data:
                return [stock['ticker'] for stock in group_data['stocks']]
            else:
                logger.debug(f"CORE-UNIVERSE-MANAGER: No 'stocks' key found in {group_name}.{key}")
                return []
                
        except Exception as e:
            logger.error(f"CORE-UNIVERSE-MANAGER: Error extracting tickers from {group_name}.{key}: {e}")
            return []
    
    def get_core_universe(self) -> List[str]:
        """
        Get the complete TickStock Core Universe as a list.
        
        Returns:
            List[str]: Sorted list of ticker symbols in core universe
        """
        if not self.core_universe_list:
            logger.warning("CORE-UNIVERSE-MANAGER: Core universe not built, attempting to build now...")
            if not self.build_core_universe():
                raise RuntimeError("Failed to build core universe")
        
        return self.core_universe_list.copy()
    
    def is_stock_in_core_universe(self, ticker: str) -> bool:
        """
        Fast membership check for TickStock Core Universe.
        Optimized for <1ms performance.
        
        Args:
            ticker: Stock symbol to check
            
        Returns:
            bool: True if ticker is in core universe, False otherwise
        """
        if not self.core_universe_set:
            logger.warning("CORE-UNIVERSE-MANAGER: Core universe not built, attempting to build now...")
            if not self.build_core_universe():
                logger.error("CORE-UNIVERSE-MANAGER: Failed to build core universe for membership check")
                return False
        
        return ticker in self.core_universe_set
    
    def get_universe_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about the current TickStock Core Universe.
        
        Returns:
            Dict[str, Any]: Universe metadata and statistics
        """
        return self.universe_metadata.copy()
    
    def get_universe_size(self) -> int:
        """
        Get the size of the current TickStock Core Universe.
        
        Returns:
            int: Number of stocks in core universe
        """
        return len(self.core_universe_set)
    
    def refresh_core_universe(self) -> bool:
        """
        Refresh the core universe by rebuilding from current cache data.
        
        Returns:
            bool: True if refresh successful, False otherwise
        """
        old_size = len(self.core_universe_set)
        
        if self.build_core_universe():
            new_size = len(self.core_universe_set)
            return True
        else:
            logger.error("CORE-UNIVERSE-MANAGER: Failed to refresh core universe")
            return False
    
    def validate_universe_health(self) -> Dict[str, Any]:
        """
        Validate the health and completeness of the core universe.
        
        Returns:
            Dict[str, Any]: Health check results
        """
        health_check = {
            'is_healthy': True,
            'issues': [],
            'warnings': [],
            'metrics': {}
        }
        
        try:
            # Check if universe exists
            if not self.core_universe_set:
                health_check['is_healthy'] = False
                health_check['issues'].append('Core universe not built')
                return health_check
            
            # Check universe size
            universe_size = len(self.core_universe_set)
            health_check['metrics']['universe_size'] = universe_size
            
            if universe_size < self.universe_config['min_size']:
                health_check['is_healthy'] = False
                health_check['issues'].append(f'Universe too small: {universe_size} < {self.universe_config["min_size"]}')
            elif universe_size > self.universe_config['max_size']:
                health_check['warnings'].append(f'Universe larger than expected: {universe_size} > {self.universe_config["max_size"]}')
            
            # Check build recency
            if self.build_timestamp:
                age_hours = (time.time() - self.build_timestamp) / 3600
                health_check['metrics']['age_hours'] = round(age_hours, 2)
                
                if age_hours > 24:  # Universe older than 24 hours
                    health_check['warnings'].append(f'Universe build is {age_hours:.1f} hours old')
                elif age_hours > 168:  # Older than 1 week
                    health_check['is_healthy'] = False
                    health_check['issues'].append(f'Universe build is {age_hours:.1f} hours old (too stale)')
            
            # Check criteria coverage
            if self.build_criteria:
                health_check['metrics']['criteria_coverage'] = self.build_criteria
                
                # Ensure we have representation from key sources
                required_sources = ['sp500', 'mega_cap', 'market_leaders']
                missing_sources = [src for src in required_sources if src not in self.build_criteria or self.build_criteria[src] == 0]
                
                if missing_sources:
                    health_check['warnings'].append(f'Missing representation from: {missing_sources}')
            
            logger.debug(f"CORE-UNIVERSE-MANAGER: Universe health check completed: {'healthy' if health_check['is_healthy'] else 'unhealthy'}")
            
        except Exception as e:
            health_check['is_healthy'] = False
            health_check['issues'].append(f'Health check failed: {str(e)}')
            logger.error(f"CORE-UNIVERSE-MANAGER: Error in universe health validation: {e}", exc_info=True)
        
        return health_check
    
    '''
    def get_universe_config(self) -> Dict[str, Any]:
        """
        Get the current universe configuration.
        
        Returns:
            Dict[str, Any]: Universe configuration settings
        """
        return self.universe_config.copy()
    
    def update_universe_config(self, new_config: Dict[str, Any]) -> bool:
        """
        Update universe configuration settings.
        
        Args:
            new_config: New configuration values to merge
            
        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            # Validate configuration
            if 'target_size' in new_config:
                if not isinstance(new_config['target_size'], int) or new_config['target_size'] < 1000:
                    logger.error("CORE-UNIVERSE-MANAGER: Invalid target_size in configuration")
                    return False
            
            # Merge configuration
            old_config = self.universe_config.copy()
            self.universe_config.update(new_config)
            
            logger.info(f"CORE-UNIVERSE-MANAGER: Universe configuration updated: {old_config} -> {self.universe_config}")
            
            # Suggest rebuilding if target size changed significantly
            if 'target_size' in new_config and abs(new_config['target_size'] - old_config['target_size']) > 100:
                logger.info("CORE-UNIVERSE-MANAGER: Significant target size change detected - consider rebuilding universe")
            
            return True
            
        except Exception as e:
            logger.error(f"CORE-UNIVERSE-MANAGER: Error updating universe configuration: {e}", exc_info=True)
            return False
    '''
