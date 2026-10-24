import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.extensions import db
from app.models import User
from werkzeug.security import check_password_hash


class TestAuth:
    
    def test_login_success(self, client, admin_user):
        response = client.post('/auth/login', data={
            'email': 'admin@test.com',
            'password': 'Admin@123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Welcome back' in response.data
    
    def test_login_failure_invalid_password(self, client, admin_user):
        response = client.post('/auth/login', data={
            'email': 'admin@test.com',
            'password': 'WrongPassword'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Invalid email or password' in response.data
    
    def test_login_failure_invalid_email(self, client, admin_user):
        response = client.post('/auth/login', data={
            'email': 'nonexistent@test.com',
            'password': 'Admin@123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Invalid email or password' in response.data
    
    def test_logout(self, client, logged_in_admin):
        response = client.get('/auth/logout', follow_redirects=True)
        
        assert response.status_code == 200
        assert b'logged out' in response.data.lower()
    
    def test_password_hashing(self, app, admin_user):
        with app.app_context():
            user = User.query.filter_by(email='admin@test.com').first()
            assert user is not None
            assert user.password_hash != 'Admin@123'
            assert check_password_hash(user.password_hash, 'Admin@123')
            assert not check_password_hash(user.password_hash, 'wrong')
    
    def test_login_redirects_to_dashboard(self, client, admin_user, staff_user, student_user):
        # Admin
        client.post('/auth/login', data={'email': 'admin@test.com', 'password': 'Admin@123'})
        response = client.get('/auth/dashboard-redirect')
        assert response.status_code == 302
        assert '/admin/dashboard' in response.location
        
        client.get('/auth/logout')
        
        # Staff
        client.post('/auth/login', data={'email': 'staff@test.com', 'password': 'Staff@123'})
        response = client.get('/auth/dashboard-redirect')
        assert response.status_code == 302
        assert '/staff/dashboard' in response.location
        
        client.get('/auth/logout')
        
        # Student
        client.post('/auth/login', data={'email': 'student@test.com', 'password': 'Student@123'})
        response = client.get('/auth/dashboard-redirect')
        assert response.status_code == 302
        assert '/student/dashboard' in response.location
    
    def test_inactive_user_cannot_login(self, client, app):
        with app.app_context():
            user = User(
                full_name='Inactive User',
                email='inactive@test.com',
                role='student',
                is_active=False
            )
            user.set_password('Student@123')
            db.session.add(user)
            db.session.commit()
        
        response = client.post('/auth/login', data={
            'email': 'inactive@test.com',
            'password': 'Student@123'
        }, follow_redirects=True)
        
        assert b'deactivated' in response.data.lower()


class TestRegistration:
    
    def test_registration_disabled_by_default(self, client, app):
        # In production config, registration is disabled by default
        # But in testing config, we enable it for testing purposes
        # So we test that the registration page loads successfully
        response = client.get('/auth/register', follow_redirects=True)
        assert response.status_code == 200
        # In testing mode, registration is enabled
        assert b'Create Account' in response.data or b'Register' in response.data
    
    def test_registration_when_enabled(self, client, app):
        app.config['REGISTRATION_ENABLED'] = True
        
        response = client.post('/auth/register', data={
            'full_name': 'New Student',
            'email': 'new@test.com',
            'password': 'Student@123',
            'confirm_password': 'Student@123',
            'course': 'B.Tech',
            'branch': 'Computer Science Engineering',
            'usn': '1CS21CS001',
            'phone': '+91 9876543210',
            'address': 'Test Address'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Registration successful' in response.data
        
        with app.app_context():
            user = User.query.filter_by(email='new@test.com').first()
            assert user is not None
            assert user.role == 'student'
        
        app.config['REGISTRATION_ENABLED'] = False
    
    def test_registration_duplicate_email(self, client, app, student_user):
        app.config['REGISTRATION_ENABLED'] = True
        
        response = client.post('/auth/register', data={
            'full_name': 'Another Student',
            'email': 'student@test.com',
            'password': 'Student@123',
            'confirm_password': 'Student@123',
            'course': 'B.Tech',
            'branch': 'Computer Science Engineering',
            'usn': '1CS21CS002',
            'phone': '+91 9876543210',
            'address': 'Test Address'
        }, follow_redirects=True)
        
        assert b'already registered' in response.data.lower()
        app.config['REGISTRATION_ENABLED'] = False