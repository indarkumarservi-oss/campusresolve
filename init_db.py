import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models import User
from config import Config


def init_database():
    """Initialize database with tables and demo data."""
    print("Starting database initialization...")
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
            print("Admin user created successfully!")
        else:
            print(f"Admin user already exists: {admin.email}")
        
        print("Database initialization complete!")


def create_demo_users():
    demo = Config.DEMO_ACCOUNTS
    email = demo['admin']['email']
    password = demo['admin']['password']
    
    print(f"Creating admin with email: {email}")
    
    admin = User(
        full_name='Admin User',
        email=email,
        role='admin',
        is_active=True,
        is_approved=True
    )
    admin.set_password(password)
    db.session.add(admin)
    
    try:
        db.session.commit()
        print("Admin user committed to database")
        
        # Verify the user was created and password works
        verify_admin = User.query.filter_by(email=email).first()
        if verify_admin:
            print(f"Verified admin exists: {verify_admin.email}")
            print(f"Password check: {verify_admin.check_password(password)}")
        else:
            print("ERROR: Admin user not found after commit!")
    except Exception as e:
        db.session.rollback()
        print(f"ERROR creating admin: {e}")
        raise


if __name__ == '__main__':
    init_database()