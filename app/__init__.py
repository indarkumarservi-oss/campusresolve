import os
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, send_from_directory, make_response
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename
from config import config
from app.extensions import db, login_manager, csrf
from app.models import User, Complaint, ComplaintAttachment, StatusHistory, ComplaintComment, Notification, Feedback, AuditLog


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')

    template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'templates')
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static')
    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    app.config.from_object(config[config_name])

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    from app.ai import get_ai_suggestions

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.context_processor
    def inject_globals():
        from app.services import get_sla_status
        return {
            'COMPLAINT_CATEGORIES': app.config['COMPLAINT_CATEGORIES'],
            'COMPLAINT_PRIORITIES': app.config['COMPLAINT_PRIORITIES'],
            'COMPLAINT_STATUSES': app.config['COMPLAINT_STATUSES'],
            'DEPARTMENTS': app.config['DEPARTMENTS'],
            'CATEGORY_DEPARTMENT_MAP': app.config['CATEGORY_DEPARTMENT_MAP'],
            'User': User,
            'get_sla_status': get_sla_status,
        }

    @app.template_filter('datetimeformat')
    def datetimeformat(value, format='%d %b %Y %H:%M'):
        if value is None:
            return ''
        return value.strftime(format)

    @app.template_filter('timeago')
    def timeago(value):
        if value is None:
            return ''
        now = datetime.utcnow()
        diff = now - value
        if diff.days > 0:
            return f'{diff.days} day{"s" if diff.days != 1 else ""} ago'
        hours = diff.seconds // 3600
        if hours > 0:
            return f'{hours} hour{"s" if hours != 1 else ""} ago'
        minutes = (diff.seconds % 3600) // 60
        if minutes > 0:
            return f'{minutes} min{"s" if minutes != 1 else ""} ago'
        return 'Just now'

    @app.template_filter('nl2br')
    def nl2br(value):
        if value is None:
            return ''
        from markupsafe import Markup
        return Markup(value.replace('\n', '<br>\n'))

    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

    def generate_ticket_number():
        year = datetime.utcnow().year
        count = Complaint.query.filter(Complaint.ticket_number.like(f'CR-{year}-%')).count() + 1
        return f'CR-{year}-{count:04d}'

    def log_audit(actor_id, action, entity_type, entity_id, details=None):
        log = AuditLog(actor_id=actor_id, action=action, entity_type=entity_type, entity_id=entity_id, details=details)
        db.session.add(log)

    def create_notification(recipient_id, title, message, complaint_id=None):
        notif = Notification(recipient_id=recipient_id, title=title, message=message, complaint_id=complaint_id)
        db.session.add(notif)

    def change_status(complaint, new_status, actor, note=None):
        old_status = complaint.status
        if old_status == new_status:
            return False
        complaint.status = new_status
        complaint.updated_at = datetime.utcnow()
        if new_status == 'Resolved':
            complaint.resolved_at = datetime.utcnow()
        elif new_status == 'Closed':
            complaint.closed_at = datetime.utcnow()
        history = StatusHistory(complaint_id=complaint.id, actor_id=actor.id, old_status=old_status, new_status=new_status, note=note)
        db.session.add(history)
        log_audit(actor.id, 'status_change', 'complaint', complaint.id, f'{old_status} -> {new_status}: {note or ""}')
        return True

    from app.auth.routes import auth_bp
    from app.student.routes import student_bp
    from app.staff.routes import staff_bp
    from app.admin.routes import admin_bp
    from app.api.routes import api_bp
    from app.oauth.routes import oauth_bp, google_bp
    from app.errors.routes import errors_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(staff_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(oauth_bp)
    app.register_blueprint(google_bp)
    app.register_blueprint(errors_bp)

    @app.route('/')
    def index():
        return render_template('public/home.html')

    @app.route('/uploads/<path:filename>')
    @login_required
    def uploaded_file(filename):
        complaint_id = request.args.get('complaint_id', type=int)
        attachment = ComplaintAttachment.query.filter_by(stored_filename=filename).first_or_404()
        complaint = attachment.complaint

        if current_user.is_student() and complaint.student_id != current_user.id:
            return redirect(url_for('errors.forbidden'))
        if current_user.is_staff() and complaint.assigned_staff_id != current_user.id and complaint.department != current_user.department:
            return redirect(url_for('errors.forbidden'))

        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        return render_template('errors/404.html'), 500

    with app.app_context():
        db.create_all()

    return app