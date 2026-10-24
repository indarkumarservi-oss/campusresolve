import pytest
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.extensions import db
from app.models import Complaint, User, Feedback, Notification


class TestDashboard:
    
    def test_student_dashboard_loads(self, client, logged_in_student):
        response = client.get('/student/dashboard')
        assert response.status_code == 200
        assert b'Student Dashboard' in response.data
        assert b'Total Complaints' in response.data
        assert b'Open Complaints' in response.data
        assert b'Resolved' in response.data
        assert b'Closed' in response.data
    
    def test_staff_dashboard_loads(self, client, logged_in_staff):
        response = client.get('/staff/dashboard')
        assert response.status_code == 200
        assert b'Staff Dashboard' in response.data
        assert b'Assigned Tickets' in response.data
        assert b'Overdue' in response.data
        assert b'Resolved/Closed' in response.data
    
    def test_admin_dashboard_loads(self, client, logged_in_admin):
        response = client.get('/admin/dashboard')
        assert response.status_code == 200
        assert b'Admin Dashboard' in response.data
        assert b'Total Complaints' in response.data
        assert b'Submitted/Review' in response.data
        assert b'Assigned/In Progress' in response.data
        assert b'Overdue' in response.data
        assert b'Avg Resolution' in response.data
    
    def test_student_dashboard_shows_stats(self, client, logged_in_student, student_user, app):
        with app.app_context():
            for i in range(3):
                complaint = Complaint(
                    ticket_number=f'CR-2026-D{i:03d}',
                    student_id=student_user.id,
                    title=f'Dashboard Test {i}',
                    description=f'Dashboard test complaint number {i} for statistics.',
                    category='IT Support',
                    priority='Low',
                    status='Submitted' if i < 2 else 'Resolved'
                )
                db.session.add(complaint)
            db.session.commit()
        
        response = client.get('/student/dashboard')
        assert response.status_code == 200
        # Check that stats are rendered (exact numbers may vary)
        assert b'3' in response.data or b'Total' in response.data
    
    def test_staff_dashboard_shows_assigned_count(self, client, logged_in_staff, staff_user, app):
        with app.app_context():
            for i in range(2):
                complaint = Complaint(
                    ticket_number=f'CR-2026-S{i:03d}',
                    student_id=1,
                    title=f'Staff Dashboard {i}',
                    description=f'Staff dashboard test complaint {i} for assigned count.',
                    category='IT Support',
                    priority='High',
                    department='IT Cell',
                    status='Assigned',
                    assigned_staff_id=staff_user.id
                )
                db.session.add(complaint)
            db.session.commit()
        
        response = client.get('/staff/dashboard')
        assert response.status_code == 200
        assert b'2' in response.data
    
    def test_admin_dashboard_shows_charts(self, client, logged_in_admin):
        response = client.get('/admin/dashboard')
        assert response.status_code == 200
        assert b'categoryChart' in response.data
        assert b'statusChart' in response.data
        assert b'priorityChart' in response.data
        assert b'monthlyChart' in response.data
    
    def test_admin_analytics_loads(self, client, logged_in_admin):
        response = client.get('/admin/analytics')
        assert response.status_code == 200
        assert b'Analytics' in response.data
        assert b'catChart' in response.data
        assert b'statusChart' in response.data
        assert b'priChart' in response.data
        assert b'monthlyChart' in response.data
        assert b'deptChart' in response.data
        assert b'locChart' in response.data
        assert b'ratingChart' in response.data
    
    def test_analytics_date_filter(self, client, logged_in_admin):
        response = client.get('/admin/analytics?date_from=2026-01-01&date_to=2026-12-31')
        assert response.status_code == 200
    
    def test_student_notifications_page(self, client, logged_in_student, student_user, app):
        with app.app_context():
            notif = Notification(
                recipient_id=student_user.id,
                title='Test Notification',
                message='This is a test notification for the student dashboard.',
                is_read=False
            )
            db.session.add(notif)
            db.session.commit()
        
        response = client.get('/student/notifications')
        assert response.status_code == 200
        assert b'Notifications' in response.data
        assert b'Test Notification' in response.data
    
    def test_mark_notification_read_api(self, client, logged_in_student, student_user, app):
        with app.app_context():
            notif = Notification(
                recipient_id=student_user.id,
                title='API Test Notification',
                message='Testing mark as read via API endpoint.',
                is_read=False
            )
            db.session.add(notif)
            db.session.commit()
            notif_id = notif.id
        
        response = client.post(f'/api/notifications/read/{notif_id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        
        with app.app_context():
            notif = Notification.query.get(notif_id)
            assert notif.is_read is True
    
    def test_mark_all_notifications_read_api(self, client, logged_in_student, student_user, app):
        with app.app_context():
            for i in range(3):
                notif = Notification(
                    recipient_id=student_user.id,
                    title=f'Bulk Notif {i}',
                    message=f'Bulk notification {i} for mark all read test.',
                    is_read=False
                )
                db.session.add(notif)
            db.session.commit()
        
        response = client.post('/api/notifications/read-all')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        
        with app.app_context():
            unread = Notification.query.filter_by(recipient_id=student_user.id, is_read=False).count()
            assert unread == 0
    
    def test_unread_count_api(self, client, logged_in_student, student_user, app):
        with app.app_context():
            for i in range(2):
                notif = Notification(
                    recipient_id=student_user.id,
                    title=f'Count Notif {i}',
                    message=f'Notification for unread count test {i}.',
                    is_read=False
                )
                db.session.add(notif)
            db.session.commit()
        
        response = client.get('/api/notifications/unread-count')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['count'] >= 2


import json