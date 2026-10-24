import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models import User, Complaint, ComplaintAttachment, StatusHistory, ComplaintComment, Notification, Feedback, AuditLog
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
            print("Creating demo users...")
            create_demo_users()
        
        print("Checking for existing complaints...")
        if Complaint.query.count() == 0:
            print("Creating demo complaints...")
            create_demo_complaints()
        
        print("Database initialization complete!")


def create_demo_users():
    demo = Config.DEMO_ACCOUNTS
    
    admin = User(
        full_name='Admin User',
        email=demo['admin']['email'],
        role='admin',
        is_active=True
    )
    admin.set_password(demo['admin']['password'])
    db.session.add(admin)
    
    staff_users = []
    for s in demo['staff']:
        user = User(
            full_name=f"{s['department'].split()[0]} Staff",
            email=s['email'],
            role='staff',
            department=s['department'],
            is_active=True
        )
        user.set_password(s['password'])
        db.session.add(user)
        staff_users.append(user)
    
    student_users = []
    for i, s in enumerate(demo['student'], 1):
        user = User(
            full_name=f'Student {i:02d}',
            email=s['email'],
            role='student',
            is_active=True
        )
        user.set_password(s['password'])
        db.session.add(user)
        student_users.append(user)
    
    db.session.commit()
    print(f"Created 1 admin, {len(staff_users)} staff, {len(student_users)} students")


def create_demo_complaints():
    admin = User.query.filter_by(role='admin').first()
    students = User.query.filter_by(role='student').all()
    staff_by_dept = {s.department: s for s in User.query.filter_by(role='staff').all()}
    
    complaint_data = [
        {
            'title': 'Water supply issue in Hostel Block A',
            'description': 'There is no water supply in Hostel Block A since morning. Students are facing difficulties with basic needs like bathing, drinking water, and washroom usage. Please address this urgently.',
            'category': 'Hostel',
            'priority': 'High',
            'location': 'Hostel Block A',
            'student': students[0],
            'status': 'Resolved',
            'assigned_staff': staff_by_dept.get('Hostel Office'),
            'days_ago': 10,
            'resolved': True,
            'feedback_rating': 4,
            'feedback_text': 'Issue resolved quickly. Water supply restored within 4 hours.'
        },
        {
            'title': 'Wi-Fi outage in Library and IT Block',
            'description': 'Wi-Fi has been down in the Library and IT Block for the past 2 days. Students cannot access online resources, submit assignments, or attend online classes. This is affecting academic work significantly.',
            'category': 'IT Support',
            'priority': 'Critical',
            'location': 'Library, IT Block',
            'student': students[1],
            'status': 'In Progress',
            'assigned_staff': staff_by_dept.get('IT Cell'),
            'days_ago': 3,
            'resolved': False
        },
        {
            'title': 'Library book not available - "Data Structures and Algorithms"',
            'description': 'The book "Data Structures and Algorithms" by Cormen is showing as available in the catalog but is not on the shelves. Multiple students have reported this issue. Please check if it is misplaced or lost.',
            'category': 'Library',
            'priority': 'Medium',
            'location': 'Central Library',
            'student': students[2],
            'status': 'Assigned',
            'assigned_staff': staff_by_dept.get('Library'),
            'days_ago': 5,
            'resolved': False
        },
        {
            'title': 'Bus route 12 delayed by 30 minutes daily',
            'description': 'Bus route 12 (Campus to City Center) is consistently delayed by 30 minutes every morning. This causes students to miss their first period classes. The schedule needs to be adjusted or additional buses allocated.',
            'category': 'Transport',
            'priority': 'High',
            'location': 'Bus Route 12',
            'student': students[0],
            'status': 'Under Review',
            'assigned_staff': staff_by_dept.get('Transport Office'),
            'days_ago': 7,
            'resolved': False
        },
        {
            'title': 'Semester results not published on portal',
            'description': 'The semester 4 results for Computer Science department were supposed to be published last week but are still not available on the student portal. Students need these results for internship applications and further studies.',
            'category': 'Examination',
            'priority': 'High',
            'location': 'Examination Cell',
            'student': students[1],
            'status': 'Submitted',
            'days_ago': 2,
            'resolved': False
        },
        {
            'title': 'Fee receipt not generated after online payment',
            'description': 'I paid the semester fees online through the portal on 15th January. Payment was successful and money was deducted from my account, but no fee receipt was generated. I have the transaction ID but need the official receipt for records.',
            'category': 'Fees and Accounts',
            'priority': 'Medium',
            'location': 'Accounts Section',
            'student': students[2],
            'status': 'Resolved',
            'assigned_staff': staff_by_dept.get('Accounts Section'),
            'days_ago': 14,
            'resolved': True,
            'feedback_rating': 5,
            'feedback_text': 'Receipt generated within 2 hours. Excellent service!'
        },
    ]
    
    for i, data in enumerate(complaint_data):
        created_at = datetime.utcnow() - timedelta(days=data['days_ago'])
        due_date = None
        
        student = data['student']
        assigned_staff = data.get('assigned_staff')
        
        try:
            from app.ai.ai_utils import get_ai_suggestions
            ai_result = get_ai_suggestions(data['title'], data['description'])
        except:
            ai_result = {'category': data['category'], 'priority': data['priority'], 'department': data.get('department'), 'estimated_duration_days': 5}
        
        complaint = Complaint(
            ticket_number=f"CR-2026-{i+1:04d}",
            student_id=student.id,
            title=data['title'],
            description=data['description'],
            category=data['category'],
            priority=data['priority'],
            location=data['location'],
            is_anonymous=data.get('is_anonymous', False),
            status=data['status'],
            assigned_staff_id=assigned_staff.id if assigned_staff else None,
            department=assigned_staff.department if assigned_staff else Config.CATEGORY_DEPARTMENT_MAP.get(data['category']),
            due_date=due_date,
            created_at=created_at,
            updated_at=created_at,
            ml_predicted_category=ai_result.get('category'),
            ml_category_confidence=ai_result.get('category_confidence', 0) / 100 if ai_result.get('category_confidence') else None,
            ml_predicted_priority=ai_result.get('priority'),
            ml_priority_confidence=ai_result.get('priority_confidence', 0) / 100 if ai_result.get('priority_confidence') else None,
            ml_suggested_department=ai_result.get('department'),
            ml_predicted_duration=ai_result.get('estimated_duration_days'),
        )
        
        if data.get('resolved'):
            complaint.resolved_at = created_at + timedelta(days=2)
            complaint.resolution_time_days = 2.0
            if data['status'] == 'Closed':
                complaint.closed_at = complaint.resolved_at + timedelta(days=1)
        
        db.session.add(complaint)
        db.session.flush()
        
        history = StatusHistory(
            complaint_id=complaint.id,
            actor_id=admin.id if assigned_staff else student.id,
            old_status=None,
            new_status='Submitted',
            note='Complaint submitted'
        )
        db.session.add(history)
        
        if data['status'] != 'Submitted':
            statuses = ['Submitted', 'Under Review', 'Assigned', 'In Progress', 'Pending Student Response', 'Resolved', 'Closed']
            current_idx = statuses.index('Submitted')
            target_idx = statuses.index(data['status'])
            
            for idx in range(current_idx + 1, target_idx + 1):
                status = statuses[idx]
                actor = assigned_staff if idx >= 2 else admin
                history = StatusHistory(
                    complaint_id=complaint.id,
                    actor_id=actor.id if actor else admin.id,
                    old_status=statuses[idx - 1],
                    new_status=status,
                    note=f'Status updated to {status}'
                )
                db.session.add(history)
        
        if data.get('resolved') and data.get('feedback_rating'):
            feedback = Feedback(
                complaint_id=complaint.id,
                student_id=student.id,
                rating=data['feedback_rating'],
                feedback_text=data.get('feedback_text', ''),
                created_at=complaint.resolved_at + timedelta(hours=1)
            )
            db.session.add(feedback)
        
        log_audit(admin.id if assigned_staff else student.id, 'create', 'complaint', complaint.id, f'Created complaint {complaint.ticket_number}')
        
        create_notification(student.id, 'Complaint Submitted', f'Your complaint {complaint.ticket_number} has been submitted.', complaint.id)
        if assigned_staff:
            create_notification(assigned_staff.id, 'New Complaint Assigned', f'Complaint {complaint.ticket_number} assigned to you.', complaint.id)
    
    db.session.commit()
    print(f"Created {len(complaint_data)} demo complaints")


def log_audit(actor_id, action, entity_type, entity_id, details=None):
    log = AuditLog(actor_id=actor_id, action=action, entity_type=entity_type, entity_id=entity_id, details=details)
    db.session.add(log)


def create_notification(recipient_id, title, message, complaint_id=None):
    notif = Notification(recipient_id=recipient_id, title=title, message=message, complaint_id=complaint_id)
    db.session.add(notif)


if __name__ == '__main__':
    from datetime import timedelta
    init_database()