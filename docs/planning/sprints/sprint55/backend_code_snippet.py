"""
Backend Code Snippet for Universe Loader Consolidation
File: src/api/rest/admin_historical_data_redis.py
Function: trigger_universe_load() starting at line 805

INSTRUCTIONS:
1. Open src/api/rest/admin_historical_data_redis.py
2. Find the function: def trigger_universe_load():  (line 805)
3. Replace lines 810-862 with the code below (between the === markers)
4. Keep everything else unchanged (lines 863-920 stay the same)

===== START: REPLACE LINES 810-862 WITH THIS CODE =====
"""

    try:
        # Get parameters
        csv_file = request.form.get('csv_file')
        universe_key_full = request.form.get('universe_key')
        years = request.form.get('years', 1, type=float)
        include_ohlcv = request.form.get('include_ohlcv', 'true') == 'true'

        symbols = []
        source_name = ''

        # Determine source: CSV file or cached universe
        if csv_file:
            # === CSV FILE MODE ===
            app.logger.info(f"CSV mode: {csv_file}, years={years}, OHLCV={include_ohlcv}")

            # Read symbols from CSV file
            import csv
            import os
            csv_path = os.path.join('data/universes', csv_file)

            if not os.path.exists(csv_path):
                return jsonify({'error': f'CSV file not found: {csv_file}'}), 404

            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    symbol = row.get('symbol', '').strip()
                    if symbol:
                        symbols.append(symbol)

            source_name = csv_file
            app.logger.info(f"Loaded {len(symbols)} symbols from CSV: {csv_file}")

        elif universe_key_full:
            # === CACHED UNIVERSE MODE ===
            app.logger.info(f"Cached mode: {universe_key_full}, years={years}")

            # Parse universe key (format: "etf_universe:etf_core")
            if ':' not in universe_key_full:
                return jsonify({'error': 'Invalid universe key format'}), 400

            universe_type, universe_key = universe_key_full.split(':', 1)

            # Get symbols from cache
            from src.infrastructure.cache.cache_control import CacheControl
            cache_control = CacheControl()

            if universe_type == 'etf_universe':
                for name, keys_dict in cache_control.cache.get('etf_universes', {}).items():
                    if universe_key in keys_dict:
                        value = keys_dict[universe_key]
                        symbols = value if isinstance(value, list) else value.get('symbols', [])
                        break

            elif universe_type == 'stock_etf_combo':
                for name, keys_dict in cache_control.cache.get('stock_etf_combos', {}).items():
                    if universe_key in keys_dict:
                        value = keys_dict[universe_key]
                        symbols = value if isinstance(value, list) else value.get('symbols', [])
                        break

            if not symbols:
                return jsonify({'error': f'No symbols found for: {universe_key}'}), 404

            source_name = universe_key_full
            app.logger.info(f"Found {len(symbols)} symbols from cache: {universe_key_full}")

        else:
            return jsonify({'error': 'Either csv_file or universe_key required'}), 400

        if not symbols:
            return jsonify({'error': f'No symbols found in {source_name}'}), 404

        app.logger.info(f"Total symbols to load: {len(symbols)} from {source_name}")

"""
===== END: CODE TO PASTE =====

AFTER PASTING:
- Lines 863-920 should remain unchanged (job creation, Redis publish, etc.)
- Total function should be ~115 lines (was ~85, added ~30 for CSV logic)
- Save the file

THEN:
1. Run: python scripts/util/clear_job_keys.py
2. Restart Flask: python src/app.py
3. Test CSV loading (dow_30.csv)
4. Test cached universe loading (Core ETFs)

VERIFICATION:
- Both sources should work via same endpoint
- Job submission returns 200 OK
- Status polling works without WRONGTYPE errors
"""
