import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models import User, Complaint, StatusHistory, Feedback, Notification
from config import TestingConfig


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        # Prevent objects from expiring after commit
        db.session.expire_on_commit = False
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


@pytest.fixture
def admin_user(app):
    with app.app_context():
        user = User(
            full_name='Test Admin',
            email='admin@test.com',
            role='admin',
            is_active=True
        )
        user.set_password('Admin@123')
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user


@pytest.fixture
def staff_user(app):
    with app.app_context():
        user = User(
            full_name='Test Staff',
            email='staff@test.com',
            role='staff',
            department='IT Cell',
            is_active=True,
            is_approved=True
        )
        user.set_password('Staff@123')
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user


@pytest.fixture
def student_user(app):
    with app.app_context():
        user = User(
            full_name='Test Student',
            email='student@test.com',
            role='student',
            is_active=True
        )
        user.set_password('Student@123')
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user


@pytest.fixture
def logged_in_admin(client, admin_user):
    client.post('/auth/login', data={
        'email': 'admin@test.com',
        'password': 'Admin@123'
    }, follow_redirects=True)
    return admin_user


@pytest.fixture
def logged_in_staff(client, staff_user):
    client.post('/auth/login', data={
        'email': 'staff@test.com',
        'password': 'Staff@123'
    }, follow_redirects=True)
    return staff_user


@pytest.fixture
def logged_in_student(client, student_user):
    client.post('/auth/login', data={
        'email': 'student@test.com',
        'password': 'Student@123'
    }, follow_redirects=True)
    return student_user


@pytest.fixture
def sample_complaint(app, student_user):
    with app.app_context():
        student = db.session.merge(student_user)
        complaint = Complaint(
            ticket_number='CR-2026-0001',
            student_id=student.id,
            title='Test Complaint',
            description='This is a test complaint description with enough characters.',
            category='IT Support',
            priority='High',
            department='IT Cell',
            status='Submitted'
        )
        db.session.add(complaint)
        db.session.commit()
        db.session.refresh(complaint)
        return complaint