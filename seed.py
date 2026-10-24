import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models import User
from config import Config
from app.ai.ai_utils import load_models


def seed_database():
    app = create_app('development')
    
    with app.app_context():
        print("Dropping all tables...")
        db.drop_all()
        print("Creating all tables...")
        db.create_all()
        
        print("Loading AI models...")
        load_models()
        
        print("Creating admin user...")
        create_demo_users()
        
        print("Seeding complete!")


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
    seed_database()