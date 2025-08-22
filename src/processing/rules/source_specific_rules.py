"""
Source-Specific Processing Rules Engine - Sprint 107

Configurable processing rules for each data source type with runtime validation
and performance monitoring. Supports different filtering and processing
criteria for tick, OHLCV, and FMV data sources.

Sprint 107: Event Processing Refactor
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Callable, List, Union
from enum import Enum
import time
import math

from config.logging_config import get_domain_logger, LogDomain
from src.processing.pipeline.source_context_manager import DataSource, SourceContext

logger = get_domain_logger(LogDomain.CORE, 'source_rules')


class RuleType(Enum):
    """Types of processing rules"""
    FILTER = "filter"           # Filter out data based on criteria
    TRANSFORM = "transform"     # Transform data before processing
    VALIDATE = "validate"       # Validate data integrity
    ENRICH = "enrich"          # Add metadata or calculated fields


@dataclass
class ProcessingRule:
    """Individual processing rule definition"""
    name: str
    rule_type: RuleType
    source_types: List[DataSource]
    condition: Callable[[Any, SourceContext], bool]
    priority: int = 1  # Lower number = higher priority
    enabled: bool = True
    description: str = ""
    
    # Performance tracking
    execution_count: int = 0
    success_count: int = 0
    total_execution_time_ms: float = 0.0
    last_execution: Optional[float] = None
    
    def execute(self, data: Any, context: SourceContext) -> bool:
        """Execute the rule and track performance"""
        if not self.enabled:
            return True
        
        start_time = time.time()
        self.execution_count += 1
        self.last_execution = start_time
        
        try:
            result = self.condition(data, context)
            if result:
                self.success_count += 1
            
            execution_time_ms = (time.time() - start_time) * 1000
            self.total_execution_time_ms += execution_time_ms
            
            return result
            
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            self.total_execution_time_ms += execution_time_ms
            
            logger.error(f"Error executing rule {self.name}: {e}", exc_info=True)
            context.add_warning(f"rule_error_{self.name}: {e}")
            return False
    
    def get_success_rate(self) -> float:
        """Get rule success rate as percentage"""
        if self.execution_count == 0:
            return 100.0
        return (self.success_count / self.execution_count) * 100.0
    
    def get_avg_execution_time_ms(self) -> float:
        """Get average execution time in milliseconds"""
        if self.execution_count == 0:
            return 0.0
        return self.total_execution_time_ms / self.execution_count


@dataclass
class RuleSetConfig:
    """Configuration for rule sets"""
    enable_logging: bool = True
    log_failures_only: bool = False
    max_execution_time_ms: float = 50.0  # Maximum allowed rule execution time
    circuit_breaker_threshold: int = 10  # Consecutive failures before disabling rule
    performance_monitoring: bool = True


class SourceSpecificRulesEngine:
    """
    Configurable rules engine for source-specific processing.
    
    Manages rules for different data sources with:
    - Runtime configuration and validation
    - Performance monitoring and circuit breakers
    - Flexible rule definitions and execution
    - Source-specific rule sets
    """
    
    def __init__(self, config: RuleSetConfig = None):
        self.config = config or RuleSetConfig()
        
        # Rules organized by source type
        self._rules: Dict[DataSource, List[ProcessingRule]] = {
            DataSource.TICK: [],
            DataSource.OHLCV: [],
            DataSource.FMV: [],
            DataSource.WEBSOCKET: [],
            DataSource.CHANNEL: []
        }
        
        # Global rules that apply to all sources
        self._global_rules: List[ProcessingRule] = []
        
        # Rule execution statistics
        self._execution_stats = {
            'total_executions': 0,
            'total_failures': 0,
            'total_execution_time_ms': 0.0,
            'rules_disabled_by_circuit_breaker': 0
        }
        
        # Initialize default rules
        self._initialize_default_rules()
        
        logger.info("SourceSpecificRulesEngine initialized")
    
    def apply_rules(self, data: Any, context: SourceContext) -> bool:
        """
        Apply all applicable rules for the data source.
        
        Args:
            data: Data to process
            context: Source context with metadata
            
        Returns:
            True if all rules pass, False if any rule fails
        """
        start_time = time.time()
        self._execution_stats['total_executions'] += 1
        
        try:
            source_type = context.source_type
            
            # Get applicable rules (source-specific + global)
            applicable_rules = self._global_rules + self._rules.get(source_type, [])
            
            # Sort by priority
            applicable_rules.sort(key=lambda r: r.priority)
            
            # Execute rules
            all_passed = True
            rules_executed = 0
            
            for rule in applicable_rules:
                if not rule.enabled:
                    continue
                
                # Check if rule applies to this source type
                if source_type not in rule.source_types and rule.source_types:
                    continue
                
                # Execute rule with timeout check
                rule_start = time.time()
                result = rule.execute(data, context)
                rule_duration = (time.time() - rule_start) * 1000
                
                rules_executed += 1
                
                # Check execution time
                if rule_duration > self.config.max_execution_time_ms:
                    logger.warning(f"Rule {rule.name} exceeded max execution time: {rule_duration:.1f}ms")
                    context.add_warning(f"slow_rule_{rule.name}: {rule_duration:.1f}ms")
                
                # Handle rule failure
                if not result:
                    all_passed = False
                    
                    if self.config.enable_logging and not self.config.log_failures_only:
                        logger.debug(f"Rule {rule.name} failed for {context.ticker}")
                    
                    # Circuit breaker check
                    self._check_rule_circuit_breaker(rule)
                    
                    # For filter rules, stop processing on failure
                    if rule.rule_type == RuleType.FILTER:
                        context.add_processing_stage(f"filtered_by_{rule.name}")
                        break
                
                # Log successful validation/enrichment rules
                elif rule.rule_type in [RuleType.VALIDATE, RuleType.ENRICH]:
                    context.add_processing_stage(f"passed_{rule.name}")
            
            # Update execution statistics
            execution_time_ms = (time.time() - start_time) * 1000
            self._execution_stats['total_execution_time_ms'] += execution_time_ms
            
            if not all_passed:
                self._execution_stats['total_failures'] += 1
            
            # Log summary (reduced verbosity)
            verbose_logging = getattr(self.config, 'verbose_rules_logging', False)
            if self.config.enable_logging and verbose_logging:
                if not all_passed or not self.config.log_failures_only:
                    logger.debug(f"Rules execution for {context.ticker}: {rules_executed} rules, "
                               f"passed={all_passed}, time={execution_time_ms:.1f}ms")
            
            return all_passed
            
        except Exception as e:
            logger.error(f"Error applying rules: {e}", exc_info=True)
            self._execution_stats['total_failures'] += 1
            context.increment_error_count()
            return False
    
    def add_rule(self, rule: ProcessingRule):
        """Add a new processing rule"""
        for source_type in rule.source_types:
            if source_type in self._rules:
                self._rules[source_type].append(rule)
        
        # Sort rules by priority
        for source_rules in self._rules.values():
            source_rules.sort(key=lambda r: r.priority)
        
        logger.info(f"Added rule {rule.name} for sources: {[s.value for s in rule.source_types]}")
    
    def add_global_rule(self, rule: ProcessingRule):
        """Add a global rule that applies to all sources"""
        self._global_rules.append(rule)
        self._global_rules.sort(key=lambda r: r.priority)
        logger.info(f"Added global rule: {rule.name}")
    
    def remove_rule(self, rule_name: str) -> bool:
        """Remove a rule by name"""
        removed = False
        
        # Remove from source-specific rules
        for source_rules in self._rules.values():
            for i, rule in enumerate(source_rules):
                if rule.name == rule_name:
                    del source_rules[i]
                    removed = True
                    break
        
        # Remove from global rules
        for i, rule in enumerate(self._global_rules):
            if rule.name == rule_name:
                del self._global_rules[i]
                removed = True
                break
        
        if removed:
            logger.info(f"Removed rule: {rule_name}")
        
        return removed
    
    def enable_rule(self, rule_name: str) -> bool:
        """Enable a rule by name"""
        return self._set_rule_enabled(rule_name, True)
    
    def disable_rule(self, rule_name: str) -> bool:
        """Disable a rule by name"""
        return self._set_rule_enabled(rule_name, False)
    
    def get_rule_statistics(self) -> Dict[str, Any]:
        """Get comprehensive rule execution statistics"""
        stats = {
            'global_stats': self._execution_stats.copy(),
            'rule_performance': [],
            'rules_by_source': {}
        }
        
        # Calculate global averages
        if self._execution_stats['total_executions'] > 0:
            stats['global_stats']['avg_execution_time_ms'] = (
                self._execution_stats['total_execution_time_ms'] / 
                self._execution_stats['total_executions']
            )
            stats['global_stats']['success_rate_percent'] = (
                (self._execution_stats['total_executions'] - self._execution_stats['total_failures']) /
                self._execution_stats['total_executions'] * 100
            )
        
        # Rule-specific performance
        all_rules = self._global_rules.copy()
        for source_rules in self._rules.values():
            all_rules.extend(source_rules)
        
        for rule in all_rules:
            rule_stats = {
                'name': rule.name,
                'type': rule.rule_type.value,
                'enabled': rule.enabled,
                'execution_count': rule.execution_count,
                'success_rate_percent': rule.get_success_rate(),
                'avg_execution_time_ms': rule.get_avg_execution_time_ms(),
                'last_execution': rule.last_execution
            }
            stats['rule_performance'].append(rule_stats)
        
        # Rules by source
        for source, rules in self._rules.items():
            stats['rules_by_source'][source.value] = {
                'count': len([r for r in rules if r.enabled]),
                'total_rules': len(rules),
                'rule_names': [r.name for r in rules if r.enabled]
            }
        
        return stats
    
    def validate_configuration(self) -> List[str]:
        """Validate current rule configuration and return any issues"""
        issues = []
        
        # Check for duplicate rule names
        all_rule_names = []
        for rules in self._rules.values():
            all_rule_names.extend([r.name for r in rules])
        all_rule_names.extend([r.name for r in self._global_rules])
        
        duplicate_names = set([name for name in all_rule_names if all_rule_names.count(name) > 1])
        if duplicate_names:
            issues.append(f"Duplicate rule names found: {duplicate_names}")
        
        # Check for rules with extremely poor performance
        for rules in list(self._rules.values()) + [self._global_rules]:
            for rule in rules:
                if rule.execution_count > 10:
                    if rule.get_success_rate() < 10:
                        issues.append(f"Rule {rule.name} has very low success rate: {rule.get_success_rate():.1f}%")
                    
                    if rule.get_avg_execution_time_ms() > self.config.max_execution_time_ms * 2:
                        issues.append(f"Rule {rule.name} consistently slow: {rule.get_avg_execution_time_ms():.1f}ms avg")
        
        return issues
    
    def _initialize_default_rules(self):
        """Initialize default processing rules for each source type"""
        
        # OHLCV Rules
        self.add_rule(ProcessingRule(
            name="ohlcv_min_price_change",
            rule_type=RuleType.FILTER,
            source_types=[DataSource.OHLCV],
            condition=lambda data, ctx: self._check_min_price_change(data, 1.0),
            priority=1,
            description="Filter OHLCV data with price change < 1%"
        ))
        
        self.add_rule(ProcessingRule(
            name="ohlcv_volume_significance",
            rule_type=RuleType.FILTER,
            source_types=[DataSource.OHLCV],
            condition=lambda data, ctx: self._check_volume_multiple(data, 1.5),
            priority=2,
            description="Filter OHLCV data with insufficient volume"
        ))
        
        # FMV Rules
        self.add_rule(ProcessingRule(
            name="fmv_confidence_threshold",
            rule_type=RuleType.FILTER,
            source_types=[DataSource.FMV],
            condition=lambda data, ctx: self._check_fmv_confidence(data, 0.7),
            priority=1,
            description="Filter FMV data with confidence < 0.7"
        ))
        
        self.add_rule(ProcessingRule(
            name="fmv_deviation_limit",
            rule_type=RuleType.FILTER,
            source_types=[DataSource.FMV],
            condition=lambda data, ctx: self._check_fmv_deviation(data, 5.0),
            priority=2,
            description="Filter FMV data with excessive deviation > 5%"
        ))
        
        # Tick Rules
        self.add_rule(ProcessingRule(
            name="tick_data_validation",
            rule_type=RuleType.VALIDATE,
            source_types=[DataSource.TICK, DataSource.WEBSOCKET],
            condition=lambda data, ctx: self._validate_tick_data(data),
            priority=1,
            description="Validate basic tick data integrity"
        ))
        
        # Global Rules
        self.add_global_rule(ProcessingRule(
            name="data_freshness_check",
            rule_type=RuleType.VALIDATE,
            source_types=[],  # Empty = applies to all
            condition=lambda data, ctx: self._check_data_freshness(data, 300),  # 5 minutes
            priority=1,
            description="Validate data is not older than 5 minutes"
        ))
    
    def _check_min_price_change(self, data: Any, threshold: float) -> bool:
        """Check if price change meets minimum threshold"""
        try:
            if hasattr(data, 'percent_change'):
                return abs(data.percent_change) >= threshold
            elif hasattr(data, 'open') and hasattr(data, 'close'):
                if data.open > 0:
                    change_pct = abs((data.close - data.open) / data.open * 100)
                    return change_pct >= threshold
            return True  # Pass if can't determine
        except:
            return True
    
    def _check_volume_multiple(self, data: Any, multiple: float) -> bool:
        """Check if volume is significant multiple of average"""
        try:
            if hasattr(data, 'volume') and hasattr(data, 'avg_volume'):
                if data.avg_volume > 0:
                    return (data.volume / data.avg_volume) >= multiple
            return True  # Pass if can't determine
        except:
            return True
    
    def _check_fmv_confidence(self, data: Any, min_confidence: float) -> bool:
        """Check FMV confidence threshold"""
        try:
            if hasattr(data, 'confidence'):
                return data.confidence >= min_confidence
            return True  # Pass if can't determine
        except:
            return True
    
    def _check_fmv_deviation(self, data: Any, max_deviation: float) -> bool:
        """Check FMV deviation limit"""
        try:
            if hasattr(data, 'deviation_percent'):
                return abs(data.deviation_percent) <= max_deviation
            return True  # Pass if can't determine
        except:
            return True
    
    def _validate_tick_data(self, data: Any) -> bool:
        """Validate basic tick data integrity"""
        try:
            # Check required fields
            if hasattr(data, 'ticker') and hasattr(data, 'price') and hasattr(data, 'timestamp'):
                return (data.ticker and 
                       data.price > 0 and 
                       data.timestamp > 0)
            elif isinstance(data, dict):
                return (data.get('ticker') and 
                       data.get('price', 0) > 0 and 
                       data.get('timestamp', 0) > 0)
            return True  # Pass if unknown format
        except:
            return False
    
    def _check_data_freshness(self, data: Any, max_age_seconds: float) -> bool:
        """Check if data is fresh enough"""
        try:
            current_time = time.time()
            
            if hasattr(data, 'timestamp'):
                age = current_time - data.timestamp
                return age <= max_age_seconds
            elif isinstance(data, dict) and 'timestamp' in data:
                age = current_time - data['timestamp']
                return age <= max_age_seconds
            
            return True  # Pass if can't determine timestamp
        except:
            return True
    
    def _set_rule_enabled(self, rule_name: str, enabled: bool) -> bool:
        """Set rule enabled/disabled state"""
        found = False
        
        # Update in source-specific rules
        for source_rules in self._rules.values():
            for rule in source_rules:
                if rule.name == rule_name:
                    rule.enabled = enabled
                    found = True
        
        # Update in global rules
        for rule in self._global_rules:
            if rule.name == rule_name:
                rule.enabled = enabled
                found = True
        
        if found:
            status = "enabled" if enabled else "disabled"
            logger.info(f"Rule {rule_name} {status}")
        
        return found
    
    def _check_rule_circuit_breaker(self, rule: ProcessingRule):
        """Check if rule should be disabled due to consecutive failures"""
        if rule.execution_count < self.config.circuit_breaker_threshold:
            return
        
        # Calculate recent failure rate
        recent_executions = min(rule.execution_count, self.config.circuit_breaker_threshold)
        recent_failures = rule.execution_count - rule.success_count
        
        if recent_failures >= self.config.circuit_breaker_threshold:
            rule.enabled = False
            self._execution_stats['rules_disabled_by_circuit_breaker'] += 1
            logger.warning(f"Rule {rule.name} disabled by circuit breaker after {recent_failures} consecutive failures")