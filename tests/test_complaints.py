import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.extensions import db
from app.models import Complaint, StatusHistory, Feedback, ComplaintAttachment, User
from datetime import datetime


class TestComplaintWorkflow:
    
    def test_student_can_create_complaint(self, client, logged_in_student, student_user, app):
        response = client.post('/student/complaints/new', data={
            'title': 'Test Complaint Title',
            'description': 'This is a test complaint description with enough characters to be valid.',
            'category': 'IT Support',
            'priority': 'High',
            'location': 'Library',
            'is_anonymous': False
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Complaint submitted successfully' in response.data
        
        with app.app_context():
            complaint = Complaint.query.filter_by(student_id=student_user.id).first()
            assert complaint is not None
            assert complaint.title == 'Test Complaint Title'
            assert complaint.status == 'Submitted'
            assert complaint.ticket_number.startswith('CR-')
    
    def test_complaint_validation_required_fields(self, client, logged_in_student):
        response = client.post('/student/complaints/new', data={
            'title': 'Short',
            'description': 'Too short',
            'category': '',
            'priority': '',
            'location': '',
            'is_anonymous': False
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'This field is required' in response.data or b'minimum' in response.data.lower()
    
    def test_complaint_title_length_validation(self, client, logged_in_student):
        response = client.post('/student/complaints/new', data={
            'title': 'A' * 5,
            'description': 'This is a test complaint description with enough characters to be valid.',
            'category': 'IT Support',
            'priority': 'High'
        }, follow_redirects=True)
        
        assert b'10' in response.data or b'minimum' in response.data.lower()
    
    def test_complaint_starts_as_submitted(self, client, logged_in_student, student_user, app):
        client.post('/student/complaints/new', data={
            'title': 'Status Test Complaint',
            'description': 'Testing initial status of complaint submission process.',
            'category': 'IT Support',
            'priority': 'Medium'
        }, follow_redirects=True)
        
        with app.app_context():
            complaint = Complaint.query.filter_by(student_id=student_user.id).first()
            assert complaint.status == 'Submitted'
            
            history = StatusHistory.query.filter_by(complaint_id=complaint.id).first()
            assert history is not None
            assert history.new_status == 'Submitted'
            assert history.old_status is None
    
    def test_admin_can_assign_complaint(self, client, logged_in_admin, sample_complaint, app):
        with app.app_context():
            complaint = Complaint.query.get(sample_complaint.id)
            assert complaint.status == 'Submitted'
            
            # Create a staff user to assign to
            staff = User(
                full_name='Test Staff',
                email='staff@test.com',
                role='staff',
                department='IT Cell',
                is_active=True
            )
            staff.set_password('Staff@123')
            db.session.add(staff)
            db.session.commit()
            staff_id = staff.id
        
        response = client.post(f'/admin/complaints/{sample_complaint.ticket_number}/assign', data={
            'assigned_staff_id': str(staff_id),
            'due_date': '',
            'note': 'Assigned for review'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        with app.app_context():
            complaint = Complaint.query.get(sample_complaint.id)
            assert complaint.status == 'Assigned'
            assert complaint.assigned_staff_id == staff_id
    
    def test_staff_can_update_to_in_progress(self, client, logged_in_staff, staff_user, app):
        with app.app_context():
            complaint = Complaint(
                ticket_number='CR-2026-0002',
                student_id=2,
                title='Staff Test Complaint',
                description='Test complaint for staff status update workflow testing.',
                category='IT Support',
                priority='High',
                department='IT Cell',
                status='Assigned',
                assigned_staff_id=staff_user.id
            )
            db.session.add(complaint)
            db.session.commit()
            complaint_id = complaint.id
            ticket = complaint.ticket_number
        
        response = client.post(f'/staff/complaints/{ticket}/update', data={
            'status': 'In Progress',
            'note': 'Started working on the issue',
            'evidence': ''
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Status updated to In Progress' in response.data
        
        with app.app_context():
            complaint = Complaint.query.get(complaint_id)
            assert complaint.status == 'In Progress'
            
            history = StatusHistory.query.filter_by(complaint_id=complaint_id).order_by(StatusHistory.created_at.desc()).first()
            assert history.new_status == 'In Progress'
            assert history.old_status == 'Assigned'
    
    def test_staff_cannot_update_to_invalid_status(self, client, logged_in_staff, staff_user, app):
        with app.app_context():
            complaint = Complaint(
                ticket_number='CR-2026-0003',
                student_id=2,
                title='Invalid Status Test',
                description='Test complaint for invalid status transition testing.',
                category='IT Support',
                priority='High',
                department='IT Cell',
                status='Assigned',
                assigned_staff_id=staff_user.id
            )
            db.session.add(complaint)
            db.session.commit()
            ticket = complaint.ticket_number
        
        response = client.post(f'/staff/complaints/{ticket}/update', data={
            'status': 'Closed',
            'note': 'Trying to close directly',
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        with app.app_context():
            complaint = Complaint.query.filter_by(ticket_number=ticket).first()
            assert complaint.status != 'Closed'
    
    def test_status_history_created_on_change(self, client, logged_in_admin, sample_complaint, app):
        with app.app_context():
            complaint = Complaint.query.get(sample_complaint.id)
            initial_count = StatusHistory.query.filter_by(complaint_id=complaint.id).count()
        
        client.post(f'/admin/complaints/{sample_complaint.ticket_number}/update', data={
            'category': 'IT Support',
            'priority': 'High',
            'department': 'IT Cell',
            'assigned_staff_id': '0',
            'due_date': '',
            'status': 'Under Review',
            'is_duplicate': False,
            'parent_complaint_id': ''
        }, follow_redirects=True)
        
        with app.app_context():
            complaint = Complaint.query.get(sample_complaint.id)
            new_count = StatusHistory.query.filter_by(complaint_id=complaint.id).count()
            assert new_count == initial_count + 1
            
            latest = StatusHistory.query.filter_by(complaint_id=complaint.id).order_by(StatusHistory.created_at.desc()).first()
            assert latest.new_status == 'Under Review'
            assert latest.old_status == 'Submitted'
    
    def test_student_can_leave_feedback_after_resolved(self, client, logged_in_student, student_user, app):
        with app.app_context():
            complaint = Complaint(
                ticket_number='CR-2026-0004',
                student_id=student_user.id,
                title='Feedback Test Complaint',
                description='Test complaint for feedback functionality testing process.',
                category='IT Support',
                priority='Medium',
                department='IT Cell',
                status='Resolved'
            )
            db.session.add(complaint)
            db.session.commit()
            ticket = complaint.ticket_number
        
        response = client.post(f'/student/complaints/{ticket}/feedback', data={
            'rating': '5',
            'feedback_text': 'Excellent service!'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Thank you for your feedback' in response.data
        
        with app.app_context():
            feedback = Feedback.query.filter_by(complaint_id=complaint.id).first()
            assert feedback is not None
            assert feedback.rating == 5
            assert feedback.feedback_text == 'Excellent service!'
    
    def test_student_cannot_leave_feedback_before_resolved(self, client, logged_in_student, student_user, app):
        with app.app_context():
            complaint = Complaint(
                ticket_number='CR-2026-0005',
                student_id=student_user.id,
                title='Early Feedback Test',
                description='Test complaint for early feedback prevention testing.',
                category='IT Support',
                priority='Medium',
                department='IT Cell',
                status='In Progress'
            )
            db.session.add(complaint)
            db.session.commit()
            ticket = complaint.ticket_number
        
        response = client.post(f'/student/complaints/{ticket}/feedback', data={
            'rating': '4',
            'feedback_text': 'Good but not done yet'
        }, follow_redirects=True)
        
        assert b'only be submitted for resolved or closed' in response.data.lower()
        
        with app.app_context():
            feedback = Feedback.query.filter_by(complaint_id=complaint.id).first()
            assert feedback is None
    
    def test_duplicate_feedback_prevented(self, client, logged_in_student, student_user, app):
        with app.app_context():
            complaint = Complaint(
                ticket_number='CR-2026-0006',
                student_id=student_user.id,
                title='Duplicate Feedback Test',
                description='Test complaint for duplicate feedback prevention testing.',
                category='IT Support',
                priority='Medium',
                department='IT Cell',
                status='Resolved'
            )
            db.session.add(complaint)
            db.session.commit()
            
            feedback = Feedback(
                complaint_id=complaint.id,
                student_id=student_user.id,
                rating=4,
                feedback_text='First feedback'
            )
            db.session.add(feedback)
            db.session.commit()
            ticket = complaint.ticket_number
        
        response = client.post(f'/student/complaints/{ticket}/feedback', data={
            'rating': '5',
            'feedback_text': 'Second feedback'
        }, follow_redirects=True)
        
        assert b'already submitted' in response.data.lower()
        
        with app.app_context():
            feedbacks = Feedback.query.filter_by(complaint_id=complaint.id).all()
            assert len(feedbacks) == 1
    
    def test_ticket_number_generation(self, client, logged_in_student, student_user, app):
        for i in range(3):
            client.post('/student/complaints/new', data={
                'title': f'Ticket Test {i+1}',
                'description': f'Testing ticket number generation for complaint number {i+1} process.',
                'category': 'IT Support',
                'priority': 'Low'
            }, follow_redirects=True)
        
        with app.app_context():
            complaints = Complaint.query.filter_by(student_id=student_user.id).order_by(Complaint.created_at).all()
            assert len(complaints) == 3
            for i, c in enumerate(complaints):
                assert c.ticket_number == f'CR-2026-{i+1:04d}'


class TestComplaintAttachment:
    
    def test_attachment_upload_validation(self, client, logged_in_student, app):
        from io import BytesIO
        
        # Test invalid file type
        data = {
            'title': 'Attachment Test',
            'description': 'Testing attachment upload validation for file types.',
            'category': 'IT Support',
            'priority': 'Low',
            'attachment': (BytesIO(b'test'), 'test.exe')
        }
        response = client.post('/student/complaints/new', data=data, content_type='multipart/form-data', follow_redirects=True)
        
        # Should still create complaint but reject attachment
        assert response.status_code == 200
    
    def test_allowed_extensions(self, client, logged_in_student, app):
        from io import BytesIO
        
        for ext in ['pdf', 'png', 'jpg', 'jpeg']:
            data = {
                'title': f'Attachment Test {ext}',
                'description': f'Testing {ext} attachment upload validation process.',
                'category': 'IT Support',
                'priority': 'Low',
                'attachment': (BytesIO(b'test content'), f'test.{ext}')
            }
            response = client.post('/student/complaints/new', data=data, content_type='multipart/form-data', follow_redirects=True)
            assert response.status_code == 200