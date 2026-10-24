import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models import User
from config import Config


def init_database():
    """Initialize database with tables and demo data."""
    app = create_app('production')
    
    with app.app_context():
        print("Creating all tables...")
        db.create_all()
        
        print("Loading AI models...")
        try:
            from app.ai.ai_utils import load_models
            load_models()
            print("AI models loaded successfully")
        except Exception as e:
            print(f"Warning: Could not load AI models: {e}")
        
        print("Checking for existing users...")
        admin = User.query.filter_by(role='admin').first()
        
        if not admin:
            print("Creating admin user...")
            create_demo_users()
        
        print("Database initialization complete!")


def create_demo_users():
    demo = Config.DEMO_ACCOUNTS
    
    admin = User(
        full_name='Admin User',
        email=demo['admin']['email'],
        role='admin',
        is_active=True,
        is_approved=True
    )
    admin.set_password(demo['admin']['password'])
    db.session.add(admin)
    
    db.session.commit()
    print("Created admin user")


if __name__ == '__main__':
    init_database()