"""
CampusResolve Business Logic Services

Centralized service layer for complaint management, notifications,
SLA tracking, workload balancing, and analytics.
"""
from datetime import datetime, timedelta
from sqlalchemy import func, desc, or_, and_, case
from app.extensions import db
from app.models.models import (
    User, Complaint, StatusHistory, Notification, Feedback,
    AuditLog, ComplaintAttachment, ComplaintComment
)
from app.ai.ai_utils import get_ai_suggestions
from config import Config


# ─── SLA Configuration ──────────────────────────────────────────────
SLA_TARGET_DAYS = {
    'Critical': 1,
    'High': 2,
    'Medium': 5,
    'Low': 7,
}


# ─── Complaint Services ─────────────────────────────────────────────
def generate_ticket_number():
    """Generate a unique ticket number CR-YYYY-NNNN."""
    year = datetime.utcnow().year
    count = Complaint.query.filter(
        Complaint.ticket_number.like(f'CR-{year}-%')
    ).count() + 1
    return f'CR-{year}-{count:04d}'


def create_complaint(student, title, description, category=None, priority=None,
                     location=None, is_anonymous=False, attachment=None):
    """Create a new complaint with AI suggestions."""
    ticket_number = generate_ticket_number()
    department = None
    if category:
        department = Config.CATEGORY_DEPARTMENT_MAP.get(category)

    complaint = Complaint(
        ticket_number=ticket_number,
        student_id=student.id,
        title=title,
        description=description,
        category=category,
        priority=priority,
        location=location,
        is_anonymous=is_anonymous,
        status='Submitted',
        department=department,
    )

    # Get AI suggestions
    ai_result = get_ai_suggestions(title, description)
    complaint.ml_predicted_category = ai_result['category']
    complaint.ml_category_confidence = ai_result['category_confidence'] / 100
    complaint.ml_predicted_priority = ai_result['priority']
    complaint.ml_priority_confidence = ai_result['priority_confidence'] / 100
    complaint.ml_suggested_department = ai_result['department']
    complaint.ml_predicted_duration = ai_result.get('estimated_duration_days')

    db.session.add(complaint)
    db.session.flush()

    # Handle attachment
    if attachment:
        att = save_attachment(attachment, complaint.id)
        if att:
            db.session.add(att)

    # Initial status history
    history = StatusHistory(
        complaint_id=complaint.id,
        actor_id=student.id,
        old_status=None,
        new_status='Submitted',
        note='Complaint submitted'
    )
    db.session.add(history)

    log_audit(student.id, 'create', 'complaint', complaint.id,
              f'Created complaint {ticket_number}')
    create_notification(student.id, 'Complaint Submitted',
                        f'Your complaint {ticket_number} has been submitted successfully.',
                        complaint.id)

    db.session.commit()
    return complaint


def save_attachment(file_storage, complaint_id, prefix=''):
    """Save uploaded file and return ComplaintAttachment."""
    from werkzeug.utils import secure_filename
    from flask import current_app
    import os

    filename = secure_filename(file_storage.filename)
    if not filename:
        return None

    ext = filename.rsplit('.', 1)[1].lower()
    if ext not in current_app.config['ALLOWED_EXTENSIONS']:
        return None

    stored_name = f"{prefix}{complaint_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{filename}"
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], stored_name)
    file_storage.save(filepath)

    return ComplaintAttachment(
        complaint_id=complaint_id,
        original_filename=filename,
        stored_filename=stored_name,
        content_type=file_storage.content_type or 'application/octet-stream',
        file_size=os.path.getsize(filepath)
    )


def change_status(complaint, new_status, actor, note=None):
    """Change complaint status with validation and history."""
    valid_transitions = {
        'Submitted': ['Under Review', 'Assigned'],
        'Under Review': ['Assigned', 'Submitted'],
        'Assigned': ['In Progress', 'Under Review'],
        'In Progress': ['Pending Student Response', 'Resolved', 'Assigned'],
        'Pending Student Response': ['In Progress', 'Resolved'],
        'Resolved': ['Closed', 'In Progress'],
        'Closed': ['Resolved'],
    }

    old_status = complaint.status
    if old_status == new_status:
        return False, 'Status unchanged'

    if new_status not in valid_transitions.get(old_status, []):
        # Admin can override; staff restricted
        if not actor.is_admin():
            return False, f'Invalid transition from {old_status} to {new_status}'

    complaint.status = new_status
    complaint.updated_at = datetime.utcnow()

    if new_status == 'Resolved':
        complaint.resolved_at = datetime.utcnow()
        if complaint.created_at:
            delta = complaint.resolved_at - complaint.created_at
            complaint.resolution_time_days = round(delta.total_seconds() / 86400, 1)
    elif new_status == 'Closed':
        complaint.closed_at = datetime.utcnow()

    history = StatusHistory(
        complaint_id=complaint.id,
        actor_id=actor.id,
        old_status=old_status,
        new_status=new_status,
        note=note
    )
    db.session.add(history)

    log_audit(actor.id, 'status_change', 'complaint', complaint.id,
              f'{old_status} -> {new_status}: {note or ""}')

    # Notify student
    if complaint.student_id:
        create_notification(
            complaint.student_id,
            f'Status Update: {new_status}',
            f'Your complaint {complaint.ticket_number} status changed to {new_status}.',
            complaint.id
        )

    return True, 'Status updated'


def assign_complaint(complaint, staff_id, due_date=None, actor=None, note=''):
    """Assign complaint to staff member."""
    from app.models.models import User
    staff = None
    if staff_id and staff_id > 0:
        staff = User.query.get(staff_id)
        if not staff or not staff.is_staff():
            return False, 'Invalid staff member'
        complaint.assigned_staff_id = staff.id
        complaint.department = staff.department
    else:
        complaint.assigned_staff_id = None

    if due_date:
        if isinstance(due_date, str):
            due_date = datetime.strptime(due_date, '%Y-%m-%d')
        complaint.due_date = due_date

    if complaint.status in ['Submitted', 'Under Review']:
        complaint.status = 'Assigned'

    history = StatusHistory(
        complaint_id=complaint.id,
        actor_id=actor.id if actor else (staff.id if staff else None),
        old_status=complaint.status,
        new_status='Assigned',
        note=note
    )
    db.session.add(history)

    log_audit(actor.id if actor else (staff.id if staff else 0),
              'assign', 'complaint', complaint.id,
              f'Assigned to {staff.full_name if staff else "None"}')

    if complaint.student_id:
        create_notification(
            complaint.student_id,
            'Complaint Assigned',
            f'Your complaint {complaint.ticket_number} has been assigned.',
            complaint.id
        )
    if staff:
        create_notification(
            staff.id,
            'New Complaint Assigned',
            f'Complaint {complaint.ticket_number} has been assigned to you.',
            complaint.id
        )

    return True, 'Complaint assigned'


def get_accessible_complaints_query(user):
    """Get query for complaints accessible to user based on role."""
    if user.is_admin():
        return Complaint.query
    elif user.is_staff():
        return Complaint.query.filter(
            or_(
                Complaint.assigned_staff_id == user.id,
                Complaint.department == user.department
            )
        )
    else:
        return Complaint.query.filter_by(student_id=user.id)


# ─── SLA Services ───────────────────────────────────────────────────
def get_sla_target_days(priority):
    """Get SLA target days for a priority level."""
    return SLA_TARGET_DAYS.get(priority, 5)


def is_overdue(complaint):
    """Check if complaint is overdue based on due_date."""
    if not complaint.due_date:
        return False
    if complaint.status in ['Resolved', 'Closed']:
        return False
    return complaint.due_date < datetime.utcnow()


def get_sla_status(complaint):
    """Get detailed SLA status for a complaint."""
    if not complaint.due_date:
        return {'status': 'no_due_date', 'days_remaining': None, 'overdue': False}

    now = datetime.utcnow()
    if complaint.status in ['Resolved', 'Closed']:
        return {'status': 'completed', 'days_remaining': 0, 'overdue': False}

    delta = complaint.due_date - now
    days_remaining = delta.days

    if days_remaining < 0:
        return {'status': 'overdue', 'days_remaining': days_remaining, 'overdue': True}
    elif days_remaining == 0:
        return {'status': 'due_today', 'days_remaining': 0, 'overdue': False}
    elif days_remaining <= 2:
        return {'status': 'approaching', 'days_remaining': days_remaining, 'overdue': False}
    else:
        return {'status': 'on_track', 'days_remaining': days_remaining, 'overdue': False}


def get_escalation_candidates(hours=24):
    """Get complaints needing escalation (overdue or approaching SLA)."""
    now = datetime.utcnow()
    threshold = now + timedelta(hours=hours)

    return Complaint.query.filter(
        Complaint.status.in_(['Assigned', 'In Progress', 'Pending Student Response']),
        Complaint.due_date.isnot(None),
        Complaint.due_date <= threshold
    ).order_by(Complaint.due_date).all()


# ─── Workload & Assignment Services ─────────────────────────────────
def get_staff_workload(department=None):
    """Get workload summary for staff members."""
    query = User.query.filter_by(role='staff', is_active=True)
    if department:
        query = query.filter_by(department=department)

    staff_members = query.all()
    result = []

    for staff in staff_members:
        base = get_accessible_complaints_query(staff)
        open_count = base.filter(
            Complaint.status.in_(['Assigned', 'In Progress', 'Pending Student Response'])
        ).count()
        overdue_count = base.filter(
            Complaint.due_date.isnot(None),
            Complaint.due_date < datetime.utcnow(),
            Complaint.status.in_(['Assigned', 'In Progress', 'Pending Student Response'])
        ).count()
        resolved_count = base.filter(
            Complaint.status.in_(['Resolved', 'Closed'])
        ).count()

        result.append({
            'staff': staff,
            'open_count': open_count,
            'overdue_count': overdue_count,
            'resolved_count': resolved_count,
            'total_load': open_count,
        })

    return sorted(result, key=lambda x: x['total_load'])


def suggest_assignment(complaint):
    """Suggest best staff member for a complaint based on workload and department."""
    staff_list = get_staff_workload(complaint.department)
    if not staff_list:
        return None

    # Prefer staff in same department with lowest load
    for s in staff_list:
        if s['staff'].department == complaint.department:
            return s['staff']

    # Fallback to lowest overall load
    return staff_list[0]['staff'] if staff_list else None


# ─── Notification Services ──────────────────────────────────────────
def create_notification(recipient_id, title, message, complaint_id=None):
    """Create a notification."""
    notif = Notification(
        recipient_id=recipient_id,
        title=title,
        message=message,
        complaint_id=complaint_id
    )
    db.session.add(notif)
    return notif


def get_unread_count(user_id):
    """Get unread notification count for user."""
    return Notification.query.filter_by(
        recipient_id=user_id, is_read=False
    ).count()


def mark_notification_read(notif_id, user_id):
    """Mark notification as read."""
    notif = Notification.query.filter_by(
        id=notif_id, recipient_id=user_id
    ).first()
    if notif:
        notif.is_read = True
        db.session.commit()
        return True
    return False


def mark_all_notifications_read(user_id):
    """Mark all notifications as read for user."""
    Notification.query.filter_by(
        recipient_id=user_id, is_read=False
    ).update({'is_read': True})
    db.session.commit()


# ─── Audit & Logging ────────────────────────────────────────────────
def log_audit(actor_id, action, entity_type, entity_id, details=None):
    """Create audit log entry."""
    log = AuditLog(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details
    )
    db.session.add(log)


# ─── Analytics Services ─────────────────────────────────────────────
def get_analytics_data(date_from=None, date_to=None):
    """Get comprehensive analytics data."""
    query = Complaint.query
    if date_from:
        query = query.filter(Complaint.created_at >= date_from)
    if date_to:
        query = query.filter(Complaint.created_at < datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1))

    # Category distribution
    by_category = db.session.query(
        Complaint.category, func.count(Complaint.id)
    ).filter(Complaint.category.isnot(None)).group_by(Complaint.category).all()

    # Status distribution
    by_status = db.session.query(
        Complaint.status, func.count(Complaint.id)
    ).group_by(Complaint.status).all()

    # Priority distribution
    by_priority = db.session.query(
        Complaint.priority, func.count(Complaint.id)
    ).filter(Complaint.priority.isnot(None)).group_by(Complaint.priority).all()

    # Monthly trend
    monthly = db.session.query(
        func.strftime('%Y-%m', Complaint.created_at), func.count(Complaint.id)
    ).group_by(func.strftime('%Y-%m', Complaint.created_at)).order_by(
        func.strftime('%Y-%m', Complaint.created_at)
    ).all()

    # Department resolution time
    dept_resolution = db.session.query(
        Complaint.department,
        func.avg(func.julianday(Complaint.resolved_at) - func.julianday(Complaint.created_at))
    ).filter(
        Complaint.resolved_at.isnot(None),
        Complaint.department.isnot(None)
    ).group_by(Complaint.department).all()

    # Top locations
    top_locations = db.session.query(
        Complaint.location, func.count(Complaint.id)
    ).filter(Complaint.location.isnot(None)).group_by(Complaint.location).order_by(
        desc(func.count(Complaint.id))
    ).limit(10).all()

    # Feedback
    avg_rating = db.session.query(func.avg(Feedback.rating)).scalar()
    rating_dist = db.session.query(
        Feedback.rating, func.count(Feedback.id)
    ).group_by(Feedback.rating).all()

    # SLA compliance
    sla_compliant = 0
    sla_total = 0
    for c in query.filter(Complaint.resolved_at.isnot(None)).all():
        sla = get_sla_status(c)
        if not sla['overdue']:
            sla_compliant += 1
        sla_total += 1

    # Recurring issues (similar complaints)
    recurring = get_recurring_issues()

    return {
        'by_category': by_category,
        'by_status': by_status,
        'by_priority': by_priority,
        'monthly': monthly,
        'dept_resolution': dept_resolution,
        'top_locations': top_locations,
        'avg_rating': round(avg_rating, 2) if avg_rating else 0,
        'rating_dist': rating_dist,
        'sla_compliance_rate': round((sla_compliant / sla_total * 100), 1) if sla_total else 0,
        'recurring_issues': recurring,
    }


def get_recurring_issues(min_similar=3):
    """Find recurring complaint patterns."""
    from app.ai.ai_utils import _vectorizer, load_models
    if not _vectorizer:
        load_models()
    if not _vectorizer:
        return []

    complaints = Complaint.query.filter(
        Complaint.category.isnot(None),
        Complaint.description.isnot(None)
    ).limit(200).all()

    if len(complaints) < min_similar:
        return []

    corpus = [f"{c.title} {c.description}" for c in complaints]
    corpus_vec = _vectorizer.transform(corpus)

    clusters = []
    processed = set()

    for i, c1 in enumerate(complaints):
        if c1.id in processed:
            continue

        query_vec = _vectorizer.transform([f"{c1.title} {c1.description}"])
        similarities = cosine_similarity(query_vec, corpus_vec).flatten()

        cluster = [c1]
        processed.add(c1.id)

        for idx in similarities.argsort()[::-1]:
            if idx != i and similarities[idx] > 0.3 and complaints[idx].id not in processed:
                cluster.append(complaints[idx])
                processed.add(complaints[idx].id)

        if len(cluster) >= min_similar:
            clusters.append({
                'category': c1.category,
                'count': len(cluster),
                'sample_title': c1.title,
                'tickets': [c.ticket_number for c in cluster[:5]],
            })

    return sorted(clusters, key=lambda x: x['count'], reverse=True)[:10]


# ─── Duplicate Detection ────────────────────────────────────────────
def find_duplicates(complaint, threshold=0.7):
    """Find potential duplicate complaints."""
    from app.ai.ai_utils import _vectorizer, load_models
    if not _vectorizer:
        load_models()
    if not _vectorizer:
        return []

    existing = Complaint.query.filter(
        Complaint.id != complaint.id,
        Complaint.category.isnot(None),
        Complaint.description.isnot(None)
    ).limit(200).all()

    if not existing:
        return []

    corpus = [f"{c.title} {c.description}" for c in existing]
    corpus_vec = _vectorizer.transform(corpus)
    query_vec = _vectorizer.transform([f"{complaint.title} {complaint.description}"])

    similarities = cosine_similarity(query_vec, corpus_vec).flatten()
    results = []

    for idx in similarities.argsort()[::-1]:
        if similarities[idx] >= threshold:
            c = existing[idx]
            results.append({
                'ticket_number': c.ticket_number,
                'title': c.title,
                'category': c.category,
                'status': c.status,
                'similarity': round(float(similarities[idx]) * 100, 1),
            })

    return results


# Import for cosine similarity
from sklearn.metrics.pairwise import cosine_similarity


# ─── Campus Map Services ────────────────────────────────────────────
CAMPUS_LOCATIONS = {
    'Main Gate': {'x': 10, 'y': 90, 'building': 'Entrance'},
    'Admin Block': {'x': 20, 'y': 70, 'building': 'Administration'},
    'Library': {'x': 30, 'y': 60, 'building': 'Academic'},
    'Engineering Block': {'x': 40, 'y': 50, 'building': 'Academic'},
    'IT Block': {'x': 50, 'y': 40, 'building': 'Academic'},
    'Hostel Block A': {'x': 70, 'y': 80, 'building': 'Hostel'},
    'Hostel Block B': {'x': 75, 'y': 70, 'building': 'Hostel'},
    'Hostel Block C': {'x': 80, 'y': 60, 'building': 'Hostel'},
    'Hostel Mess': {'x': 72, 'y': 65, 'building': 'Hostel'},
    'Sports Complex': {'x': 85, 'y': 40, 'building': 'Sports'},
    'Canteen': {'x': 45, 'y': 70, 'building': 'Common'},
    'Auditorium': {'x': 35, 'y': 30, 'building': 'Common'},
    'Medical Center': {'x': 25, 'y': 20, 'building': 'Support'},
    'Parking Lot': {'x': 15, 'y': 85, 'building': 'Parking'},
    'Bus Stop': {'x': 5, 'y': 95, 'building': 'Transport'},
}


def get_campus_heatmap_data():
    """Get complaint counts by campus location for heatmap."""
    location_counts = db.session.query(
        Complaint.location, func.count(Complaint.id)
    ).filter(
        Complaint.location.isnot(None)
    ).group_by(Complaint.location).all()

    heatmap = []
    for loc, count in location_counts:
        if loc in CAMPUS_LOCATIONS:
            heatmap.append({
                'location': loc,
                'count': count,
                'x': CAMPUS_LOCATIONS[loc]['x'],
                'y': CAMPUS_LOCATIONS[loc]['y'],
                'building': CAMPUS_LOCATIONS[loc]['building'],
            })

    return heatmap


def get_location_details(location_name):
    """Get detailed complaints for a location."""
    return Complaint.query.filter_by(location=location_name).order_by(
        desc(Complaint.created_at)
    ).all()