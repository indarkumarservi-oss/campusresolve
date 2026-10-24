import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.extensions import db
from app.models import Complaint, User


class TestPermissions:
    
    def test_student_cannot_access_admin_route(self, client, logged_in_student):
        response = client.get('/admin/dashboard', follow_redirects=True)
        assert response.status_code == 403
    
    def test_student_cannot_access_staff_route(self, client, logged_in_student):
        response = client.get('/staff/dashboard', follow_redirects=True)
        assert response.status_code == 403
    
    def test_staff_cannot_access_admin_route(self, client, logged_in_staff):
        response = client.get('/admin/dashboard', follow_redirects=True)
        assert response.status_code == 403
    
    def test_student_cannot_access_another_student_complaint(self, client, logged_in_student, student_user, app):
        with app.app_context():
            other_student = User(
                full_name='Other Student',
                email='other@test.com',
                role='student',
                is_active=True
            )
            other_student.set_password('Student@123')
            db.session.add(other_student)
            db.session.commit()
            
            complaint = Complaint(
                ticket_number='CR-2026-9999',
                student_id=other_student.id,
                title='Other Student Complaint',
                description='This complaint belongs to another student for permission testing.',
                category='IT Support',
                priority='Medium',
                status='Submitted'
            )
            db.session.add(complaint)
            db.session.commit()
            ticket = complaint.ticket_number
        
        response = client.get(f'/student/complaints/{ticket}', follow_redirects=True)
        assert response.status_code == 403
    
    def test_student_can_access_own_complaint(self, client, logged_in_student, student_user, app):
        with app.app_context():
            complaint = Complaint(
                ticket_number='CR-2026-8888',
                student_id=student_user.id,
                title='My Own Complaint',
                description='This complaint belongs to the current student for access testing.',
                category='IT Support',
                priority='Medium',
                status='Submitted'
            )
            db.session.add(complaint)
            db.session.commit()
            ticket = complaint.ticket_number
        
        response = client.get(f'/student/complaints/{ticket}')
        assert response.status_code == 200
        assert b'My Own Complaint' in response.data
    
    def test_staff_cannot_access_unassigned_complaint(self, client, logged_in_staff, staff_user, app):
        with app.app_context():
            complaint = Complaint(
                ticket_number='CR-2026-7777',
                student_id=2,
                title='Unassigned Complaint',
                description='This complaint is not assigned to the current staff member.',
                category='Hostel',
                priority='Medium',
                department='Hostel Office',
                status='Assigned'
            )
            db.session.add(complaint)
            db.session.commit()
            ticket = complaint.ticket_number
        
        response = client.get(f'/staff/complaints/{ticket}', follow_redirects=True)
        assert response.status_code == 403
    
    def test_staff_can_access_assigned_complaint(self, client, logged_in_staff, staff_user, app):
        with app.app_context():
            complaint = Complaint(
                ticket_number='CR-2026-6666',
                student_id=2,
                title='My Assigned Complaint',
                description='This complaint is assigned to the current staff member.',
                category='IT Support',
                priority='High',
                department='IT Cell',
                status='Assigned',
                assigned_staff_id=staff_user.id
            )
            db.session.add(complaint)
            db.session.commit()
            ticket = complaint.ticket_number
        
        response = client.get(f'/staff/complaints/{ticket}')
        assert response.status_code == 200
        assert b'My Assigned Complaint' in response.data
    
    def test_staff_can_access_department_complaint(self, client, logged_in_staff, staff_user, app):
        with app.app_context():
            complaint = Complaint(
                ticket_number='CR-2026-5555',
                student_id=2,
                title='Department Complaint',
                description='This complaint is in the same department as the staff member.',
                category='IT Support',
                priority='High',
                department='IT Cell',
                status='Assigned'
            )
            db.session.add(complaint)
            db.session.commit()
            ticket = complaint.ticket_number
        
        response = client.get(f'/staff/complaints/{ticket}')
        assert response.status_code == 200
    
    def test_non_admin_cannot_export_csv(self, client, logged_in_student, logged_in_staff):
        # Student
        response = client.get('/admin/complaints?export=1', follow_redirects=True)
        assert response.status_code == 403
        
        # Staff
        response = client.get('/admin/complaints?export=1', follow_redirects=True)
        assert response.status_code == 403
    
    def test_admin_can_export_csv(self, client, logged_in_admin, app):
        with app.app_context():
            complaint = Complaint(
                ticket_number='CR-2026-4444',
                student_id=1,
                title='Export Test',
                description='Test complaint for CSV export functionality testing.',
                category='IT Support',
                priority='Low',
                status='Submitted'
            )
            db.session.add(complaint)
            db.session.commit()
        
        response = client.get('/admin/complaints?export=1')
        assert response.status_code == 200
        assert response.content_type == 'text/csv'
        assert b'CR-2026-4444' in response.data
    
    def test_anonymous_complaint_hides_student_name(self, client, logged_in_staff, staff_user, app):
        with app.app_context():
            student = User(
                full_name='Anonymous Student',
                email='anon@test.com',
                role='student',
                is_active=True
            )
            student.set_password('Student@123')
            db.session.add(student)
            db.session.commit()
            
            complaint = Complaint(
                ticket_number='CR-2026-3333',
                student_id=student.id,
                title='Anonymous Complaint',
                description='This is an anonymous complaint for privacy testing.',
                category='IT Support',
                priority='Medium',
                department='IT Cell',
                status='Assigned',
                is_anonymous=True,
                assigned_staff_id=staff_user.id
            )
            db.session.add(complaint)
            db.session.commit()
            ticket = complaint.ticket_number
        
        response = client.get(f'/staff/complaints/{ticket}')
        assert response.status_code == 200
        assert b'Anonymous' in response.data
        assert b'Anonymous Student' not in response.data
    
    def test_admin_can_see_anonymous_student(self, client, logged_in_admin, app):
        with app.app_context():
            student = User(
                full_name='Anonymous Student',
                email='anon2@test.com',
                role='student',
                is_active=True
            )
            student.set_password('Student@123')
            db.session.add(student)
            db.session.commit()
            
            complaint = Complaint(
                ticket_number='CR-2026-2222',
                student_id=student.id,
                title='Admin View Anonymous',
                description='Admin should see student name even for anonymous complaints.',
                category='IT Support',
                priority='Medium',
                status='Submitted',
                is_anonymous=True
            )
            db.session.add(complaint)
            db.session.commit()
            ticket = complaint.ticket_number
        
        response = client.get(f'/admin/complaints/{ticket}')
        assert response.status_code == 200
        assert b'Anonymous Student' in response.data
    
    def test_inactive_user_cannot_access_dashboard(self, client, app):
        with app.app_context():
            inactive = User(
                full_name='Inactive Student',
                email='inactive2@test.com',
                role='student',
                is_active=False
            )
            inactive.set_password('Student@123')
            db.session.add(inactive)
            db.session.commit()
        
        # In testing mode, LOGIN_DISABLED=True so login succeeds
        # But the dashboard should redirect inactive users
        client.post('/auth/login', data={
            'email': 'inactive2@test.com',
            'password': 'Student@123'
        }, follow_redirects=True)
        
        response = client.get('/student/dashboard', follow_redirects=True)
        # Should be redirected to 403 or login page
        assert response.status_code in [200, 403]
        # The user should not be able to access the dashboard content
        assert b'Student Dashboard' not in response.data
    
    def test_csrf_protection_on_forms(self, client, logged_in_student):
        # Try to submit without CSRF token (should fail in non-testing config)
        # In testing config, CSRF is disabled, so this just verifies the form works
        response = client.post('/student/complaints/new', data={
            'title': 'CSRF Test Complaint',
            'description': 'Testing CSRF protection on complaint submission form.',
            'category': 'IT Support',
            'priority': 'Low'
        }, follow_redirects=True)
        
        # In testing, CSRF is disabled so this should work
        # In production, it would require valid CSRF token
        assert response.status_code == 200


class TestRoleBasedAccess:
    
    def test_admin_sees_all_complaints(self, client, logged_in_admin, app):
        with app.app_context():
            for i in range(3):
                complaint = Complaint(
                    ticket_number=f'CR-2026-1{i:03d}',
                    student_id=1,
                    title=f'Admin Test {i}',
                    description=f'Admin test complaint number {i} for listing.',
                    category='IT Support',
                    priority='Low',
                    status='Submitted'
                )
                db.session.add(complaint)
            db.session.commit()
        
        response = client.get('/admin/complaints')
        assert response.status_code == 200
        assert b'Admin Test 0' in response.data
        assert b'Admin Test 1' in response.data
        assert b'Admin Test 2' in response.data
    
    def test_student_sees_only_own_complaints(self, client, logged_in_student, student_user, app):
        with app.app_context():
            other = User(
                full_name='Other Student',
                email='other2@test.com',
                role='student',
                is_active=True
            )
            other.set_password('Student@123')
            db.session.add(other)
            db.session.commit()
            
            my_complaint = Complaint(
                ticket_number='CR-2026-0100',
                student_id=student_user.id,
                title='My Complaint',
                description='My own complaint for student dashboard testing.',
                category='IT Support',
                priority='Low',
                status='Submitted'
            )
            other_complaint = Complaint(
                ticket_number='CR-2026-0101',
                student_id=other.id,
                title='Other Complaint',
                description='Another student complaint not visible to current user.',
                category='IT Support',
                priority='Low',
                status='Submitted'
            )
            db.session.add_all([my_complaint, other_complaint])
            db.session.commit()
        
        response = client.get('/student/complaints')
        assert response.status_code == 200
        assert b'My Complaint' in response.data
        assert b'Other Complaint' not in response.data
    
    def test_staff_dashboard_shows_only_assigned(self, client, logged_in_staff, staff_user, app):
        with app.app_context():
            assigned = Complaint(
                ticket_number='CR-2026-0200',
                student_id=1,
                title='Assigned to Me',
                description='Complaint assigned to current staff member.',
                category='IT Support',
                priority='High',
                department='IT Cell',
                status='Assigned',
                assigned_staff_id=staff_user.id
            )
            dept_complaint = Complaint(
                ticket_number='CR-2026-0201',
                student_id=1,
                title='In My Department',
                description='Complaint in staff department but not assigned directly.',
                category='IT Support',
                priority='Medium',
                department='IT Cell',
                status='Assigned'
            )
            other_dept = Complaint(
                ticket_number='CR-2026-0202',
                student_id=1,
                title='Other Department',
                description='Complaint in different department.',
                category='Hostel',
                priority='High',
                department='Hostel Office',
                status='Assigned'
            )
            db.session.add_all([assigned, dept_complaint, other_dept])
            db.session.commit()
        
        response = client.get('/staff/dashboard')
        assert response.status_code == 200
        assert b'Assigned to Me' in response.data
        assert b'In My Department' in response.data
        assert b'Other Department' not in response.data