#!/usr/bin/env python3
"""
Reset password for a user
"""

import psycopg2
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

def reset_password():
    load_dotenv()
    DATABASE_URI = os.getenv('DATABASE_URI', 'postgresql://app_readwrite:LJI48rUEkUpe6e@localhost:5433/tickstock')
    
    try:
        conn = psycopg2.connect(DATABASE_URI)
        cursor = conn.cursor()
        
        email = input("Enter email address: ").strip()
        new_password = input("Enter new password: ").strip()
        
        if not email or not new_password:
            print("Email and password required")
            return
        
        # Check if user exists
        cursor.execute("SELECT id, email FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        
        if not user:
            print(f"User {email} not found")
            return
        
        # Hash the password
        password_hash = generate_password_hash(new_password)
        
        # Update password
        cursor.execute("UPDATE users SET password_hash = %s WHERE email = %s", (password_hash, email))
        conn.commit()
        
        print(f"Password updated for {email}")
        print(f"You can now login at: http://localhost:5000/login")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    reset_password()