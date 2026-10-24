import csv
import io
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, make_response
from flask_login import login_required, current_user
from sqlalchemy import desc, func, or_, and_
from app.extensions import db
from app.models.models import User, Complaint, ComplaintAttachment, ComplaintComment, Notification, Feedback, StatusHistory, AuditLog
from app.forms import AdminComplaintEditForm, UserForm, ComplaintFilterForm
from app.ai.ai_utils import get_ai_suggestions
from app.services import (
    get_analytics_data, get_sla_status, get_staff_workload,
    suggest_assignment, find_duplicates, get_campus_heatmap_data,
    get_recurring_issues, CAMPUS_LOCATIONS, SLA_TARGET_DAYS
)
from config import Config

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            return redirect(url_for('errors.forbidden'))
        if not current_user.is_active:
            flash('Your account has been deactivated. Please contact administrator.', 'danger')
            return redirect(url_for('auth.logout'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    # Basic stats
    total = Complaint.query.count()
    submitted_review = Complaint.query.filter(Complaint.status.in_(['Submitted', 'Under Review'])).count()
    assigned_progress = Complaint.query.filter(Complaint.status.in_(['Assigned', 'In Progress'])).count()
    overdue = Complaint.query.filter(Complaint.due_date.isnot(None), Complaint.due_date < datetime.utcnow(), Complaint.status.in_(['Assigned', 'In Progress', 'Pending Student Response'])).count()
    resolved_closed = Complaint.query.filter(Complaint.status.in_(['Resolved', 'Closed'])).count()
    
    # Pending staff approvals
    pending_staff_count = User.query.filter_by(role='staff', is_approved=False).count()
    
    avg_resolution = db.session.query(func.avg(func.julianday(Complaint.resolved_at) - func.julianday(Complaint.created_at))).filter(Complaint.resolved_at.isnot(None)).scalar()
    avg_days = round(avg_resolution, 1) if avg_resolution else 0
    
    category_stats = db.session.query(Complaint.category, func.count(Complaint.id)).filter(Complaint.category.isnot(None)).group_by(Complaint.category).all()
    status_stats = db.session.query(Complaint.status, func.count(Complaint.id)).group_by(Complaint.status).all()
    priority_stats = db.session.query(Complaint.priority, func.count(Complaint.id)).filter(Complaint.priority.isnot(None)).group_by(Complaint.priority).all()
    
    recent_activity = AuditLog.query.order_by(desc(AuditLog.created_at)).limit(10).all()
    
    overdue_tickets = Complaint.query.filter(Complaint.due_date.isnot(None), Complaint.due_date < datetime.utcnow(), Complaint.status.in_(['Assigned', 'In Progress', 'Pending Student Response'])).order_by(Complaint.due_date).limit(10).all()
    
    # SLA compliance
    sla_compliant = 0
    sla_total = 0
    for c in Complaint.query.filter(Complaint.resolved_at.isnot(None)).all():
        from app.services import get_sla_status
        sla = get_sla_status(c)
        if not sla['overdue']:
            sla_compliant += 1
        sla_total += 1
    sla_rate = round((sla_compliant / sla_total * 100), 1) if sla_total else 0
    
    # Staff workload summary
    staff_workload = get_staff_workload()
    
    # Recurring issues
    recurring_issues = get_recurring_issues(min_similar=2)[:5]
    
    return render_template('admin/dashboard.html',
                           total=total, submitted_review=submitted_review, assigned_progress=assigned_progress,
                           overdue=overdue, resolved_closed=resolved_closed, avg_days=avg_days,
                           category_stats=category_stats, status_stats=status_stats, priority_stats=priority_stats,
                           recent_activity=recent_activity, overdue_tickets=overdue_tickets,
                           sla_rate=sla_rate, sla_total=sla_total, sla_compliant=sla_compliant,
                           staff_workload=staff_workload, recurring_issues=recurring_issues,
                           pending_staff_count=pending_staff_count)


@admin_bp.route('/kanban')
@login_required
@admin_required
def kanban():
    """Kanban board view for complaint workflow."""
    statuses = Config.COMPLAINT_STATUSES
    columns = {}
    for status in statuses:
        columns[status] = Complaint.query.filter_by(status=status).order_by(desc(Complaint.priority), Complaint.due_date.asc().nullslast()).all()
    
    return render_template('admin/kanban.html', columns=columns, statuses=statuses)


@admin_bp.route('/campus-map')
@login_required
@admin_required
def campus_map():
    """Campus issue map view."""
    heatmap_data = get_campus_heatmap_data()
    return render_template('admin/campus_map.html', heatmap_data=heatmap_data, locations=CAMPUS_LOCATIONS)


@admin_bp.route('/complaints')
@login_required
@admin_required
def complaints():
    form = ComplaintFilterForm(request.args)
    page = request.args.get('page', 1, type=int)
    
    query = Complaint.query
    
    if form.search.data:
        search = f"%{form.search.data}%"
        query = query.filter(or_(
            Complaint.ticket_number.ilike(search),
            Complaint.title.ilike(search),
            Complaint.description.ilike(search),
            User.full_name.ilike(search)
        ).join(User, Complaint.student_id == User.id))
    
    if form.status.data:
        query = query.filter_by(status=form.status.data)
    if form.category.data:
        query = query.filter_by(category=form.category.data)
    if form.priority.data:
        query = query.filter_by(priority=form.priority.data)
    if form.department.data:
        query = query.filter_by(department=form.department.data)
    if form.date_from.data:
        try:
            date_from = datetime.strptime(form.date_from.data, '%Y-%m-%d')
            query = query.filter(Complaint.created_at >= date_from)
        except ValueError:
            pass
    if form.date_to.data:
        try:
            date_to = datetime.strptime(form.date_to.data, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(Complaint.created_at < date_to)
        except ValueError:
            pass
    if form.show_duplicates.data:
        query = query.filter_by(is_duplicate=True)
    
    sort = request.args.get('sort', 'newest')
    if sort == 'oldest':
        query = query.order_by(Complaint.created_at.asc())
    elif sort == 'priority':
        query = query.order_by(desc(Complaint.priority), Complaint.created_at.desc())
    elif sort == 'due_date':
        query = query.order_by(Complaint.due_date.asc().nullslast())
    else:
        query = query.order_by(desc(Complaint.created_at))
    
    if request.args.get('export') == '1' or request.method == 'POST' and form.export.data:
        return export_complaints_csv(query)
    
    complaints = query.paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/complaints.html', complaints=complaints, form=form, sort=sort, now=datetime.utcnow())


def export_complaints_csv(query):
    complaints = query.all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Ticket Number', 'Student', 'Title', 'Category', 'Priority', 'Department', 'Status', 'Assigned Staff', 'Due Date', 'Created At', 'Resolved At', 'Is Duplicate'])
    
    for c in complaints:
        writer.writerow([
            c.ticket_number,
            c.student.full_name if c.student else 'Anonymous',
            c.title,
            c.category or '',
            c.priority or '',
            c.department or '',
            c.status,
            c.assigned_staff.full_name if c.assigned_staff else '',
            c.due_date.strftime('%Y-%m-%d') if c.due_date else '',
            c.created_at.strftime('%Y-%m-%d %H:%M'),
            c.resolved_at.strftime('%Y-%m-%d %H:%M') if c.resolved_at else '',
            'Yes' if c.is_duplicate else 'No'
        ])
    
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = f'attachment; filename=complaints_{datetime.utcnow().strftime("%Y%m%d")}.csv'
    response.headers['Content-Type'] = 'text/csv'
    return response


@admin_bp.route('/complaints/<ticket_number>')
@login_required
@admin_required
def complaint_detail(ticket_number):
    complaint = Complaint.query.filter_by(ticket_number=ticket_number).first_or_404()
    
    comments = ComplaintComment.query.filter_by(complaint_id=complaint.id).order_by(ComplaintComment.created_at).all()
    attachments = ComplaintAttachment.query.filter_by(complaint_id=complaint.id).all()
    status_history = StatusHistory.query.filter_by(complaint_id=complaint.id).order_by(StatusHistory.created_at).all()
    audit_logs = AuditLog.query.filter_by(entity_type='complaint', entity_id=complaint.id).order_by(desc(AuditLog.created_at)).all()
    feedback = Feedback.query.filter_by(complaint_id=complaint.id).first()
    
    ai_suggestions = None
    if complaint.ml_predicted_category:
        ai_suggestions = {
            'category': complaint.ml_predicted_category,
            'category_confidence': round(complaint.ml_category_confidence * 100, 1) if complaint.ml_category_confidence else 0,
            'priority': complaint.ml_predicted_priority,
            'priority_confidence': round(complaint.ml_priority_confidence * 100, 1) if complaint.ml_priority_confidence else 0,
            'department': complaint.ml_suggested_department,
            'explanation': 'AI model prediction based on complaint text.'
        }
    
    similar = find_similar_complaints(complaint)
    
    form = AdminComplaintEditForm(obj=complaint)
    form.assigned_staff_id.choices = [(0, 'Unassigned')] + [(u.id, f"{u.full_name} ({u.department})") for u in User.query.filter_by(role='staff', is_active=True).all()]
    
    return render_template('admin/complaint_detail.html',
                           complaint=complaint, comments=comments, attachments=attachments,
                           status_history=status_history, audit_logs=audit_logs, feedback=feedback,
                           ai_suggestions=ai_suggestions, similar=similar, form=form,
                           now=datetime.utcnow(), get_sla_status=get_sla_status,
                           SLA_TARGET_DAYS=Config.SLA_TARGET_DAYS)


@admin_bp.route('/complaints/<ticket_number>/assign', methods=['POST'])
@login_required
@admin_required
def assign_complaint(ticket_number):
    complaint = Complaint.query.filter_by(ticket_number=ticket_number).first_or_404()
    
    staff_id = request.form.get('assigned_staff_id', type=int)
    due_date_str = request.form.get('due_date')
    note = request.form.get('note', '')
    
    staff = None
    if staff_id and staff_id > 0:
        staff = User.query.get(staff_id)
        if staff and staff.is_staff():
            complaint.assigned_staff_id = staff.id
            complaint.department = staff.department
            complaint.status = 'Assigned'
            flash(f'Assigned to {staff.full_name}.', 'success')
        else:
            flash('Invalid staff member.', 'danger')
            return redirect(url_for('admin.complaint_detail', ticket_number=ticket_number))
    else:
        complaint.assigned_staff_id = None
        flash('Staff assignment removed.', 'info')
    
    if due_date_str:
        try:
            complaint.due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
        except ValueError:
            flash('Invalid due date format.', 'warning')
    
    history = StatusHistory(complaint_id=complaint.id, actor_id=current_user.id, old_status=complaint.status, new_status='Assigned', note=note)
    db.session.add(history)
    log_audit(current_user.id, 'assign', 'complaint', complaint.id, f'Assigned to {staff.full_name if staff else "None"}')
    
    if complaint.student_id:
        create_notification(complaint.student_id, 'Complaint Assigned', f'Your complaint {complaint.ticket_number} has been assigned.', complaint.id)
    
    if staff:
        create_notification(staff.id, 'New Complaint Assigned', f'Complaint {complaint.ticket_number} has been assigned to you.', complaint.id)
    
    db.session.commit()
    return redirect(url_for('admin.complaint_detail', ticket_number=ticket_number))


@admin_bp.route('/complaints/<ticket_number>/suggest-assignment')
@login_required
@admin_required
def suggest_assignment(ticket_number):
    """API endpoint to get staff assignment suggestion."""
    complaint = Complaint.query.filter_by(ticket_number=ticket_number).first_or_404()
    suggested = suggest_assignment(complaint)
    workload = get_staff_workload(complaint.department)
    
    return jsonify({
        'suggested_staff': {
            'id': suggested.id,
            'name': suggested.full_name,
            'department': suggested.department,
        } if suggested else None,
        'workload': [
            {
                'id': w['staff'].id,
                'name': w['staff'].full_name,
                'department': w['staff'].department,
                'open_count': w['open_count'],
                'overdue_count': w['overdue_count'],
            }
            for w in workload
        ],
        'sla_target_days': SLA_TARGET_DAYS.get(complaint.priority, 5),
    })


@admin_bp.route('/complaints/<ticket_number>/update', methods=['POST'])
@login_required
@admin_required
def update_complaint(ticket_number):
    complaint = Complaint.query.filter_by(ticket_number=ticket_number).first_or_404()
    
    form = AdminComplaintEditForm()
    form.assigned_staff_id.choices = [(0, 'Unassigned')] + [(u.id, f"{u.full_name} ({u.department})") for u in User.query.filter_by(role='staff', is_active=True).all()]
    
    if form.validate_on_submit():
        old_status = complaint.status
        old_category = complaint.category
        old_priority = complaint.priority
        old_department = complaint.department
        
        complaint.category = form.category.data
        complaint.priority = form.priority.data
        complaint.department = form.department.data
        
        if form.assigned_staff_id.data and form.assigned_staff_id.data > 0:
            staff = User.query.get(form.assigned_staff_id.data)
            if staff:
                complaint.assigned_staff_id = staff.id
                complaint.department = staff.department
        else:
            complaint.assigned_staff_id = None
        
        if form.due_date.data:
            try:
                complaint.due_date = datetime.strptime(form.due_date.data, '%Y-%m-%d')
            except ValueError:
                pass
        
        if form.status.data != old_status:
            complaint.status = form.status.data
            complaint.updated_at = datetime.utcnow()
            if form.status.data == 'Resolved':
                complaint.resolved_at = datetime.utcnow()
            elif form.status.data == 'Closed':
                complaint.closed_at = datetime.utcnow()
            
            history = StatusHistory(complaint_id=complaint.id, actor_id=current_user.id, old_status=old_status, new_status=form.status.data, note=form.note.data if hasattr(form, 'note') else None)
            db.session.add(history)
            
            if complaint.student_id:
                create_notification(complaint.student_id, f'Status Update: {form.status.data}', f'Your complaint {complaint.ticket_number} status changed to {form.status.data}.', complaint.id)
        
        if form.is_duplicate.data and form.parent_complaint_id.data:
            parent = Complaint.query.filter_by(ticket_number=form.parent_complaint_id.data).first()
            if parent and parent.id != complaint.id:
                complaint.is_duplicate = True
                complaint.parent_complaint_id = parent.id
                flash(f'Marked as duplicate of {parent.ticket_number}.', 'info')
        
        log_audit(current_user.id, 'update', 'complaint', complaint.id, f'Category: {old_category}->{complaint.category}, Priority: {old_priority}->{complaint.priority}, Dept: {old_department}->{complaint.department}, Status: {old_status}->{complaint.status}')
        db.session.commit()
        flash('Complaint updated successfully.', 'success')
    
    return redirect(url_for('admin.complaint_detail', ticket_number=ticket_number))


@admin_bp.route('/users')
@login_required
@admin_required
def users():
    page = request.args.get('page', 1, type=int)
    users = User.query.order_by(User.role, User.full_name).paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/users.html', users=users)


@admin_bp.route('/users/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_user():
    form = UserForm()
    if form.validate_on_submit():
        user = User(
            full_name=form.full_name.data,
            email=form.email.data.lower(),
            role=form.role.data,
            department=form.department.data if form.role.data == 'staff' else None,
            is_active=form.is_active.data
        )
        user.set_password(form.password.data if form.password.data else 'Student@123')
        db.session.add(user)
        log_audit(current_user.id, 'create', 'user', user.id, f'Created {form.role.data} user')
        db.session.commit()
        flash('User created successfully.', 'success')
        return redirect(url_for('admin.users'))
    return render_template('admin/user_form.html', form=form, title='Create User')


@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = UserForm(user_id=user_id, obj=user)
    if form.validate_on_submit():
        user.full_name = form.full_name.data
        user.email = form.email.data.lower()
        user.role = form.role.data
        user.department = form.department.data if form.role.data == 'staff' else None
        user.is_active = form.is_active.data
        if form.password.data:
            user.set_password(form.password.data)
        log_audit(current_user.id, 'update', 'user', user.id, 'Updated user')
        db.session.commit()
        flash('User updated successfully.', 'success')
        return redirect(url_for('admin.users'))
    return render_template('admin/user_form.html', form=form, title='Edit User')


@admin_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Cannot deactivate yourself.', 'danger')
        return redirect(url_for('admin.users'))
    user.is_active = not user.is_active
    log_audit(current_user.id, 'toggle_active', 'user', user.id, f'Active: {user.is_active}')
    db.session.commit()
    flash(f'User {"activated" if user.is_active else "deactivated"}.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/staff-approvals')
@login_required
@admin_required
def staff_approvals():
    """View pending staff approval requests."""
    pending_staff = User.query.filter_by(role='staff', is_approved=False).order_by(User.created_at.desc()).all()
    approved_staff = User.query.filter_by(role='staff', is_approved=True).order_by(User.created_at.desc()).all()
    return render_template('admin/staff_approvals.html', pending_staff=pending_staff, approved_staff=approved_staff)


@admin_bp.route('/staff-approvals/<int:user_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_staff(user_id):
    """Approve a pending staff registration."""
    user = User.query.get_or_404(user_id)
    if user.role != 'staff':
        flash('User is not a staff member.', 'danger')
        return redirect(url_for('admin.staff_approvals'))
    
    user.is_approved = True
    log_audit(current_user.id, 'approve_staff', 'user', user.id, f'Approved staff registration')
    
    # Notify the staff member
    create_notification(user.id, 'Account Approved', 'Your staff registration has been approved. You can now log in.')
    
    db.session.commit()
    flash(f'Staff {user.full_name} approved successfully.', 'success')
    return redirect(url_for('admin.staff_approvals'))


@admin_bp.route('/staff-approvals/<int:user_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_staff(user_id):
    """Reject a pending staff registration."""
    user = User.query.get_or_404(user_id)
    if user.role != 'staff':
        flash('User is not a staff member.', 'danger')
        return redirect(url_for('admin.staff_approvals'))
    
    email = user.email
    name = user.full_name
    log_audit(current_user.id, 'reject_staff', 'user', user.id, f'Rejected staff registration')
    
    # Notify the staff member
    create_notification(user.id, 'Account Rejected', 'Your staff registration has been rejected. Please contact administration for more information.')
    
    db.session.delete(user)
    db.session.commit()
    flash(f'Staff {name} ({email}) registration rejected and removed.', 'success')
    return redirect(url_for('admin.staff_approvals'))


@admin_bp.route('/analytics')
@login_required
@admin_required
def analytics():
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    data = get_analytics_data(date_from, date_to)
    
    return render_template('admin/analytics.html',
                           **data, date_from=date_from, date_to=date_to)


def find_similar_complaints(complaint, top_n=3):
    complaints = Complaint.query.filter(
        Complaint.id != complaint.id,
        Complaint.category.isnot(None),
        Complaint.description.isnot(None)
    ).limit(100).all()
    
    if not complaints:
        return []
    
    from app.ai.ai_utils import _vectorizer
    if not _vectorizer:
        from app.ai.ai_utils import load_models
        load_models()
    if not _vectorizer:
        return []
    
    from sklearn.metrics.pairwise import cosine_similarity
    corpus = [f"{c.title} {c.description}" for c in complaints]
    corpus_vec = _vectorizer.transform(corpus)
    query_vec = _vectorizer.transform([f"{complaint.title} {complaint.description}"])
    
    similarities = cosine_similarity(query_vec, corpus_vec).flatten()
    top_indices = similarities.argsort()[-top_n:][::-1]
    
    results = []
    for idx in top_indices:
        if similarities[idx] > 0.1:
            c = complaints[idx]
            results.append({
                'ticket_number': c.ticket_number,
                'title': c.title[:80],
                'category': c.category,
                'status': c.status,
                'similarity': round(float(similarities[idx]) * 100, 1)
            })
    
    return results


@admin_bp.route('/api/complaints/<ticket_number>/duplicates')
@login_required
@admin_required
def api_find_duplicates(ticket_number):
    """API endpoint to find potential duplicate complaints."""
    complaint = Complaint.query.filter_by(ticket_number=ticket_number).first_or_404()
    duplicates = find_duplicates(complaint, threshold=0.7)
    return jsonify({'duplicates': duplicates})


def log_audit(actor_id, action, entity_type, entity_id, details=None):
    log = AuditLog(actor_id=actor_id, action=action, entity_type=entity_type, entity_id=entity_id, details=details)
    db.session.add(log)


def create_notification(recipient_id, title, message, complaint_id=None):
    notif = Notification(recipient_id=recipient_id, title=title, message=message, complaint_id=complaint_id)
    db.session.add(notif)