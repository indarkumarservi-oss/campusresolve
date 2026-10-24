from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import desc, func
from app.extensions import db
from app.models.models import Complaint, ComplaintAttachment, ComplaintComment, Notification, Feedback, StatusHistory
from app.forms import ComplaintForm, ComplaintCommentForm, FeedbackForm
from app.services import get_sla_status
from config import Config

student_bp = Blueprint('student', __name__, url_prefix='/student')


def student_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_student():
            return redirect(url_for('errors.forbidden'))
        if not current_user.is_active:
            flash('Your account has been deactivated. Please contact administrator.', 'danger')
            return redirect(url_for('auth.logout'))
        return f(*args, **kwargs)
    return decorated_function


@student_bp.route('/dashboard')
@login_required
@student_required
def dashboard():
    total = Complaint.query.filter_by(student_id=current_user.id).count()
    open_count = Complaint.query.filter_by(student_id=current_user.id).filter(Complaint.status.in_(['Submitted', 'Under Review', 'Assigned', 'In Progress', 'Pending Student Response'])).count()
    resolved = Complaint.query.filter_by(student_id=current_user.id, status='Resolved').count()
    closed = Complaint.query.filter_by(student_id=current_user.id, status='Closed').count()
    
    overdue_count = Complaint.query.filter_by(student_id=current_user.id).filter(
        Complaint.due_date.isnot(None),
        Complaint.due_date < datetime.utcnow(),
        Complaint.status.in_(['Submitted', 'Under Review', 'Assigned', 'In Progress', 'Pending Student Response'])
    ).count()
    
    pending_response_count = Complaint.query.filter_by(student_id=current_user.id, status='Pending Student Response').count()
    in_progress_count = Complaint.query.filter_by(student_id=current_user.id, status='In Progress').count()
    
    recent = Complaint.query.filter_by(student_id=current_user.id).order_by(desc(Complaint.created_at)).limit(5).all()
    
    notifications = Notification.query.filter_by(recipient_id=current_user.id, is_read=False).order_by(desc(Notification.created_at)).limit(5).all()
    unread_count = Notification.query.filter_by(recipient_id=current_user.id, is_read=False).count()
    
    return render_template('student/dashboard.html',
                           total=total, open_count=open_count, resolved=resolved, closed=closed,
                           overdue_count=overdue_count, pending_response_count=pending_response_count,
                           in_progress_count=in_progress_count,
                           recent=recent, notifications=notifications, unread_count=unread_count,
                           get_sla_status=get_sla_status)


@student_bp.route('/complaints')
@login_required
@student_required
def my_complaints():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status')
    
    query = Complaint.query.filter_by(student_id=current_user.id)
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    complaints = query.order_by(desc(Complaint.created_at)).paginate(page=page, per_page=10, error_out=False)
    return render_template('student/my_complaints.html', complaints=complaints, status_filter=status_filter)


@student_bp.route('/complaints/new', methods=['GET', 'POST'])
@login_required
@student_required
def new_complaint():
    form = ComplaintForm()
    if form.validate_on_submit():
        # Check if AI verification is required (skip in testing mode)
        from flask import current_app
        is_testing = current_app.config.get('TESTING', False)
        
        ai_verification_token = request.form.get('ai_verification_token')
        ai_verified = request.form.get('ai_verified') == 'true'
        
        if not is_testing:
            if not ai_verified or not ai_verification_token:
                flash('Please verify your complaint with AI before submitting.', 'danger')
                return render_template('student/complaint_form.html', form=form)
            
            # Verify the token matches the submitted text
            from app.ai.ai_utils import verify_verification_token
            verification_result = verify_verification_token(
                ai_verification_token,
                form.title.data,
                form.description.data
            )
            
            if not verification_result.get('valid'):
                flash('Verification failed: ' + verification_result.get('error', 'Invalid token'), 'danger')
                return render_template('student/complaint_form.html', form=form)
            
            # Verify category and priority match verification
            if form.category.data != verification_result.get('category') or \
               form.priority.data != verification_result.get('priority'):
                flash('Category or priority was changed after verification. Please re-verify.', 'danger')
                return render_template('student/complaint_form.html', form=form)
        else:
            # In testing mode, use form data directly for verification result
            verification_result = {
                'category': form.category.data,
                'priority': form.priority.data,
                'duration': 5
            }
        
        ticket_number = generate_ticket_number()
        category = form.category.data if form.category.data else None
        department = current_app.config['CATEGORY_DEPARTMENT_MAP'].get(category) if category else None
        complaint = Complaint(
            ticket_number=ticket_number,
            student_id=current_user.id,
            title=form.title.data,
            description=form.description.data,
            category=category,
            priority=form.priority.data if form.priority.data else None,
            location=form.location.data if form.location.data else None,
            is_anonymous=form.is_anonymous.data,
            status='Submitted',
            department=department,
            ai_verification_token=ai_verification_token if not is_testing else 'test-token',
            ai_verification_expires=datetime.fromisoformat(verification_result.get('expires').replace('Z', '+00:00')) if verification_result.get('expires') else None,
            ai_verified_category=verification_result.get('category'),
            ai_verified_priority=verification_result.get('priority'),
            ai_verified_duration=verification_result.get('duration'),
            ai_verified_at=datetime.utcnow()
        )
        db.session.add(complaint)
        db.session.flush()
        
        if form.attachment.data:
            attachment = save_attachment(form.attachment.data, complaint.id)
            if attachment:
                db.session.add(attachment)
        
        # Create initial status history
        history = StatusHistory(
            complaint_id=complaint.id,
            actor_id=current_user.id,
            old_status=None,
            new_status='Submitted',
            note='Complaint submitted'
        )
        db.session.add(history)
        
        log_audit(current_user.id, 'create', 'complaint', complaint.id, f'Created complaint {ticket_number}')
        create_notification(current_user.id, 'Complaint Submitted', f'Your complaint {ticket_number} has been submitted successfully.', complaint.id)
        
        db.session.commit()
        flash(f'Complaint submitted successfully! Your ticket number is {ticket_number}.', 'success')
        return redirect(url_for('student.my_complaints'))
    
    return render_template('student/complaint_form.html', form=form)


@student_bp.route('/complaints/<ticket_number>')
@login_required
@student_required
def complaint_detail(ticket_number):
    complaint = Complaint.query.filter_by(ticket_number=ticket_number).first_or_404()
    
    if complaint.student_id != current_user.id:
        return redirect(url_for('errors.forbidden'))
    
    comments = ComplaintComment.query.filter_by(complaint_id=complaint.id).order_by(ComplaintComment.created_at).all()
    attachments = ComplaintAttachment.query.filter_by(complaint_id=complaint.id).all()
    status_history = StatusHistory.query.filter_by(complaint_id=complaint.id).order_by(StatusHistory.created_at).all()
    feedback = Feedback.query.filter_by(complaint_id=complaint.id).first()
    
    comment_form = ComplaintCommentForm()
    feedback_form = FeedbackForm()
    
    can_feedback = complaint.status in ['Resolved', 'Closed'] and not feedback
    can_comment = complaint.status != 'Closed'
    
    return render_template('student/complaint_detail.html',
                           complaint=complaint, comments=comments, attachments=attachments,
                           status_history=status_history, feedback=feedback,
                           comment_form=comment_form, feedback_form=feedback_form,
                           can_feedback=can_feedback, can_comment=can_comment,
                           now=datetime.utcnow(),
                           get_sla_status=get_sla_status,
                           SLA_TARGET_DAYS=Config.SLA_TARGET_DAYS)


@student_bp.route('/complaints/<ticket_number>/comment', methods=['POST'])
@login_required
@student_required
def add_comment(ticket_number):
    complaint = Complaint.query.filter_by(ticket_number=ticket_number).first_or_404()
    
    if complaint.student_id != current_user.id:
        return redirect(url_for('errors.forbidden'))
    
    if complaint.status == 'Closed':
        flash('Cannot comment on closed complaints.', 'warning')
        return redirect(url_for('student.complaint_detail', ticket_number=ticket_number))
    
    form = ComplaintCommentForm()
    if form.validate_on_submit():
        comment = ComplaintComment(
            complaint_id=complaint.id,
            author_id=current_user.id,
            comment_text=form.comment_text.data,
            is_internal_note=False
        )
        db.session.add(comment)
        log_audit(current_user.id, 'comment', 'complaint', complaint.id, 'Added comment')
        db.session.commit()
        flash('Comment added.', 'success')
    
    return redirect(url_for('student.complaint_detail', ticket_number=ticket_number))


@student_bp.route('/complaints/<ticket_number>/feedback', methods=['POST'])
@login_required
@student_required
def submit_feedback(ticket_number):
    complaint = Complaint.query.filter_by(ticket_number=ticket_number).first_or_404()
    
    if complaint.student_id != current_user.id:
        return redirect(url_for('errors.forbidden'))
    
    if complaint.status not in ['Resolved', 'Closed']:
        flash('Feedback can only be submitted for resolved or closed complaints.', 'warning')
        return redirect(url_for('student.complaint_detail', ticket_number=ticket_number))
    
    existing = Feedback.query.filter_by(complaint_id=complaint.id).first()
    if existing:
        flash('Feedback already submitted.', 'info')
        return redirect(url_for('student.complaint_detail', ticket_number=ticket_number))
    
    form = FeedbackForm()
    if form.validate_on_submit():
        feedback = Feedback(
            complaint_id=complaint.id,
            student_id=current_user.id,
            rating=form.rating.data,
            feedback_text=form.feedback_text.data
        )
        db.session.add(feedback)
        log_audit(current_user.id, 'feedback', 'complaint', complaint.id, f'Rating: {form.rating.data}/5')
        db.session.commit()
        flash('Thank you for your feedback!', 'success')
    
    return redirect(url_for('student.complaint_detail', ticket_number=ticket_number))


@student_bp.route('/notifications')
@login_required
@student_required
def notifications():
    page = request.args.get('page', 1, type=int)
    notifs = Notification.query.filter_by(recipient_id=current_user.id).order_by(desc(Notification.created_at)).paginate(page=page, per_page=20, error_out=False)
    return render_template('student/notifications.html', notifications=notifs)


@student_bp.route('/notifications/read/<int:notif_id>', methods=['POST'])
@login_required
@student_required
def mark_notification_read(notif_id):
    notif = Notification.query.filter_by(id=notif_id, recipient_id=current_user.id).first_or_404()
    notif.is_read = True
    db.session.commit()
    return jsonify({'success': True})


@student_bp.route('/notifications/read-all', methods=['POST'])
@login_required
@student_required
def mark_all_notifications_read():
    Notification.query.filter_by(recipient_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    return jsonify({'success': True})


def generate_ticket_number():
    year = datetime.utcnow().year
    count = Complaint.query.filter(Complaint.ticket_number.like(f'CR-{year}-%')).count() + 1
    return f'CR-{year}-{count:04d}'


def save_attachment(file_storage, complaint_id):
    from werkzeug.utils import secure_filename
    from flask import current_app
    import os
    
    filename = secure_filename(file_storage.filename)
    if not filename:
        return None
    
    ext = filename.rsplit('.', 1)[1].lower()
    if ext not in current_app.config['ALLOWED_EXTENSIONS']:
        return None
    
    stored_name = f"{complaint_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{filename}"
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