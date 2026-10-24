from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=True)
    role = db.Column(db.String(20), nullable=False, default='student')
    department = db.Column(db.String(100), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_approved = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    google_id = db.Column(db.String(100), unique=True, nullable=True, index=True)
    course = db.Column(db.String(100), nullable=True)
    branch = db.Column(db.String(100), nullable=True)
    usn = db.Column(db.String(50), unique=True, nullable=True, index=True)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)
    profile_completed = db.Column(db.Boolean, default=False, nullable=False)
    
    complaints = db.relationship('Complaint', backref='student', foreign_keys='Complaint.student_id', lazy='dynamic')
    assigned_complaints = db.relationship('Complaint', backref='assigned_staff', foreign_keys='Complaint.assigned_staff_id', lazy='dynamic')
    status_history = db.relationship('StatusHistory', backref='actor', lazy='dynamic')
    comments = db.relationship('ComplaintComment', backref='author', lazy='dynamic')
    notifications = db.relationship('Notification', backref='recipient', lazy='dynamic')
    feedback = db.relationship('Feedback', backref='student', lazy='dynamic')
    audit_logs = db.relationship('AuditLog', backref='actor', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_staff(self):
        return self.role == 'staff'
    
    def is_student(self):
        return self.role == 'student'
    
    def __repr__(self):
        return f'<User {self.email} ({self.role})>'


class Complaint(db.Model):
    __tablename__ = 'complaints'
    
    id = db.Column(db.Integer, primary_key=True)
    ticket_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=True)
    priority = db.Column(db.String(20), nullable=True)
    department = db.Column(db.String(100), nullable=True)
    location = db.Column(db.String(200), nullable=True)
    is_anonymous = db.Column(db.Boolean, default=False, nullable=False)
    status = db.Column(db.String(30), default='Submitted', nullable=False, index=True)
    assigned_staff_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    due_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    resolved_at = db.Column(db.DateTime, nullable=True)
    closed_at = db.Column(db.DateTime, nullable=True)
    resolution_time_days = db.Column(db.Float, nullable=True)
    
    ml_predicted_category = db.Column(db.String(50), nullable=True)
    ml_category_confidence = db.Column(db.Float, nullable=True)
    ml_predicted_priority = db.Column(db.String(20), nullable=True)
    ml_priority_confidence = db.Column(db.Float, nullable=True)
    ml_suggested_department = db.Column(db.String(100), nullable=True)
    ml_predicted_duration = db.Column(db.Integer, nullable=True)
    
    # AI Verification fields
    ai_verification_token = db.Column(db.String(256), nullable=True)
    ai_verification_expires = db.Column(db.DateTime, nullable=True)
    ai_verified_category = db.Column(db.String(50), nullable=True)
    ai_verified_priority = db.Column(db.String(20), nullable=True)
    ai_verified_duration = db.Column(db.Integer, nullable=True)
    ai_verified_at = db.Column(db.DateTime, nullable=True)
    
    is_duplicate = db.Column(db.Boolean, default=False, nullable=False)
    parent_complaint_id = db.Column(db.Integer, db.ForeignKey('complaints.id'), nullable=True)
    parent_complaint = db.relationship('Complaint', remote_side=[id], backref='duplicate_complaints')
    
    attachments = db.relationship('ComplaintAttachment', backref='complaint', lazy='dynamic', cascade='all, delete-orphan')
    status_history = db.relationship('StatusHistory', backref='complaint', lazy='dynamic', cascade='all, delete-orphan')
    comments = db.relationship('ComplaintComment', backref='complaint', lazy='dynamic', cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='complaint', lazy='dynamic')
    feedback = db.relationship('Feedback', backref='complaint', uselist=False, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Complaint {self.ticket_number}: {self.title}>'


class ComplaintAttachment(db.Model):
    __tablename__ = 'complaint_attachments'
    
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey('complaints.id'), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    content_type = db.Column(db.String(100), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<Attachment {self.original_filename}>'


class StatusHistory(db.Model):
    __tablename__ = 'status_history'
    
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey('complaints.id'), nullable=False)
    actor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    old_status = db.Column(db.String(30), nullable=True)
    new_status = db.Column(db.String(30), nullable=False)
    note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<StatusHistory {self.old_status} -> {self.new_status}>'


class ComplaintComment(db.Model):
    __tablename__ = 'complaint_comments'
    
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey('complaints.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    comment_text = db.Column(db.Text, nullable=False)
    is_internal_note = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<Comment by {self.author_id} on {self.complaint_id}>'


class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    complaint_id = db.Column(db.Integer, db.ForeignKey('complaints.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<Notification {self.title}>'


class Feedback(db.Model):
    __tablename__ = 'feedback'
    
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey('complaints.id'), unique=True, nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    feedback_text = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<Feedback {self.rating}/5 for {self.complaint_id}>'


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.Integer, nullable=False)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<AuditLog {self.action} on {self.entity_type} {self.entity_id}>'