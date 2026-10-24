import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'campusresolve-dev-secret-key-change-in-production')
    database_url = os.environ.get('DATABASE_URL', 'sqlite:///campusresolve.db')
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None
    
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'uploads')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
    
    LOGIN_DISABLED = False
    REMEMBER_COOKIE_DURATION = timedelta(days=7)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = False
    
    REGISTRATION_ENABLED = True
    
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
    
    COURSES = [
        'B.Tech', 'M.Tech', 'B.E', 'M.E', 'B.Sc', 'M.Sc', 
        'BCA', 'MCA', 'BBA', 'MBA', 'B.Com', 'M.Com',
        'BA', 'MA', 'PhD', 'Diploma', 'Other'
    ]
    
    BRANCHES = [
        'Computer Science Engineering', 'Information Technology', 
        'Electronics & Communication', 'Electrical & Electronics',
        'Mechanical Engineering', 'Civil Engineering',
        'Chemical Engineering', 'Biotechnology',
        'Artificial Intelligence & ML', 'Data Science',
        'Cyber Security', 'Computer Science & Business Systems',
        'Other'
    ]
    
    COMPLAINT_CATEGORIES = [
        'Academics', 'Examination', 'Fees and Accounts', 'Hostel', 'Transport',
        'Library', 'IT Support', 'Campus Facilities', 'Placement', 'Student Wellbeing', 'Other'
    ]
    
    COMPLAINT_PRIORITIES = ['Low', 'Medium', 'High', 'Critical']
    
    COMPLAINT_STATUSES = [
        'Submitted', 'Under Review', 'Assigned', 'In Progress',
        'Pending Student Response', 'Resolved', 'Closed'
    ]
    
    DEPARTMENTS = [
        'Academic Department / HOD', 'Examination Cell', 'Accounts Section',
        'Hostel Office', 'Transport Office', 'Library', 'IT Cell',
        'Maintenance Department', 'Placement Cell', 'Student Support Cell', 'Administration'
    ]
    
    CATEGORY_DEPARTMENT_MAP = {
        'Academics': 'Academic Department / HOD',
        'Examination': 'Examination Cell',
        'Fees and Accounts': 'Accounts Section',
        'Hostel': 'Hostel Office',
        'Transport': 'Transport Office',
        'Library': 'Library',
        'IT Support': 'IT Cell',
        'Campus Facilities': 'Maintenance Department',
        'Placement': 'Placement Cell',
        'Student Wellbeing': 'Student Support Cell',
        'Other': 'Administration'
    }
    
    AI_CONFIDENCE_THRESHOLD = 0.3
    
    PAGINATION_PER_PAGE = 15
    
    # SLA Configuration (target resolution days by priority)
    SLA_TARGET_DAYS = {
        'Critical': 1,
        'High': 2,
        'Medium': 5,
        'Low': 7,
    }
    
    DEMO_ACCOUNTS = {
        'admin': {'email': 'admin@campusresolve.demo', 'password': 'Admin@123', 'role': 'admin'},
    }


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = False


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    LOGIN_DISABLED = True
    REGISTRATION_ENABLED = True


class ProductionConfig(Config):
    DEBUG = False
    REMEMBER_COOKIE_SECURE = True


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}