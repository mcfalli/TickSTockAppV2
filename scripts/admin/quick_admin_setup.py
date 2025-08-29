#!/usr/bin/env python3
"""
Quick setup - Add role column and make test@example.com an admin
"""

import psycopg2
import os
from dotenv import load_dotenv

def quick_admin_setup():
    load_dotenv()
    DATABASE_URI = os.getenv('DATABASE_URI', 'postgresql://app_readwrite:LJI48rUEkUpe6e@localhost:5433/tickstock')
    
    try:
        conn = psycopg2.connect(DATABASE_URI)
        cursor = conn.cursor()
        
        # Add role column
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'user' NOT NULL")
            print("✅ Added role column")
        except:
            cursor.execute("ROLLBACK")
            print("ℹ️  Role column already exists")
        
        # Make test@example.com an admin
        cursor.execute("""
            UPDATE users SET 
                role = 'admin',
                is_verified = true,
                is_active = true,
                terms_accepted = true,
                terms_accepted_at = CURRENT_TIMESTAMP
            WHERE email = 'test@example.com'
        """)
        
        if cursor.rowcount > 0:
            conn.commit()
            print("✅ test@example.com is now an admin!")
            print("🔑 You can login at: http://localhost:5000/login")
            print("   Email: test@example.com")
            print("   (Use existing password)")
        else:
            print("❌ User test@example.com not found")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    quick_admin_setup()