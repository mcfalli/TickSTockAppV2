#!/usr/bin/env python3
"""
Add role-based admin system and make specific user an admin
"""

import psycopg2
import os
from dotenv import load_dotenv

def setup_admin_system():
    load_dotenv()
    DATABASE_URI = os.getenv('DATABASE_URI', 'postgresql://app_readwrite:LJI48rUEkUpe6e@localhost:5433/tickstock')
    
    try:
        conn = psycopg2.connect(DATABASE_URI)
        cursor = conn.cursor()
        
        print("🔧 Setting up admin role system...")
        
        # Step 1: Add role column to users table
        print("1. Adding role column to users table...")
        try:
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN role VARCHAR(20) DEFAULT 'user' NOT NULL
            """)
            print("   ✅ Role column added successfully")
        except psycopg2.errors.DuplicateColumn:
            cursor.execute("ROLLBACK")
            print("   ℹ️  Role column already exists")
        
        # Step 2: Show available users to choose from
        print("\n2. Available users:")
        cursor.execute("SELECT id, email, username FROM users ORDER BY id")
        users = cursor.fetchall()
        
        for user in users:
            print(f"   ID: {user[0]:2} | Email: {user[1]:30} | Username: {user[2]}")
        
        # Step 3: Let user choose which account to make admin
        print("\n3. Which user should be made admin?")
        user_choice = input("   Enter user ID or email: ").strip()
        
        # Find the user
        if user_choice.isdigit():
            cursor.execute("SELECT id, email, username FROM users WHERE id = %s", (int(user_choice),))
        else:
            cursor.execute("SELECT id, email, username FROM users WHERE email = %s", (user_choice,))
        
        target_user = cursor.fetchone()
        
        if not target_user:
            print("   ❌ User not found")
            return
        
        # Step 4: Make the user an admin
        cursor.execute("UPDATE users SET role = 'admin' WHERE id = %s", (target_user[0],))
        
        # Step 5: Also ensure they're verified and active
        cursor.execute("""
            UPDATE users SET 
                is_verified = true,
                is_active = true,
                terms_accepted = true,
                terms_accepted_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (target_user[0],))
        
        conn.commit()
        
        print(f"\n✅ SUCCESS: User setup complete!")
        print(f"   User: {target_user[1]} ({target_user[2]})")
        print(f"   Role: admin")
        print(f"   Status: verified, active, terms accepted")
        print(f"\n🔑 You can now log in with this account and access:")
        print(f"   Login: http://localhost:5000/login")
        print(f"   Admin: http://localhost:5000/admin/historical-data")
        
        # Step 6: Show role summary
        print(f"\n📊 Role Summary:")
        cursor.execute("SELECT role, COUNT(*) FROM users GROUP BY role")
        roles = cursor.fetchall()
        for role, count in roles:
            print(f"   {role}: {count} users")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    setup_admin_system()