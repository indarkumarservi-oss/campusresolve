from flask import Blueprint, redirect, url_for, flash, session, current_app
from flask_login import login_user, current_user
from flask_dance.contrib.google import make_google_blueprint, google
from app.extensions import db
from app.models.models import User

oauth_bp = Blueprint('oauth', __name__, url_prefix='/oauth')

google_bp = make_google_blueprint(
    client_id=current_app.config.get('GOOGLE_CLIENT_ID') if current_app else None,
    client_secret=current_app.config.get('GOOGLE_CLIENT_SECRET') if current_app else None,
    scope=['openid', 'https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile'],
    redirect_to='oauth.google_callback'
)

@oauth_bp.route('/google')
def google_login():
    if not google.authorized:
        return redirect(url_for('google.login'))
    return redirect(url_for('oauth.google_callback'))

@oauth_bp.route('/google/callback')
def google_callback():
    if not google.authorized:
        flash('Google login failed. Please try again.', 'danger')
        return redirect(url_for('auth.login'))
    
    resp = google.get('/oauth2/v2/userinfo')
    if not resp.ok:
        flash('Failed to get user info from Google.', 'danger')
        return redirect(url_for('auth.login'))
    
    user_info = resp.json()
    google_id = user_info.get('id')
    email = user_info.get('email', '').lower()
    full_name = user_info.get('name', '')
    picture = user_info.get('picture', '')
    
    if not email:
        flash('Email not provided by Google.', 'danger')
        return redirect(url_for('auth.login'))
    
    user = User.query.filter_by(google_id=google_id).first()
    
    if not user:
        user = User.query.filter_by(email=email).first()
        if user:
            user.google_id = google_id
            db.session.commit()
    
    if not user:
        session['google_user'] = {
            'google_id': google_id,
            'email': email,
            'full_name': full_name,
            'picture': picture
        }
        return redirect(url_for('auth.complete_registration'))
    
    if not user.is_active:
        flash('Your account has been deactivated. Please contact administrator.', 'danger')
        return redirect(url_for('auth.login'))
    
    login_user(user, remember=True)
    flash(f'Welcome back, {user.full_name}!', 'success')
    return redirect(url_for('dashboard_redirect'))

@oauth_bp.route('/unlink-google')
def unlink_google():
    if current_user.is_authenticated and current_user.google_id:
        current_user.google_id = None
        db.session.commit()
        flash('Google account unlinked.', 'success')
    return redirect(url_for('student.dashboard') if current_user.is_student() else url_for('admin.dashboard'))