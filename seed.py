import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models import User, Complaint, ComplaintAttachment, StatusHistory, ComplaintComment, Notification, Feedback, AuditLog
from config import Config
from app.ai.ai_utils import get_ai_suggestions, load_models


def seed_database():
    app = create_app('development')
    
    with app.app_context():
        print("Dropping all tables...")
        db.drop_all()
        print("Creating all tables...")
        db.create_all()
        
        print("Loading AI models...")
        load_models()
        
        print("Creating demo users...")
        create_demo_users()
        
        print("Creating demo complaints...")
        create_demo_complaints()
        
        print("Seeding complete!")


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
        {
            'title': 'Projector not working in Classroom 302',
            'description': 'The projector in Classroom 302 (Engineering Block) has been malfunctioning for a week. It shows distorted colors and frequently disconnects. This affects all classes scheduled in this room.',
            'category': 'Campus Facilities',
            'priority': 'Medium',
            'location': 'Engineering Block, Classroom 302',
            'student': students[0],
            'status': 'In Progress',
            'assigned_staff': staff_by_dept.get('Maintenance Department'),
            'days_ago': 4,
            'resolved': False
        },
        {
            'title': 'Placement portal login issues',
            'description': 'Unable to login to the placement portal using valid credentials. The system shows "Invalid credentials" error even with correct username and password. This is preventing students from applying to job postings.',
            'category': 'Placement',
            'priority': 'High',
            'location': 'Placement Cell',
            'student': students[1],
            'status': 'Pending Student Response',
            'assigned_staff': staff_by_dept.get('Placement Cell'),
            'days_ago': 6,
            'resolved': False
        },
        {
            'title': 'Water supply issue in Hostel Block A - duplicate',
            'description': 'There is no water supply in Hostel Block A since morning. Students are facing difficulties with basic needs like bathing, drinking water, and washroom usage. Please address this urgently.',
            'category': 'Hostel',
            'priority': 'High',
            'location': 'Hostel Block A',
            'student': students[2],
            'status': 'Closed',
            'assigned_staff': staff_by_dept.get('Hostel Office'),
            'days_ago': 9,
            'resolved': True,
            'is_duplicate': True,
            'parent_ticket': 1,
            'feedback_rating': 3,
            'feedback_text': 'Marked as duplicate. Original complaint already resolved.'
        },
        {
            'title': 'AC not working in Computer Lab 2',
            'description': 'The air conditioning in Computer Lab 2 (IT Block) is not working. The room temperature is very high making it uncomfortable for practical sessions. Multiple students have complained about this.',
            'category': 'Campus Facilities',
            'priority': 'Medium',
            'location': 'IT Block, Computer Lab 2',
            'student': students[0],
            'status': 'Resolved',
            'assigned_staff': staff_by_dept.get('Maintenance Department'),
            'days_ago': 12,
            'resolved': True,
            'feedback_rating': 4,
            'feedback_text': 'AC repaired. Temperature is now comfortable.'
        },
        {
            'title': 'Mess food quality issue',
            'description': 'The food quality in the hostel mess has deteriorated significantly over the past month. Food is often cold, stale, or undercooked. Students are falling sick frequently. Please investigate the kitchen and supplier.',
            'category': 'Hostel',
            'priority': 'High',
            'location': 'Hostel Mess',
            'student': students[1],
            'status': 'In Progress',
            'assigned_staff': staff_by_dept.get('Hostel Office'),
            'days_ago': 8,
            'resolved': False
        },
        {
            'title': 'Scholarship application portal error',
            'description': 'When trying to submit the scholarship application, the portal throws a 500 Internal Server Error after clicking submit. This has been happening for 3 days. Deadline is approaching.',
            'category': 'IT Support',
            'priority': 'Critical',
            'location': 'Online Portal',
            'student': students[2],
            'status': 'Assigned',
            'assigned_staff': staff_by_dept.get('IT Cell'),
            'days_ago': 1,
            'resolved': False
        },
        {
            'title': 'Exam hall seating arrangement issue',
            'description': 'The seating arrangement for the upcoming mid-term exams has not been published. Students do not know their exam halls and seat numbers. This causes confusion on exam day.',
            'category': 'Examination',
            'priority': 'Medium',
            'location': 'Examination Cell',
            'student': students[0],
            'status': 'Submitted',
            'days_ago': 1,
            'resolved': False
        },
        {
            'title': 'Hostel room maintenance - leaking ceiling',
            'description': 'Ceiling in Room 204, Hostel Block B is leaking during rain. Water drips on the bed and study table. This has been reported twice before but not fixed properly. Mold is starting to form.',
            'category': 'Hostel',
            'priority': 'High',
            'location': 'Hostel Block B, Room 204',
            'student': students[1],
            'status': 'Under Review',
            'assigned_staff': staff_by_dept.get('Hostel Office'),
            'days_ago': 15,
            'resolved': False
        },
        {
            'title': 'Library fine incorrectly charged',
            'description': 'I returned the book "Operating System Concepts" on 10th January, but the system shows it as overdue and charged a fine of Rs. 500. I have the return receipt from the library counter. Please correct this.',
            'category': 'Library',
            'priority': 'Low',
            'location': 'Central Library',
            'student': students[2],
            'status': 'Resolved',
            'assigned_staff': staff_by_dept.get('Library'),
            'days_ago': 20,
            'resolved': True,
            'feedback_rating': 5,
            'feedback_text': 'Fine waived and record corrected. Very helpful staff.'
        },
        {
            'title': 'Bus not stopping at designated stop',
            'description': 'Bus route 5 does not stop at the Engineering Block stop in the morning. Students have to walk 1 km from the next stop. This happens specifically with the 7:30 AM bus. Driver ignores the stop.',
            'category': 'Transport',
            'priority': 'Medium',
            'location': 'Bus Route 5, Engineering Block stop',
            'student': students[0],
            'status': 'In Progress',
            'assigned_staff': staff_by_dept.get('Transport Office'),
            'days_ago': 2,
            'resolved': False
        },
        {
            'title': 'Course registration system error',
            'description': 'During course registration for next semester, the system shows "Prerequisite not met" for courses I have already completed. This is preventing me from registering for required elective courses.',
            'category': 'Academics',
            'priority': 'High',
            'location': 'Academic Portal',
            'student': students[1],
            'status': 'Assigned',
            'assigned_staff': staff_by_dept.get('Academic Department / HOD'),
            'days_ago': 3,
            'resolved': False
        },
        {
            'title': 'Mental health counseling request',
            'description': 'I would like to request an appointment with the campus counselor for academic stress and anxiety. I have been feeling overwhelmed with coursework and need professional guidance. This is not an emergency.',
            'category': 'Student Wellbeing',
            'priority': 'Medium',
            'location': 'Student Support Cell',
            'student': students[2],
            'is_anonymous': True,
            'status': 'Assigned',
            'assigned_staff': staff_by_dept.get('Student Support Cell'),
            'days_ago': 5,
            'resolved': False
        },
        {
            'title': 'Parking space shortage',
            'description': 'There is severe shortage of parking space for two-wheelers near the Main Gate. Vehicles are parked on the road causing traffic congestion. Need additional parking area or better management.',
            'category': 'Campus Facilities',
            'priority': 'Low',
            'location': 'Main Gate Parking',
            'student': students[0],
            'status': 'Submitted',
            'days_ago': 1,
            'resolved': False
        },
        {
            'title': 'Similar to water issue - Hostel Block C',
            'description': 'Water pressure is very low in Hostel Block C. Showers and taps have minimal flow. This has been ongoing for a week. Similar to the issue in Block A last month.',
            'category': 'Hostel',
            'priority': 'Medium',
            'location': 'Hostel Block C',
            'student': students[1],
            'status': 'Submitted',
            'days_ago': 1,
            'resolved': False
        },
        {
            'title': 'Overdue - Lab equipment not calibrated',
            'description': 'The oscilloscopes and function generators in Electronics Lab 1 have not been calibrated for over 6 months. Measurements are inaccurate affecting lab experiments and project work. Due date for calibration was last month.',
            'category': 'Campus Facilities',
            'priority': 'High',
            'location': 'Electronics Lab 1',
            'student': students[2],
            'status': 'In Progress',
            'assigned_staff': staff_by_dept.get('Maintenance Department'),
            'days_ago': 45,
            'due_days_ago': 10,
            'resolved': False
        },
        {
            'title': 'Overdue - Exam re-evaluation pending',
            'description': 'Applied for re-evaluation of Data Structures exam paper 3 weeks ago. No update on status. The deadline for re-evaluation results was 2 weeks ago. Need this for GPA calculation.',
            'category': 'Examination',
            'priority': 'High',
            'location': 'Examination Cell',
            'student': students[0],
            'status': 'In Progress',
            'assigned_staff': staff_by_dept.get('Examination Cell'),
            'days_ago': 30,
            'due_days_ago': 5,
            'resolved': False
        }
    ]
    
    for i, data in enumerate(complaint_data):
        created_at = datetime.utcnow() - timedelta(days=data['days_ago'])
        due_date = None
        if 'due_days_ago' in data:
            due_date = datetime.utcnow() - timedelta(days=data['due_days_ago'])
        
        student = data['student']
        assigned_staff = data.get('assigned_staff')
        
        ai_result = get_ai_suggestions(data['title'], data['description'])
        
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
            ml_predicted_category=ai_result['category'],
            ml_category_confidence=ai_result['category_confidence'] / 100 if ai_result['category_confidence'] else None,
            ml_predicted_priority=ai_result['priority'],
            ml_priority_confidence=ai_result['priority_confidence'] / 100 if ai_result['priority_confidence'] else None,
            ml_suggested_department=ai_result['department'],
            ml_predicted_duration=ai_result.get('estimated_duration_days'),
            is_duplicate=data.get('is_duplicate', False)
        )
        
        if data.get('resolved'):
            complaint.resolved_at = created_at + timedelta(days=2)
            complaint.resolution_time_days = 2.0
            if data['status'] == 'Closed':
                complaint.closed_at = complaint.resolved_at + timedelta(days=1)
        
        if data.get('is_duplicate') and data.get('parent_ticket'):
            parent = Complaint.query.filter_by(ticket_number=f"CR-2026-{data['parent_ticket']:04d}").first()
            if parent:
                complaint.parent_complaint_id = parent.id
        
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
    seed_database()