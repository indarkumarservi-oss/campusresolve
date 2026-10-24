from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.ai.ai_utils import get_ai_suggestions, verify_verification_token, find_duplicates
from app.models.models import Notification, Complaint
from app.forms import AIRequestForm

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/ai/suggest', methods=['POST'])
@login_required
def ai_suggest():
    form = AIRequestForm()
    if form.validate_on_submit():
        result = get_ai_suggestions(form.title.data, form.description.data)
        return jsonify(result)
    return jsonify({'error': 'Invalid input', 'details': form.errors}), 400


@api_bp.route('/ai/verify', methods=['POST'])
@login_required
def ai_verify():
    """Verify a previously generated AI verification token."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid JSON'}), 400
    
    token = data.get('token')
    title = data.get('title')
    description = data.get('description')
    
    if not token or not title or not description:
        return jsonify({'error': 'Missing required fields'}), 400
    
    result = verify_verification_token(token, title, description)
    return jsonify(result)


@api_bp.route('/complaints/<ticket_number>/duplicates', methods=['GET'])
@login_required
def check_duplicates(ticket_number):
    """Check for potential duplicate complaints."""
    complaint = Complaint.query.filter_by(ticket_number=ticket_number).first_or_404()
    
    # Check permissions
    if current_user.is_student() and complaint.student_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    duplicates = find_duplicates(complaint, threshold=0.7)
    return jsonify({'duplicates': duplicates})


@api_bp.route('/notifications/read/<int:notif_id>', methods=['POST'])
@login_required
def mark_notification_read(notif_id):
    notif = Notification.query.filter_by(id=notif_id, recipient_id=current_user.id).first_or_404()
    notif.is_read = True
    db.session.commit()
    return jsonify({'success': True})


@api_bp.route('/notifications/read-all', methods=['POST'])
@login_required
def mark_all_notifications_read():
    Notification.query.filter_by(recipient_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    return jsonify({'success': True})


@api_bp.route('/notifications/unread-count')
@login_required
def unread_count():
    count = Notification.query.filter_by(recipient_id=current_user.id, is_read=False).count()
    return jsonify({'count': count})