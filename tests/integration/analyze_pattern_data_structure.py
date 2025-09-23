"""
Pattern Data Structure Analysis
Analyze the structure and content of pattern data to understand the communication failure.
"""

import psycopg2
import json
from datetime import datetime

def analyze_pattern_detections():
    """Analyze the pattern_detections table structure and data."""
    print("ANALYZING PATTERN_DETECTIONS TABLE")
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
        
        # Get table structure
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'pattern_detections'
            ORDER BY ordinal_position
        """)
        
        columns = cursor.fetchall()
        print("Table Structure:")
        for col in columns:
            print(f"  {col[0]}: {col[1]} ({'NULL' if col[2] == 'YES' else 'NOT NULL'})")
        
        # Sample data
        print("\nSample Data (10 records):")
        cursor.execute("""
            SELECT id, symbol, pattern_type, confidence, detected_at, source
            FROM pattern_detections
            ORDER BY detected_at DESC
            LIMIT 10
        """)
        
        samples = cursor.fetchall()
        for sample in samples:
            print(f"  ID: {sample[0]}, Symbol: {sample[1]}, Pattern: {sample[2]}, "
                  f"Confidence: {sample[3]}, Detected: {sample[4]}, Source: {sample[5]}")
        
        # Pattern type distribution
        print("\nPattern Type Distribution:")
        cursor.execute("""
            SELECT pattern_type, COUNT(*) as count
            FROM pattern_detections
            GROUP BY pattern_type
            ORDER BY count DESC
            LIMIT 15
        """)
        
        patterns = cursor.fetchall()
        for pattern in patterns:
            print(f"  {pattern[0]}: {pattern[1]}")
        
        # Source distribution
        print("\nSource Distribution:")
        cursor.execute("""
            SELECT source, COUNT(*) as count
            FROM pattern_detections
            GROUP BY source
            ORDER BY count DESC
        """)
        
        sources = cursor.fetchall()
        for source in sources:
            print(f"  {source[0]}: {source[1]}")
        
        # Date range
        print("\nDate Range:")
        cursor.execute("""
            SELECT MIN(detected_at) as earliest, MAX(detected_at) as latest
            FROM pattern_detections
        """)
        
        date_range = cursor.fetchone()
        print(f"  Earliest: {date_range[0]}")
        print(f"  Latest: {date_range[1]}")
        
        # Recent activity
        print("\nRecent Activity:")
        for days in [1, 7, 30]:
            cursor.execute(f"""
                SELECT COUNT(*) FROM pattern_detections 
                WHERE detected_at > NOW() - INTERVAL '{days} days'
            """)
            count = cursor.fetchone()[0]
            print(f"  Last {days} day(s): {count} patterns")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error analyzing pattern_detections: {e}")

def check_daily_intraday_tables():
    """Check the daily_patterns and intraday_patterns table structures."""
    print("\n\nCHECKING DAILY AND INTRADAY TABLES")
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
        
        # Check if tables exist
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name IN ('daily_patterns', 'intraday_patterns')
        """)
        
        existing_tables = [row[0] for row in cursor.fetchall()]
        print(f"Existing tables: {existing_tables}")
        
        # Check daily_patterns structure
        if 'daily_patterns' in existing_tables:
            print("\nDAILY_PATTERNS structure:")
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'daily_patterns'
                ORDER BY ordinal_position
            """)
            
            columns = cursor.fetchall()
            for col in columns:
                print(f"  {col[0]}: {col[1]} ({'NULL' if col[2] == 'YES' else 'NOT NULL'})")
        else:
            print("\nDAILY_PATTERNS table does not exist!")
        
        # Check intraday_patterns structure
        if 'intraday_patterns' in existing_tables:
            print("\nINTRADAY_PATTERNS structure:")
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'intraday_patterns'
                ORDER BY ordinal_position
            """)
            
            columns = cursor.fetchall()
            for col in columns:
                print(f"  {col[0]}: {col[1]} ({'NULL' if col[2] == 'YES' else 'NOT NULL'})")
        else:
            print("\nINTRADAY_PATTERNS table does not exist!")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error checking daily/intraday tables: {e}")

def check_tickstockpl_processes():
    """Check if TickStockPL processes are running."""
    print("\n\nCHECKING TICKSTOCKPL PROCESSES")
    print("=" * 50)
    
    import subprocess
    import os
    
    # Look for TickStockPL processes
    try:
        result = subprocess.run(['tasklist'], capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            processes = result.stdout.lower()
            tickstock_processes = []
            
            for line in processes.split('\n'):
                if 'tickstock' in line or 'python' in line:
                    tickstock_processes.append(line.strip())
            
            if tickstock_processes:
                print("Potential TickStock-related processes:")
                for proc in tickstock_processes[:10]:  # Limit output
                    print(f"  {proc}")
            else:
                print("No obvious TickStockPL processes found")
        
    except Exception as e:
        print(f"Error checking processes: {e}")
    
    # Check for TickStockPL directory
    tickstockpl_paths = [
        "C:\\TickStockPL",
        "C:\\Users\\McDude\\TickStockPL",
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "TickStockPL")
    ]
    
    print("\nChecking for TickStockPL installation:")
    for path in tickstockpl_paths:
        if os.path.exists(path):
            print(f"  FOUND: {path}")
            # List some contents
            try:
                contents = os.listdir(path)
                print(f"    Contents (first 10): {contents[:10]}")
            except:
                pass
        else:
            print(f"  NOT FOUND: {path}")

def main():
    """Run pattern data structure analysis."""
    print("PATTERN DATA STRUCTURE ANALYSIS")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    analyze_pattern_detections()
    check_daily_intraday_tables() 
    check_tickstockpl_processes()
    
    print("\n" + "=" * 50)
    print("ANALYSIS COMPLETE")

if __name__ == "__main__":
    main()