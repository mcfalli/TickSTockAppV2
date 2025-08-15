#!/usr/bin/env python3
"""
TickStock File Migration Mapper - Enhanced Version
Maps ALL files from old structure to new modular V2 structure
"""

import os
import json
import shutil
from pathlib import Path
from typing import Dict, List, Tuple
import hashlib

class EnhancedFileMigrationMapper:
    def __init__(self, source_dir: str = r"C:\Users\McDude\TickStockApp", 
                 dest_dir: str = r"C:\Users\McDude\TickStockAppV2"):
        self.source_dir = Path(source_dir)
        self.dest_dir = Path(dest_dir)
        self.file_mappings = {}
        self.unmapped_files = []
        
    def create_comprehensive_mapping(self) -> Dict[str, str]:
        """Create complete file mapping including previously unmapped files."""
        
        # Start with the existing mappings
        mapping = {
            # Root level files
            ".env": ".env",
            ".env.template": ".env.template",
            ".gitignore": ".gitignore",
            "app.py": "src/app.py",
            "app_forms.py": "src/presentation/validators/forms.py",
            "app_routes_api.py": "src/api/rest/api.py",
            "app_routes_auth.py": "src/api/rest/auth.py",
            "app_routes_main.py": "src/api/rest/main.py",
            "app_startup.py": "src/core/services/startup_service.py",
            "app_utils.py": "src/shared/utils/app_utils.py",
            "docker-compose.yml": "docker/docker-compose.yml",
            "Dockerfile": "docker/Dockerfile",
            "LICENSE.txt": "LICENSE.txt",
            "market_utils.py": "src/shared/utils/market_utils.py",
            "nginx.conf": "docker/nginx.conf",
            "package-lock.json": "web/package-lock.json",
            "package.json": "web/package.json",
            "prometheus.yml": "config/prometheus.yml",
            "pytest.ini": "pytest.ini",
            "requirements.txt": "requirements/base.txt",
            "temp.py": "scripts/temp/temp.py",  # Keep temp files in scripts/temp
            
            # Auth module
            "auth/authentication.py": "src/auth/authentication.py",
            "auth/registration.py": "src/auth/registration.py",
            "auth/session.py": "src/auth/session.py",
            "auth/__init__.py": "src/auth/__init__.py",
            
            # Classes - Domain models
            "classes/__init__.py": "src/core/domain/__init__.py",
            "classes/analytics/model.py": "src/infrastructure/database/models/analytics.py",
            "classes/analytics/__init__.py": "src/infrastructure/database/models/__init__.py",
            "classes/events/base.py": "src/core/domain/events/base.py",
            "classes/events/control.py": "src/core/domain/events/control.py",
            "classes/events/highlow.py": "src/core/domain/events/highlow.py",
            "classes/events/surge.py": "src/core/domain/events/surge.py",
            "classes/events/trend.py": "src/core/domain/events/trend.py",
            "classes/events/__init__.py": "src/core/domain/events/__init__.py",
            "classes/market/state.py": "src/core/domain/market/state.py",
            "classes/market/tick.py": "src/core/domain/market/tick.py",
            "classes/market/__init__.py": "src/core/domain/market/__init__.py",
            "classes/processing/queue.py": "src/processing/queues/base_queue.py",
            "classes/processing/__init__.py": "src/processing/queues/__init__.py",
            "classes/transport/models.py": "src/presentation/converters/transport_models.py",
            "classes/transport/__init__.py": "src/presentation/converters/__init__.py",
            
            # Config
            "config/app_config.py": "config/app_config.py",
            "config/cache_control.py": "src/infrastructure/cache/cache_control.py",
            "config/config_manager.py": "src/core/services/config_manager.py",
            "config/logging_config.py": "config/logging_config.py",
            "config/__init__.py": "config/__init__.py",
            
            # Database
            "database/model.py": "src/infrastructure/database/models/base.py",
            "database/model_migrations_run.py": "src/infrastructure/database/migrations/run_migrations.py",
            "database/__init__.py": "src/infrastructure/database/__init__.py",
            "database/__init__.py.bak": "src/infrastructure/database/__init__.py.bak",
            
            # Data flow / Monitoring
            "data_flow/metrics_collector.py": "src/monitoring/metrics_collector.py",
            "data_flow/performance_monitor.py": "src/monitoring/performance_monitor.py",
            "data_flow/session_manager.py": "src/core/services/session_manager.py",
            "data_flow/__init__.py": "src/monitoring/__init__.py",
            
            # Data providers
            "data_providers/data_provider_factory.py": "src/infrastructure/data_sources/factory.py",
            "data_providers/real_time_data_adapter.py": "src/infrastructure/data_sources/adapters/realtime_adapter.py",
            "data_providers/__init__.py": "src/infrastructure/data_sources/__init__.py",
            "data_providers/base/data_provider.py": "src/core/interfaces/data_provider.py",
            "data_providers/base/data_result.py": "src/core/interfaces/data_result.py",
            "data_providers/base/__init__.py": "src/core/interfaces/__init__.py",
            "data_providers/polygon/polygon_data_provider.py": "src/infrastructure/data_sources/polygon/provider.py",
            "data_providers/polygon/polygon_api.py": "src/infrastructure/data_sources/polygon/api.py",
            "data_providers/polygon/__init__.py": "src/infrastructure/data_sources/polygon/__init__.py",
            "data_providers/simulated/simulated_data_provider.py": "src/infrastructure/data_sources/synthetic/provider.py",
            "data_providers/simulated/synthetic_data_generator.py": "src/infrastructure/data_sources/synthetic/generator.py",
            "data_providers/simulated/synthetic_data_loader.py": "src/infrastructure/data_sources/synthetic/loader.py",
            "data_providers/simulated/__init__.py": "src/infrastructure/data_sources/synthetic/__init__.py",
            
            # Event detection
            "event_detection/buysell_market_tracker.py": "src/processing/detectors/buysell_tracker.py",
            "event_detection/event_detection_manager.py": "src/processing/detectors/manager.py",
            "event_detection/event_detection_engines.py": "src/processing/detectors/engines.py",
            "event_detection/event_detector_util.py": "src/processing/detectors/utils.py",
            "event_detection/__init__.py": "src/processing/detectors/__init__.py",
            "event_detection/engines/__init__.py": "src/processing/detectors/engines/__init__.py",
            "event_detection/engines/buysell_tracker.py": "src/processing/detectors/buysell_engine.py",
            "event_detection/engines/highlow_detector.py": "src/processing/detectors/highlow_detector.py",
            "event_detection/engines/surge_detector.py": "src/processing/detectors/surge_detector.py",
            "event_detection/engines/trend_detector.py": "src/processing/detectors/trend_detector.py",
            
            # Market analytics
            "market_analytics/analytics_manager.py": "src/core/services/analytics_manager.py",
            "market_analytics/analytics_sync.py": "src/core/services/analytics_sync.py",
            "market_analytics/market_metrics.py": "src/core/services/market_metrics.py",
            "market_analytics/memory_analytics.py": "src/core/services/memory_analytics.py",
            "market_analytics/__init__.py": "src/core/services/__init__.py",
            
            # Market data service
            "market_data_service/core_service.py": "src/core/services/market_data_service.py",
            "market_data_service/data_publisher.py": "src/presentation/websocket/data_publisher.py",
            "market_data_service/event_processor.py": "src/processing/pipeline/event_processor.py",
            "market_data_service/analytics_coordinator.py": "src/core/services/analytics_coordinator.py",
            "market_data_service/health_monitor.py": "src/monitoring/health_monitor.py",
            "market_data_service/universe_coordinator.py": "src/core/services/universe_coordinator.py",
            "market_data_service/__init__.py": "src/core/services/__init__.py",
            
            # Monitoring
            "monitoring/monitoring.py": "src/monitoring/system_monitor.py",
            "monitoring/tracer.py": "src/monitoring/tracer.py",
            "monitoring/query_debug_logger.py": "src/monitoring/query_debug_logger.py",
            "monitoring/__init__.py": "src/monitoring/__init__.py",
            
            # Processing
            "processing/event_detector.py": "src/processing/pipeline/event_detector.py",
            "processing/priority_manager.py": "src/processing/queues/priority_manager.py",
            "processing/tick_processor.py": "src/processing/pipeline/tick_processor.py",
            "processing/worker_pool.py": "src/processing/workers/worker_pool.py",
            "processing/__init__.py": "src/processing/__init__.py",
            
            # Services
            "services/email_manager.py": "src/infrastructure/messaging/email_service.py",
            "services/sms_manager.py": "src/infrastructure/messaging/sms_service.py",
            "services/tickstock_universe_manager.py": "src/core/services/universe_service.py",
            "services/user_filters_service.py": "src/core/services/user_filters_service.py",
            "services/user_settings_service.py": "src/core/services/user_settings_service.py",
            "services/__init__.py": "src/core/services/__init__.py",
            
            # Session accumulation
            "session_accumulation/accumulation_manager.py": "src/core/services/accumulation_manager.py",
            "session_accumulation/database_sync.py": "src/core/services/database_sync.py",
            "session_accumulation/memory_accumulation.py": "src/core/services/memory_accumulation.py",
            "session_accumulation/__init__.py": "src/core/services/__init__.py",
            
            # Universe
            "universe/core_universe_manager.py": "src/core/services/universe/core_manager.py",
            "universe/subscription_manager.py": "src/core/services/universe/subscription_manager.py",
            "universe/universe_analytics.py": "src/core/services/universe/analytics.py",
            "universe/user_universe_manager.py": "src/core/services/universe/user_manager.py",
            "universe/__init__.py": "src/core/services/universe/__init__.py",
            
            # Utils
            "utils/event_factory.py": "src/shared/utils/event_factory.py",
            "utils/utils.py": "src/shared/utils/general.py",
            "utils/validation.py": "src/shared/utils/validation.py",
            "utils/__init__.py": "src/shared/utils/__init__.py",
            
            # WebSocket handlers (ws_handlers -> presentation/websocket)
            "ws_handlers/polygon_websocket_client.py": "src/presentation/websocket/polygon_client.py",
            "ws_handlers/websocket_analytics.py": "src/presentation/websocket/analytics.py",
            "ws_handlers/websocket_data_filter.py": "src/presentation/websocket/data_filter.py",
            "ws_handlers/websocket_display.py": "src/presentation/websocket/display_converter.py",
            "ws_handlers/websocket_filter_cache.py": "src/presentation/websocket/filter_cache.py",
            "ws_handlers/websocket_publisher.py": "src/presentation/websocket/publisher.py",
            "ws_handlers/websocket_statistics.py": "src/presentation/websocket/statistics.py",
            "ws_handlers/websocket_universe_cache.py": "src/presentation/websocket/universe_cache.py",
            "ws_handlers/web_socket_manager.py": "src/presentation/websocket/manager.py",
            "ws_handlers/__init__.py": "src/presentation/websocket/__init__.py",
            
            # Dev tools - keep in scripts/dev_tools
            "dev_tools/maint_get_stocks.py": "scripts/dev_tools/maint_get_stocks.py",
            "dev_tools/maint_load_stock_cache_entries.py": "scripts/dev_tools/maint_load_stock_cache_entries.py",
            "dev_tools/maint_read_stock_cache_entries.py": "scripts/dev_tools/maint_read_stock_cache_entries.py",
            "dev_tools/test_monitoring_optimization.py": "scripts/dev_tools/test_monitoring_optimization.py",
            "dev_tools/test_polygon_api_check.py": "scripts/dev_tools/test_polygon_api_check.py",
            "dev_tools/test_polygon_comprehensive_api_config.py": "scripts/dev_tools/test_polygon_comprehensive_api_config.py",
            "dev_tools/util_code_scan_unused_code.py": "scripts/dev_tools/scan_unused_code.py",
            "dev_tools/util_create_project_structure_documentation.py": "scripts/dev_tools/create_structure_docs.py",
            "dev_tools/util_dump_trace_details.py": "scripts/dev_tools/dump_trace_details.py",
            "dev_tools/util_dump_trace_entries.py": "scripts/dev_tools/dump_trace_entries.py",
            "dev_tools/util_extract_documentation.py": "scripts/dev_tools/extract_documentation.py",
            "dev_tools/util_load_stocks_cache_entries.py": "scripts/dev_tools/load_stocks_cache_entries.py",
            "dev_tools/util_proj_generate_structure.py": "scripts/dev_tools/generate_structure.py",
            "dev_tools/util_temp_run.py": "scripts/temp/util_temp_run.py",
            
            # Documentation - keep as is
            "docs/DOCUMENTATION_CHECKLIST.md": "docs/DOCUMENTATION_CHECKLIST.md",
            "docs/quick-reference.md": "docs/quick-reference.md",
            "docs/README.md": "docs/README.md",
            "docs/technical-overview.md": "docs/technical-overview.md",
            "docs/TickStock-About.md": "docs/TickStock-About.md",
            "docs/api/rest-endpoints.md": "docs/api/rest-endpoints.md",
            "docs/api/websocket-events.md": "docs/api/websocket-events.md",
            "docs/architecture/Architecture-Overview.md": "docs/architecture/Architecture-Overview.md",
            "docs/architecture/component-architecture.md": "docs/architecture/component-architecture.md",
            "docs/architecture/data-flow-pileline.md": "docs/architecture/data-flow-pileline.md",
            "docs/architecture/grid-stack.md": "docs/architecture/grid-stack.md",
            "docs/architecture/JSON.md": "docs/architecture/JSON.md",
            "docs/architecture/market-tracker.md": "docs/architecture/market-tracker.md",
            "docs/architecture/project_structure.md": "docs/architecture/project_structure.md",
            "docs/features/event-detection.md": "docs/features/event-detection.md",
            "docs/features/features_logging-strategy.md": "docs/features/features_logging-strategy.md",
            "docs/features/filtering-system.md": "docs/features/filtering-system.md",
            "docs/features/highlow-detector.md": "docs/features/highlow-detector.md",
            "docs/features/memory-first-processing.md": "docs/features/memory-first-processing.md",
            "docs/features/surge-detection.md": "docs/features/surge-detection.md",
            "docs/features/trend-detection.md": "docs/features/trend-detection.md",
            "docs/features/user-authentication.md": "docs/features/user-authentication.md",
            "docs/maintenance/maintenance_load_cache_entries.md": "docs/maintenance/maintenance_load_cache_entries.md",
            "docs/maintenance/maintenance_load_stocks.md": "docs/maintenance/maintenance_load_stocks.md",
            
            # Email templates - move to web/templates/email
            "email_template/account_update_email.html": "web/templates/email/account_update_email.html",
            "email_template/change_password_email.html": "web/templates/email/change_password_email.html",
            "email_template/disable_email.html": "web/templates/email/disable_email.html",
            "email_template/email_change_notification.html": "web/templates/email/email_change_notification.html",
            "email_template/lockout_email.html": "web/templates/email/lockout_email.html",
            "email_template/reset_email.html": "web/templates/email/reset_email.html",
            "email_template/subscription_cancelled_email.html": "web/templates/email/subscription_cancelled_email.html",
            "email_template/subscription_reactivated_email.html": "web/templates/email/subscription_reactivated_email.html",
            "email_template/temp_code_email.html": "web/templates/email/temp_code_email.html",
            "email_template/verification_email.html": "web/templates/email/verification_email.html",
            "email_template/welcome_email.html": "web/templates/email/welcome_email.html",
            
            # Migrations - keep as is (Alembic requires specific structure)
            "migrations/alembic.ini": "migrations/alembic.ini",
            "migrations/env.py": "migrations/env.py",
            "migrations/README": "migrations/README",
            "migrations/script.py.mako": "migrations/script.py.mako",
            "migrations/versions/eaf466e1159c_initial_migration_baseline_schema.py": "migrations/versions/eaf466e1159c_initial_migration_baseline_schema.py",
            "migrations/versions/20250603_072046_create_market_analytics_table.py": "migrations/versions/20250603_072046_create_market_analytics_table.py",
            "migrations/versions/9cb2ed91a331_test_migration_add_test_field.py": "migrations/versions/9cb2ed91a331_test_migration_add_test_field.py",
            "migrations/versions/c4bff4478223_remove_test_fields_complete_migration_.py": "migrations/versions/c4bff4478223_remove_test_fields_complete_migration_.py",
            "migrations/versions/d176423a036f_test_miration_workflow.py": "migrations/versions/d176423a036f_test_miration_workflow.py",
            
            # Static files
            "static/favicon.ico": "web/static/favicon.ico",
            "static/css/auth.css": "web/static/css/utilities/auth.css",
            "static/css/main.css": "web/static/css/utilities/main.css",
            "static/css/base/reset.css": "web/static/css/base/reset.css",
            "static/css/base/variables.css": "web/static/css/base/variables.css",
            "static/css/components/dashboard.css": "web/static/css/utilities/dashboard.css",
            "static/css/components/dialogs.css": "web/static/css/utilities/dialogs.css",
            "static/css/components/events.css": "web/static/css/utilities/events.css",
            "static/css/components/filters.css": "web/static/css/utilities/filters.css",
            "static/css/components/gauges.css": "web/static/css/components/gauges.css",
            "static/css/components/modals.css": "web/static/css/components/modals.css",
            "static/css/components/navbar.css": "web/static/css/utilities/navbar.css",
            "static/css/components/status-bar.css": "web/static/css/utilities/status-bar.css",
            "static/css/components/user-menu.css": "web/static/css/utilities/user-menu.css",
            "static/css/components/velocity.css": "web/static/css/utilities/velocity.css",
            "static/css/layout/grid.css": "web/static/css/layout/grid.css",
            "static/css/layout/layout.css": "web/static/css/layout/layout.css",
            "static/css/utilities/animations.css": "web/static/css/utilities/animations.css",
            "static/images/logo-placehodlerv2.jpg": "web/static/images/logo-placehodlerv2.jpg",
            "static/images/logo-placeholder.jpg": "web/static/images/logo-placeholder.jpg",
            "static/js/app-core.js": "web/static/js/core/app-core.js",
            "static/js/app-events.js": "web/static/js/core/app-events.js",
            "static/js/app-filters.js": "web/static/js/core/app-filters.js",
            "static/js/app-gauges.js": "web/static/js/core/app-gauges.js",
            "static/js/app-gridstack.js": "web/static/js/core/app-gridstack.js",
            "static/js/app-layout-sync.js": "web/static/js/core/app-layout-sync.js",
            "static/js/app-universe.js": "web/static/js/core/app-universe.js",
            "static/js/libphonenumber-min.js": "web/static/js/vendor/libphonenumber-min.js",
            
            # Templates
            "templates/account.html": "web/templates/pages/account.html",
            "templates/actvity.html": "web/templates/pages/actvity.html",
            "templates/change_password.html": "web/templates/pages/change_password.html",
            "templates/chart.html": "web/templates/pages/chart.html",
            "templates/error.html": "web/templates/pages/error.html",
            "templates/index.html": "web/templates/pages/index.html",
            "templates/initiate_password_reset.html": "web/templates/pages/initiate_password_reset.html",
            "templates/login.html": "web/templates/pages/login.html",
            "templates/privacy_notice.html": "web/templates/pages/privacy_notice.html",
            "templates/register.html": "web/templates/pages/register.html",
            "templates/reset_password.html": "web/templates/pages/reset_password.html",
            "templates/simple_test.html": "web/templates/pages/simple_test.html",
            "templates/subscription.html": "web/templates/pages/subscription.html",
            "templates/subscription_renewal.html": "web/templates/pages/subscription_renewal.html",
            "templates/terms_and_conditions.html": "web/templates/pages/terms_and_conditions.html",
            "templates/trace.html": "web/templates/pages/trace.html",
            "templates/verify_phone.html": "web/templates/pages/verify_phone.html",
            
            # Tests
            "tests/test_trace_coverage.py": "tests/integration/trace/test_trace_coverage.py",
            "tests/test_trace_diagnostics.py": "tests/integration/trace/test_trace_diagnostics.py",
            "tests/test_trace_emission_gap.py": "tests/integration/trace/test_trace_emission_gap.py",
            "tests/test_trace_emission_timing.py": "tests/integration/trace/test_trace_emission_timing.py",
            "tests/test_trace_flow_validation.py": "tests/integration/trace/test_trace_flow_validation.py",
            "tests/test_trace_format_validator.py": "tests/integration/trace/test_trace_format_validator.py",
            "tests/test_trace_highlow_analysis.py": "tests/integration/trace/test_trace_highlow_analysis.py",
            "tests/test_trace_lost_events.py": "tests/integration/trace/test_trace_lost_events.py",
            "tests/test_trace_orchestrator.py": "tests/integration/trace/test_trace_orchestrator.py",
            "tests/test_trace_run_all_tests.py": "tests/integration/trace/test_trace_run_all_tests.py",
            "tests/test_trace_run_all_tests_diag.py": "tests/integration/trace/test_trace_run_all_tests_diag.py",
            "tests/test_trace_statistical.py": "tests/integration/trace/test_trace_statistical.py",
            "tests/test_trace_surge_analysis.py": "tests/integration/trace/test_trace_surge_analysis.py",
            "tests/test_trace_system_health.py": "tests/integration/trace/test_trace_system_health.py",
            "tests/test_trace_trend_analysis.py": "tests/integration/trace/test_trace_trend_analysis.py",
            "tests/test_trace_user_connections.py": "tests/integration/trace/test_trace_user_connections.py",
            "tests/test_trace_visualization.py": "tests/integration/trace/test_trace_visualization.py",
            "tests/test_utilities.py": "tests/unit/test_utilities.py",
            "tests/trace_analysis_tools.md": "tests/fixtures/trace/trace_analysis_tools.md",
            "tests/trace_analyzer_base.py": "tests/fixtures/trace/trace_analyzer_base.py",
            "tests/trace_component_definitions.py": "tests/fixtures/trace/trace_component_definitions.py",
            "tests/trace_system_documentation.md": "tests/fixtures/trace/trace_system_documentation.md",
            "tests/util_prepare_viz_data.py": "scripts/dev_tools/util_prepare_viz_data.py",
            "tests/util_trace_dump_utility.py": "tests/fixtures/trace/util_trace_dump_utility.py",
            "tests/__init__.py": "tests/fixtures/__init__.py",
            "tests/modules/__init__.py": "tests/fixtures/__init__.py",
        }
        
        return mapping
    
    def migrate_files(self, dry_run: bool = True):
        """Migrate files based on mapping."""
        mapping = self.create_comprehensive_mapping()
        
        print("=" * 60)
        print("TickStock V2 File Migration")
        print("=" * 60)
        print(f"Mode: {'DRY RUN' if dry_run else 'ACTUAL MIGRATION'}")
        print(f"Source: {self.source_dir}")
        print(f"Destination: {self.dest_dir}")
        print("=" * 60)
        
        # Categorize files
        found_files = set()
        missing_files = []
        successful_migrations = []
        failed_migrations = []
        
        # Scan source directory
        for root, dirs, files in os.walk(self.source_dir):
            # Skip certain directories
            dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'venv', '.venv', 'node_modules']]
            
            for file in files:
                # Skip Python cache files
                if file.endswith('.pyc'):
                    continue
                    
                rel_path = os.path.relpath(os.path.join(root, file), self.source_dir)
                rel_path = rel_path.replace('\\', '/')  # Normalize path separators
                found_files.add(rel_path)
        
        # Process mappings
        for source_file, dest_file in mapping.items():
            source_path = self.source_dir / source_file.replace('/', os.sep)
            dest_path = self.dest_dir / dest_file.replace('/', os.sep)
            
            if source_path.exists():
                if not dry_run:
                    try:
                        # Create destination directory
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        # Copy file
                        shutil.copy2(source_path, dest_path)
                        successful_migrations.append((source_file, dest_file))
                        print(f"✓ Migrated: {source_file} -> {dest_file}")
                    except Exception as e:
                        failed_migrations.append((source_file, dest_file, str(e)))
                        print(f"✗ Failed: {source_file} -> {dest_file}: {e}")
                else:
                    successful_migrations.append((source_file, dest_file))
                    print(f"  Would migrate: {source_file} -> {dest_file}")
            else:
                missing_files.append(source_file)
                if not source_file.endswith('__init__.py'):  # Don't warn about __init__ files
                    print(f"⚠ Not found in source: {source_file}")
        
        # Identify unmapped files
        mapped_sources = set(mapping.keys())
        unmapped = found_files - mapped_sources
        
        # Save reports
        self._save_migration_report(successful_migrations, failed_migrations, 
                                   missing_files, list(unmapped), dry_run)
        
        # Print summary
        print("\n" + "=" * 60)
        print("MIGRATION SUMMARY")
        print("=" * 60)
        print(f"Total files in source: {len(found_files)}")
        print(f"Files mapped: {len(successful_migrations)}")
        print(f"Files not found: {len(missing_files)}")
        print(f"Files unmapped: {len(unmapped)}")
        if not dry_run:
            print(f"Failed migrations: {len(failed_migrations)}")
        
        if unmapped:
            print("\nUnmapped files (not in migration plan):")
            for file in sorted(unmapped)[:10]:
                print(f"  - {file}")
            if len(unmapped) > 10:
                print(f"  ... and {len(unmapped) - 10} more")
        
        if not dry_run:
            print(f"\n✅ Migration completed!")
        else:
            print(f"\n📋 Dry run completed. Run with --execute to perform actual migration.")
        
        return successful_migrations, failed_migrations, missing_files, list(unmapped)
    
    def _save_migration_report(self, successful, failed, missing, unmapped, dry_run):
        """Save detailed migration report."""
        report = {
            "timestamp": str(Path.cwd()),
            "mode": "dry_run" if dry_run else "actual",
            "source": str(self.source_dir),
            "destination": str(self.dest_dir),
            "successful_migrations": successful,
            "failed_migrations": failed,
            "missing_files": missing,
            "unmapped_files": unmapped,
            "statistics": {
                "total_mapped": len(successful),
                "total_failed": len(failed),
                "total_missing": len(missing),
                "total_unmapped": len(unmapped)
            }
        }
        
        # Save JSON report
        report_file = self.dest_dir / "migration_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Save human-readable report
        readable_file = self.dest_dir / "migration_report.txt"
        with open(readable_file, 'w') as f:
            f.write("TICKSTOCK V2 MIGRATION REPORT\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Mode: {'DRY RUN' if dry_run else 'ACTUAL MIGRATION'}\n")
            f.write(f"Source: {self.source_dir}\n")
            f.write(f"Destination: {self.dest_dir}\n\n")
            
            f.write("STATISTICS:\n")
            f.write(f"  Successful: {len(successful)}\n")
            f.write(f"  Failed: {len(failed)}\n")
            f.write(f"  Missing: {len(missing)}\n")
            f.write(f"  Unmapped: {len(unmapped)}\n\n")
            
            if failed:
                f.write("FAILED MIGRATIONS:\n")
                for source, dest, error in failed:
                    f.write(f"  {source} -> {dest}\n")
                    f.write(f"    Error: {error}\n")
                f.write("\n")
            
            if unmapped:
                f.write("UNMAPPED FILES:\n")
                for file in sorted(unmapped):
                    f.write(f"  - {file}\n")
        
        print(f"\n📄 Reports saved to:")
        print(f"  - {report_file}")
        print(f"  - {readable_file}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate TickStock files to V2 structure")
    parser.add_argument("--execute", action="store_true", 
                       help="Execute actual migration (default is dry run)")
    parser.add_argument("--source", default=r"C:\Users\McDude\TickStockApp",
                       help="Source directory")
    parser.add_argument("--dest", default=r"C:\Users\McDude\TickStockAppV2",
                       help="Destination directory")
    
    args = parser.parse_args()
    
    mapper = EnhancedFileMigrationMapper(args.source, args.dest)
    mapper.migrate_files(dry_run=not args.execute)


if __name__ == "__main__":
    main()