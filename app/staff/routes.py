from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import desc, func, or_
from app.extensions import db
from app.models.models import Complaint, ComplaintAttachment, ComplaintComment, Notification, StatusHistory
from app.forms import StaffStatusUpdateForm, ComplaintCommentForm
from app.services import get_sla_status, get_staff_workload, get_accessible_complaints_query
from config import Config

staff_bp = Blueprint('staff', __name__, url_prefix='/staff')


def staff_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_staff():
            return redirect(url_for('errors.forbidden'))
        if not current_user.is_active:
            flash('Your account has been deactivated. Please contact administrator.', 'danger')
            return redirect(url_for('auth.logout'))
        return f(*args, **kwargs)
    return decorated_function


@staff_bp.route('/dashboard')
@login_required
@staff_required
def dashboard():
    base_query = get_accessible_complaints_query(current_user)
    
    assigned_count = base_query.count()
    overdue_count = base_query.filter(Complaint.due_date.isnot(None), Complaint.due_date < datetime.utcnow(), Complaint.status.in_(['Assigned', 'In Progress', 'Pending Student Response'])).count()
    resolved_count = base_query.filter(Complaint.status.in_(['Resolved', 'Closed'])).count()
    in_progress_count = base_query.filter(Complaint.status.in_(['In Progress'])).count()
    
    status_filter = request.args.get('status')
    priority_filter = request.args.get('priority')
    
    query = base_query
    if status_filter:
        query = query.filter_by(status=status_filter)
    if priority_filter:
        query = query.filter_by(priority=priority_filter)
    
    page = request.args.get('page', 1, type=int)
    complaints = query.order_by(desc(Complaint.priority), Complaint.due_date.asc().nullslast(), desc(Complaint.created_at)).paginate(page=page, per_page=15, error_out=False)
    
    # Workload for current department
    workload = get_staff_workload(current_user.department)
    
    return render_template('staff/dashboard.html',
                           assigned_count=assigned_count, overdue_count=overdue_count, resolved_count=resolved_count,
                           in_progress_count=in_progress_count,
                           complaints=complaints, status_filter=status_filter, priority_filter=priority_filter,
                           now=datetime.utcnow(), workload=workload, get_sla_status=get_sla_status,
                           SLA_TARGET_DAYS=Config.SLA_TARGET_DAYS)


@staff_bp.route('/complaints/<ticket_number>')
@login_required
@staff_required
def complaint_detail(ticket_number):
    complaint = Complaint.query.filter_by(ticket_number=ticket_number).first_or_404()
    
    if not can_access_complaint(complaint):
        return redirect(url_for('errors.forbidden'))
    
    comments = ComplaintComment.query.filter_by(complaint_id=complaint.id).order_by(ComplaintComment.created_at).all()
    attachments = ComplaintAttachment.query.filter_by(complaint_id=complaint.id).all()
    status_history = StatusHistory.query.filter_by(complaint_id=complaint.id).order_by(StatusHistory.created_at).all()
    
    form = StaffStatusUpdateForm()
    comment_form = ComplaintCommentForm()
    
    return render_template('staff/assigned_complaint_detail.html',
                           complaint=complaint, comments=comments, attachments=attachments,
                           status_history=status_history, form=form, comment_form=comment_form,
                           now=datetime.utcnow(), get_sla_status=get_sla_status,
                           SLA_TARGET_DAYS=Config.SLA_TARGET_DAYS)


@staff_bp.route('/complaints/<ticket_number>/update', methods=['POST'])
@login_required
@staff_required
def update_complaint(ticket_number):
    complaint = Complaint.query.filter_by(ticket_number=ticket_number).first_or_404()
    
    if not can_access_complaint(complaint):
        return redirect(url_for('errors.forbidden'))
    
    form = StaffStatusUpdateForm()
    if form.validate_on_submit():
        old_status = complaint.status
        new_status = form.status.data
        
        if new_status not in ['In Progress', 'Pending Student Response', 'Resolved']:
            flash('Invalid status transition.', 'danger')
            return redirect(url_for('staff.complaint_detail', ticket_number=ticket_number))
        
        if old_status == new_status:
            flash('Status unchanged.', 'info')
            return redirect(url_for('staff.complaint_detail', ticket_number=ticket_number))
        
        complaint.status = new_status
        complaint.updated_at = datetime.utcnow()
        
        if new_status == 'Resolved':
            complaint.resolved_at = datetime.utcnow()
        
        history = StatusHistory(
            complaint_id=complaint.id,
            actor_id=current_user.id,
            old_status=old_status,
            new_status=new_status,
            note=form.note.data
        )
        db.session.add(history)
        
        if form.evidence.data:
            attachment = save_attachment(form.evidence.data, complaint.id, 'evidence')
            if attachment:
                db.session.add(attachment)
        
        log_audit(current_user.id, 'status_update', 'complaint', complaint.id, f'{old_status} -> {new_status}: {form.note.data or ""}')
        
        if complaint.student_id:
            create_notification(complaint.student_id, f'Status Update: {new_status}', 
                              f'Your complaint {complaint.ticket_number} status changed to {new_status}.', complaint.id)
        
        db.session.commit()
        flash(f'Status updated to {new_status}.', 'success')
    
    return redirect(url_for('staff.complaint_detail', ticket_number=ticket_number))


@staff_bp.route('/complaints/<ticket_number>/comment', methods=['POST'])
@login_required
@staff_required
def add_comment(ticket_number):
    complaint = Complaint.query.filter_by(ticket_number=ticket_number).first_or_404()
    
    if not can_access_complaint(complaint):
        return redirect(url_for('errors.forbidden'))
    
    form = ComplaintCommentForm()
    if form.validate_on_submit():
        comment = ComplaintComment(
            complaint_id=complaint.id,
            author_id=current_user.id,
            comment_text=form.comment_text.data,
            is_internal_note=form.is_internal_note.data
        )
        db.session.add(comment)
        log_audit(current_user.id, 'comment', 'complaint', complaint.id, 'Added internal note' if form.is_internal_note.data else 'Added comment')
        db.session.commit()
        flash('Comment added.', 'success')
    
    return redirect(url_for('staff.complaint_detail', ticket_number=ticket_number))


def can_access_complaint(complaint):
    return complaint.assigned_staff_id == current_user.id or complaint.department == current_user.department


def save_attachment(file_storage, complaint_id, prefix=''):
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


def log_audit(actor_id, action, entity_type, entity_id, details=None):
    from app.models.models import AuditLog
    log = AuditLog(actor_id=actor_id, action=action, entity_type=entity_type, entity_id=entity_id, details=details)
    db.session.add(log)


def create_notification(recipient_id, title, message, complaint_id=None):
    notif = Notification(recipient_id=recipient_id, title=title, message=message, complaint_id=complaint_id)
    db.session.add(notif)