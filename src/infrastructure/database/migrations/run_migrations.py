"""
Direct Migration Runner
Run migrations without Flask CLI conflicts.


Updated Migration Commands
bash# Create new migration from model changes
python model_migrations_run.py migrate "Description of changes"

# Apply migrations to database
python model_migrations_run.py upgrade

# Initialize migrations (already done)
python model_migrations_run.py init

# Mark database as current (already done)
python model_migrations_run.py stamp
Your Complete Migration Workflow
For future database changes:

Modify your models in model.py
Create migration: python model_migrations_run.py migrate "Add market data tables"
Apply migration: python model_migrations_run.py upgrade

Additional helpful commands:
bash# Check current migration version
python model_migrations_run.py current

# See migration history
python model_migrations_run.py history

"""

import os
import sys

def run_migration_command(command, message=None):
    """Run migration commands directly."""
    
    try:
        # Import Flask components WITHOUT importing anything that triggers eventlet
        from flask import Flask
        from flask_migrate import Migrate, init, migrate, upgrade, stamp
        
        # Import components that don't have eventlet monkey patching
        import logging
        from datetime import datetime, timezone
        
        # Configure basic logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
        
        # Load environment configuration directly
        from src.core.services.startup_service import load_environment_config
        env_config = load_environment_config()
        
        # Create minimal Flask app for migrations
        app = Flask(__name__)
        
        # Configure database
        app.config['SQLALCHEMY_DATABASE_URI'] = env_config['DATABASE_URI']
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        # Import and initialize database
        from src.infrastructure.database import db
        db.init_app(app)
        
        # Initialize Flask-Migrate
        migrate_instance = Migrate(app, db)
        
        with app.app_context():
            if command == 'init':
                print("Initializing migration repository...")
                init()
                print("[SUCCESS] Migration repository initialized")
                
            elif command == 'migrate':
                print(f"Creating migration: {message}")
                migrate(message=message)
                print("[SUCCESS] Migration created")
                
            elif command == 'upgrade':
                print("Upgrading database...")
                upgrade()
                print("[SUCCESS] Database upgraded")
                
            elif command == 'stamp':
                print("Stamping database as current...")
                stamp()
                print("[SUCCESS] Database stamped")
                
            else:
                print(f"Unknown command: {command}")
                return False
                
        return True
        
    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python run_migrations.py <command> [message]")
        print("Commands: init, migrate, upgrade, stamp")
        print("\nExamples:")
        print("  python run_migrations.py init")
        print("  python run_migrations.py migrate \"Add new table\"")
        print("  python run_migrations.py upgrade")
        print("  python run_migrations.py stamp")
        sys.exit(1)
    
    command = sys.argv[1]
    message = ' '.join(sys.argv[2:]) if len(sys.argv) > 2 else None
    
    if command == 'migrate' and not message:
        print("Error: migrate command requires a message")
        sys.exit(1)
    
    success = run_migration_command(command, message)
    sys.exit(0 if success else 1)