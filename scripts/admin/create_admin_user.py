#!/usr/bin/env python3
"""
Quick script to create an admin user for testing
"""

import os
import sys
from dotenv import load_dotenv
load_dotenv()

# Add src to path
sys.path.append('src')

import psycopg2
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta

def create_admin_user():
    DATABASE_URI = os.getenv('DATABASE_URI', 'postgresql://app_readwrite:LJI48rUEkUpe6e@localhost:5432/tickstock')
    
    try:
        conn = psycopg2.connect(DATABASE_URI)
        cursor = conn.cursor()
        
        # Admin user details
        email = "admin@tickstock.local"
        username = "admin"
        password = "admin123"  # Simple password for testing
        
        # Hash the password
        password_hash = generate_password_hash(password)
        
        # Check if admin user already exists
        cursor.execute("SELECT id FROM users WHERE email = %s OR username = %s", (email, username))
        existing = cursor.fetchone()
        
        if existing:
            print(f"Admin user already exists with ID: {existing[0]}")
            print(f"Email: {email}")
            print(f"Password: {password}")
            return
        
        # Create admin user
        cursor.execute("""
            INSERT INTO users (
                email, username, password_hash, 
                is_verified, subscription_active, subscription_end_date,
                created_at, role
            ) VALUES (
                %s, %s, %s, 
                %s, %s, %s,
                %s, %s
            )
        """, (
            email, username, password_hash,
            True,  # is_verified
            True,  # subscription_active  
            datetime.now() + timedelta(days=365),  # subscription_end_date
            datetime.now(),  # created_at
            'admin'  # role (if column exists)
        ))
        
        conn.commit()
        user_id = cursor.lastrowid
        
        print("✅ Admin user created successfully!")
        print(f"Email: {email}")
        print(f"Username: {username}")
        print(f"Password: {password}")
        print(f"Role: admin")
        print("\nYou can now log in at: http://localhost:5000/login")
        
    except psycopg2.errors.UndefinedColumn:
        # Role column might not exist yet, try without it
        cursor.execute("ROLLBACK")
        cursor.execute("""
            INSERT INTO users (
                email, username, password_hash, 
                is_verified, subscription_active, subscription_end_date,
                created_at
            ) VALUES (
                %s, %s, %s, 
                %s, %s, %s,
                %s
            )
        """, (
            email, username, password_hash,
            True,  # is_verified
            True,  # subscription_active  
            datetime.now() + timedelta(days=365),  # subscription_end_date
            datetime.now()  # created_at
        ))
        
        conn.commit()
        
        print("✅ Admin user created successfully (without role field)!")
        print(f"Email: {email}")
        print(f"Username: {username}")
        print(f"Password: {password}")
        print("\nYou can now log in at: http://localhost:5000/login")
        print("\n⚠️  Note: Role-based access control not yet implemented - any user can access admin routes")
        
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        conn.rollback()
        
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    create_admin_user()