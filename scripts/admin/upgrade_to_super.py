#!/usr/bin/env python3
"""
Upgrade a user to super role (full access to both admin and regular areas)
"""

import psycopg2
import os
from dotenv import load_dotenv

def upgrade_to_super():
    load_dotenv()
    DATABASE_URI = os.getenv('DATABASE_URI', 'postgresql://app_readwrite:LJI48rUEkUpe6e@localhost:5433/tickstock')
    
    try:
        conn = psycopg2.connect(DATABASE_URI)
        cursor = conn.cursor()
        
        print("Available users with admin/super roles:")
        cursor.execute("SELECT id, email, username, role FROM users WHERE role IN ('admin', 'super') ORDER BY id")
        admin_users = cursor.fetchall()
        
        if not admin_users:
            print("No admin or super users found")
            return
        
        for user in admin_users:
            print(f"ID: {user[0]:2} | Email: {user[1]:30} | Username: {user[2]:15} | Role: {user[3]}")
        
        user_input = input("\nEnter user ID or email to upgrade to super: ").strip()
        
        # Find the user
        if user_input.isdigit():
            cursor.execute("SELECT id, email, username, role FROM users WHERE id = %s", (int(user_input),))
        else:
            cursor.execute("SELECT id, email, username, role FROM users WHERE email = %s", (user_input,))
        
        target_user = cursor.fetchone()
        
        if not target_user:
            print("User not found")
            return
        
        print(f"\nUpgrading user: {target_user[1]} ({target_user[2]}) from '{target_user[3]}' to 'super'")
        confirm = input("Continue? (y/N): ").strip().lower()
        
        if confirm != 'y':
            print("Cancelled")
            return
        
        # Upgrade to super
        cursor.execute("UPDATE users SET role = 'super' WHERE id = %s", (target_user[0],))
        conn.commit()
        
        print(f"\nSUCCESS: User upgraded to super role!")
        print(f"User: {target_user[1]} ({target_user[2]})")
        print(f"New Role: super")
        print(f"\nSuper users can access:")
        print(f"  - All regular user pages (dashboard, account, etc.)")
        print(f"  - All admin pages (user management, historical data, health monitor)")
        print(f"  - Full system access")
        
        # Show role summary
        print(f"\nRole Summary:")
        cursor.execute("SELECT role, COUNT(*) FROM users GROUP BY role ORDER BY role")
        roles = cursor.fetchall()
        for role, count in roles:
            print(f"  {role}: {count} users")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    upgrade_to_super()