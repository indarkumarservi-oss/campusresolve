from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models.models import User, Notification
from app.forms import LoginForm, RegistrationForm, CompleteRegistrationForm, StaffRegistrationForm


def create_notification(recipient_id, title, message, complaint_id=None):
    notif = Notification(recipient_id=recipient_id, title=title, message=message, complaint_id=complaint_id)
    db.session.add(notif)

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('auth.dashboard_redirect'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash('Your account has been deactivated. Please contact administrator.', 'danger')
                return render_template('auth/login.html', form=form)
            if user.is_staff() and not user.is_approved:
                flash('Your account is pending admin approval. You cannot log in until approved.', 'warning')
                return render_template('auth/login.html', form=form)
            login_user(user, remember=form.remember_me.data)
            flash(f'Welcome back, {user.full_name}!', 'success')
            return redirect(url_for('auth.dashboard_redirect'))
        flash('Invalid email or password.', 'danger')
    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    from flask import current_app
    if not current_app.config.get('REGISTRATION_ENABLED', False):
        flash('Registration is currently disabled.', 'warning')
        return redirect(url_for('auth.login'))
    
    if current_user.is_authenticated:
        return redirect(url_for('auth.dashboard_redirect'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            full_name=form.full_name.data,
            email=form.email.data.lower(),
            role='student'
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form=form)


@auth_bp.route('/register-staff', methods=['GET', 'POST'])
def register_staff():
    from flask import current_app
    if not current_app.config.get('REGISTRATION_ENABLED', False):
        flash('Registration is currently disabled.', 'warning')
        return redirect(url_for('auth.login'))
    
    if current_user.is_authenticated:
        return redirect(url_for('auth.dashboard_redirect'))
    
    form = StaffRegistrationForm()
    if form.validate_on_submit():
        user = User(
            full_name=form.full_name.data,
            email=form.email.data.lower(),
            role='staff',
            department=form.department.data,
            usn=form.employee_id.data.upper(),
            phone=form.phone.data,
            address=form.address.data,
            profile_completed=True,
            is_approved=False  # Requires admin approval
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        
        # Notify all admins about the new staff registration request
        admins = User.query.filter_by(role='admin', is_active=True).all()
        for admin in admins:
            create_notification(
                admin.id,
                'New Staff Registration',
                f'Staff member {user.full_name} ({user.email}) has registered and is pending approval.',
                complaint_id=None
            )
        
        flash('Staff registration submitted! Your account is pending admin approval. You will be notified once approved.', 'info')
        return redirect(url_for('auth.login'))
    return render_template('auth/register_staff.html', form=form)


@auth_bp.route('/dashboard-redirect')
@login_required
def dashboard_redirect():
    if current_user.is_admin():
        return redirect(url_for('admin.dashboard'))
    elif current_user.is_staff():
        return redirect(url_for('staff.dashboard'))
    else:
        return redirect(url_for('student.dashboard'))

@auth_bp.route('/complete-registration', methods=['GET', 'POST'])
def complete_registration():
    google_data = session.get('google_user')
    if not google_data:
        flash('No Google account data found. Please log in with Google first.', 'warning')
        return redirect(url_for('auth.login'))
    
    form = CompleteRegistrationForm()
    if form.validate_on_submit():
        user = User(
            full_name=form.full_name.data,
            email=google_data['email'],
            google_id=google_data['google_id'],
            role='student',
            course=form.course.data,
            branch=form.branch.data,
            usn=form.usn.data.upper() if form.usn.data else None,
            phone=form.phone.data,
            address=form.address.data,
            profile_completed=True
        )
        if form.password.data:
            user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        session.pop('google_user', None)
        login_user(user, remember=True)
        flash('Registration completed successfully!', 'success')
        return redirect(url_for('auth.dashboard_redirect'))
    
    if request.method == 'GET':
        form.full_name.data = google_data.get('full_name', '')
    
    return render_template('auth/complete_registration.html', form=form, google_data=google_data)