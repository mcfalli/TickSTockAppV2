#!/usr/bin/env python3
"""
Simple admin setup - Add role column and show users
"""

import psycopg2
import os
from dotenv import load_dotenv

def simple_admin_setup():
    load_dotenv()
    DATABASE_URI = os.getenv('DATABASE_URI', 'postgresql://app_readwrite:LJI48rUEkUpe6e@localhost:5432/tickstock')
    
    try:
        conn = psycopg2.connect(DATABASE_URI)
        cursor = conn.cursor()
        
        print("Setting up admin role system...")
        
        # Add role column
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'user' NOT NULL")
            print("Role column added successfully")
        except:
            cursor.execute("ROLLBACK")
            print("Role column already exists")
        
        # Show available users
        print("\nAvailable users:")
        cursor.execute("SELECT id, email, username FROM users ORDER BY id")
        users = cursor.fetchall()
        
        for user in users:
            print(f"ID: {user[0]:2} | Email: {user[1]:30} | Username: {user[2]}")
        
        # Make first user admin for now
        if users:
            first_user = users[0]
            cursor.execute("UPDATE users SET role = 'admin' WHERE id = %s", (first_user[0],))
            
            # Also ensure they're verified and active
            cursor.execute("""
                UPDATE users SET 
                    is_verified = true,
                    is_active = true,
                    terms_accepted = true,
                    terms_accepted_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (first_user[0],))
            
            conn.commit()
            
            print(f"\nSUCCESS: User setup complete!")
            print(f"User: {first_user[1]} ({first_user[2]})")
            print(f"Role: admin")
            print(f"Status: verified, active, terms accepted")
            print(f"\nYou can now log in with this account:")
            print(f"Login: http://localhost:5000/login")
            print(f"Admin: http://localhost:5000/admin/historical-data")
            
            # Show role summary
            print(f"\nRole Summary:")
            cursor.execute("SELECT role, COUNT(*) FROM users GROUP BY role")
            roles = cursor.fetchall()
            for role, count in roles:
                print(f"{role}: {count} users")
        else:
            print("No users found in database")
            
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    simple_admin_setup()