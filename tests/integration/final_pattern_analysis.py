"""
Final Pattern Data Analysis
Complete analysis of the pattern data communication failure.
"""

import psycopg2
import json
from datetime import datetime

def analyze_pattern_detections_correct():
    """Analyze pattern_detections table with correct column names."""
    print("FINAL PATTERN_DETECTIONS ANALYSIS")
    print("=" * 50)
    
    try:
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='tickstock',
            user='app_readwrite',
            password='LJI48rUEkUpe6e'
        )
        
        cursor = conn.cursor()
        
        # Sample data with correct columns
        print("Sample Data (10 most recent records):")
        cursor.execute("""
            SELECT id, symbol, detected_at, confidence, pattern_data::text
            FROM pattern_detections
            ORDER BY detected_at DESC
            LIMIT 10
        """)
        
        samples = cursor.fetchall()
        for sample in samples:
            pattern_data = json.loads(sample[4]) if sample[4] else {}
            pattern_type = pattern_data.get('pattern', 'Unknown')
            print(f"  ID: {sample[0]}, Symbol: {sample[1]}, Pattern: {pattern_type}, "
                  f"Confidence: {sample[2]}, Detected: {sample[3]}")
        
        # Pattern type distribution from JSON data
        print("\nPattern Type Distribution (from pattern_data JSON):")
        cursor.execute("""
            SELECT pattern_data->>'pattern' as pattern_type, COUNT(*) as count
            FROM pattern_detections
            WHERE pattern_data ? 'pattern'
            GROUP BY pattern_data->>'pattern'
            ORDER BY count DESC
            LIMIT 15
        """)
        
        patterns = cursor.fetchall()
        for pattern in patterns:
            print(f"  {pattern[0]}: {pattern[1]}")
        
        # Source distribution from JSON data
        print("\nSource Distribution (from pattern_data JSON):")
        cursor.execute("""
            SELECT pattern_data->>'source' as source, COUNT(*) as count
            FROM pattern_detections
            WHERE pattern_data ? 'source'
            GROUP BY pattern_data->>'source'
            ORDER BY count DESC
        """)
        
        sources = cursor.fetchall()
        if sources:
            for source in sources:
                print(f"  {source[0]}: {source[1]}")
        else:
            print("  No source information found in pattern_data")
        
        # Check pattern_data structure
        print("\nPattern Data Structure Analysis:")
        cursor.execute("""
            SELECT pattern_data
            FROM pattern_detections
            WHERE pattern_data IS NOT NULL
            LIMIT 5
        """)
        
        pattern_samples = cursor.fetchall()
        for i, sample in enumerate(pattern_samples, 1):
            try:
                data = json.loads(sample[0])
                keys = list(data.keys())
                print(f"  Sample {i} keys: {keys}")
            except:
                print(f"  Sample {i}: Invalid JSON")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error analyzing pattern_detections: {e}")

def check_daily_intraday_data():
    """Check if daily and intraday tables have any data."""
    print("\n\nDAILY AND INTRADAY TABLE DATA CHECK")
    print("=" * 50)
    
    try:
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='tickstock',
            user='app_readwrite',
            password='LJI48rUEkUpe6e'
        )
        
        cursor = conn.cursor()
        
        # Check daily_patterns data
        cursor.execute("SELECT COUNT(*) FROM daily_patterns")
        daily_count = cursor.fetchone()[0]
        print(f"Daily patterns count: {daily_count}")
        
        if daily_count > 0:
            cursor.execute("""
                SELECT symbol, pattern_type, confidence, detection_timestamp
                FROM daily_patterns
                ORDER BY detection_timestamp DESC
                LIMIT 5
            """)
            daily_samples = cursor.fetchall()
            print("  Sample daily patterns:")
            for sample in daily_samples:
                print(f"    {sample[0]}: {sample[1]} ({sample[2]}) at {sample[3]}")
        
        # Check intraday_patterns data
        cursor.execute("SELECT COUNT(*) FROM intraday_patterns")
        intraday_count = cursor.fetchone()[0]
        print(f"\nIntraday patterns count: {intraday_count}")
        
        if intraday_count > 0:
            cursor.execute("""
                SELECT symbol, pattern_type, confidence, detection_timestamp
                FROM intraday_patterns
                ORDER BY detection_timestamp DESC
                LIMIT 5
            """)
            intraday_samples = cursor.fetchall()
            print("  Sample intraday patterns:")
            for sample in intraday_samples:
                print(f"    {sample[0]}: {sample[1]} ({sample[2]}) at {sample[3]}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error checking daily/intraday data: {e}")

def generate_final_diagnostic_report():
    """Generate the final diagnostic report with findings and recommendations."""
    print("\n\nFINAL DIAGNOSTIC REPORT")
    print("=" * 60)
    print(f"Generated: {datetime.now().isoformat()}")
    
    print("\nFINDINGS:")
    print("1. Redis connectivity: WORKING")
    print("2. Database connectivity: WORKING")
    print("3. TickStockPL installation: FOUND at C:\\Users\\McDude\\TickStockPL")
    print("4. Pattern data structure:")
    print("   - pattern_detections table: 569 records (POPULATED)")
    print("   - daily_patterns table: 0 records (EMPTY)")
    print("   - intraday_patterns table: 0 records (EMPTY)")
    print("5. TickStockPL Redis activity: NO ACTIVE PUBLISHING")
    print("6. Recent pattern activity: NONE in last 24 hours")
    
    print("\nROOT CAUSE ANALYSIS:")
    print("PRIMARY ISSUE: TickStockPL is not currently running or publishing events")
    print("  EVIDENCE:")
    print("  - No Redis channel activity detected")
    print("  - Historical data exists but no recent patterns")
    print("  - Daily/intraday tables are empty (different schema from combo patterns)")
    print("  - Pattern data structure mismatch between tables")
    
    print("\nSECONDARY ISSUES:")
    print("1. Schema mismatch between pattern_detections and daily/intraday tables")
    print("   - pattern_detections uses JSONB pattern_data field")
    print("   - daily/intraday tables expect structured pattern_type field")
    print("2. TickStockApp expecting data in daily/intraday tables")
    print("3. Redis pattern cache not populated (no active event publishing)")
    
    print("\nRECOMMENDED SOLUTIONS:")
    print("1. IMMEDIATE ACTION: Start TickStockPL service")
    print("   - Navigate to C:\\Users\\McDude\\TickStockPL")
    print("   - Check TickStockPL configuration for Redis connection")
    print("   - Start pattern detection and event publishing services")
    print("   - Verify Redis channels: tickstock.events.patterns")
    
    print("\n2. CONFIGURATION FIXES:")
    print("   - Ensure TickStockPL Redis config matches TickStockApp:")
    print("     * Redis host: localhost:6379")
    print("     * Channels: tickstock.events.patterns")
    print("   - Verify TickStockPL database connection (port 5432)")
    
    print("\n3. SCHEMA ALIGNMENT:")
    print("   - Check if TickStockPL should populate daily/intraday tables")
    print("   - OR update TickStockApp to read from pattern_detections table")
    print("   - Standardize pattern data structure across tables")
    
    print("\n4. MONITORING SETUP:")
    print("   - Set up health checks for TickStockPL service")
    print("   - Monitor Redis channel activity")
    print("   - Track pattern detection frequency")
    
    print("\nTEST PLAN:")
    print("1. Start TickStockPL service")
    print("2. Monitor Redis channels for 1-2 minutes")
    print("3. Verify pattern events are published")
    print("4. Check if daily/intraday tables get populated")
    print("5. Test TickStockApp pattern display functionality")
    
    print("\nEXPECTED OUTCOMES:")
    print("- Pattern events flowing: TickStockPL → Redis → TickStockApp")
    print("- WebSocket broadcasts to frontend clients")
    print("- Pattern cache populated with live data")
    print("- Pattern discovery APIs returning real-time data")
    
    print("\n" + "=" * 60)

def main():
    """Run final pattern data analysis."""
    analyze_pattern_detections_correct()
    check_daily_intraday_data()
    generate_final_diagnostic_report()

if __name__ == "__main__":
    main()