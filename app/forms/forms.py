from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileSize
from wtforms import StringField, TextAreaField, SelectField, BooleanField, SubmitField, PasswordField, IntegerField, HiddenField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Optional, NumberRange
from app.models.models import User, Complaint
from config import Config


class CompleteRegistrationForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=120)])
    course = SelectField('Course', validators=[DataRequired()])
    branch = SelectField('Branch/Department', validators=[DataRequired()])
    usn = StringField('USN / Roll Number', validators=[DataRequired(), Length(min=3, max=50)])
    phone = StringField('Phone Number', validators=[Optional(), Length(max=20)])
    address = TextAreaField('Address', validators=[Optional(), Length(max=500)], render_kw={'rows': 3})
    password = PasswordField('Password (optional - leave blank to use Google login only)', validators=[Optional(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[Optional(), EqualTo('password', message='Passwords must match')])
    submit = SubmitField('Complete Registration')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.course.choices = [(c, c) for c in Config.COURSES]
        self.branch.choices = [(b, b) for b in Config.BRANCHES]
    
    def validate_usn(self, field):
        if User.query.filter_by(usn=field.data.upper()).first():
            raise ValidationError('USN/Roll Number already registered.')


class StaffRegistrationForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=120)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    department = SelectField('Department', validators=[DataRequired()])
    employee_id = StringField('Employee ID', validators=[DataRequired(), Length(min=3, max=50)])
    designation = StringField('Designation', validators=[DataRequired(), Length(min=2, max=100)])
    phone = StringField('Phone Number', validators=[Optional(), Length(max=20)])
    address = TextAreaField('Address', validators=[Optional(), Length(max=500)], render_kw={'rows': 3})
    submit = SubmitField('Register Staff')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.department.choices = [(d, d) for d in Config.DEPARTMENTS]
    
    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError('Email already registered.')
    
    def validate_employee_id(self, field):
        if User.query.filter_by(usn=field.data.upper()).first():
            raise ValidationError('Employee ID already registered.')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class RegistrationForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=120)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    course = SelectField('Course', validators=[DataRequired()])
    branch = SelectField('Branch/Department', validators=[DataRequired()])
    usn = StringField('USN / Roll Number', validators=[DataRequired(), Length(min=3, max=50)])
    phone = StringField('Phone Number', validators=[Optional(), Length(max=20)])
    address = TextAreaField('Address', validators=[Optional(), Length(max=500)], render_kw={'rows': 3})
    submit = SubmitField('Register')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.course.choices = [(c, c) for c in Config.COURSES]
        self.branch.choices = [(b, b) for b in Config.BRANCHES]
    
    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError('Email already registered.')
    
    def validate_usn(self, field):
        if User.query.filter_by(usn=field.data.upper()).first():
            raise ValidationError('USN/Roll Number already registered.')


class ComplaintForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(min=10, max=120)])
    description = TextAreaField('Description', validators=[DataRequired(), Length(min=20)], render_kw={'rows': 5})
    category = SelectField('Category', choices=[('', 'Select (or use AI suggestion)')], validators=[Optional()])
    priority = SelectField('Priority', choices=[('', 'Select (or use AI suggestion)')], validators=[Optional()])
    location = StringField('Location (e.g., Block A, Room 101)', validators=[Optional(), Length(max=200)])
    is_anonymous = BooleanField('Submit anonymously (name hidden from staff)')
    attachment = FileField('Attachment (PDF, PNG, JPG - max 5MB)', validators=[
        FileAllowed(Config.ALLOWED_EXTENSIONS, 'Only PDF, PNG, JPG files allowed'),
        FileSize(max_size=5 * 1024 * 1024, message='File must be less than 5MB')
    ])
    submit = SubmitField('Submit Complaint')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.category.choices += [(c, c) for c in Config.COMPLAINT_CATEGORIES]
        self.priority.choices += [(p, p) for p in Config.COMPLAINT_PRIORITIES]


class ComplaintCommentForm(FlaskForm):
    comment_text = TextAreaField('Comment', validators=[DataRequired(), Length(min=1, max=2000)], render_kw={'rows': 3})
    is_internal_note = BooleanField('Internal note (visible to staff/admin only)')
    submit = SubmitField('Post Comment')


class FeedbackForm(FlaskForm):
    rating = IntegerField('Rating (1-5)', validators=[DataRequired(), NumberRange(min=1, max=5)])
    feedback_text = TextAreaField('Feedback (optional)', validators=[Optional(), Length(max=2000)], render_kw={'rows': 4})
    submit = SubmitField('Submit Feedback')


class AdminComplaintEditForm(FlaskForm):
    category = SelectField('Category', validators=[DataRequired()])
    priority = SelectField('Priority', validators=[DataRequired()])
    department = SelectField('Department', validators=[DataRequired()])
    assigned_staff_id = SelectField('Assign Staff', coerce=int, validators=[Optional()])
    due_date = StringField('Due Date (YYYY-MM-DD)', validators=[Optional()])
    status = SelectField('Status', validators=[DataRequired()])
    is_duplicate = BooleanField('Mark as duplicate')
    parent_complaint_id = StringField('Parent Ticket Number', validators=[Optional()])
    submit = SubmitField('Update Complaint')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.category.choices = [(c, c) for c in Config.COMPLAINT_CATEGORIES]
        self.priority.choices = [(p, p) for p in Config.COMPLAINT_PRIORITIES]
        self.department.choices = [(d, d) for d in Config.DEPARTMENTS]
        self.status.choices = [(s, s) for s in Config.COMPLAINT_STATUSES]


class StaffStatusUpdateForm(FlaskForm):
    status = SelectField('Status', validators=[DataRequired()])
    note = TextAreaField('Action Note', validators=[Optional(), Length(max=2000)], render_kw={'rows': 3})
    evidence = FileField('Resolution Evidence (PDF, PNG, JPG - max 5MB)', validators=[
        FileAllowed(Config.ALLOWED_EXTENSIONS, 'Only PDF, PNG, JPG files allowed'),
        FileSize(max_size=5 * 1024 * 1024, message='File must be less than 5MB')
    ])
    submit = SubmitField('Update Status')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status.choices = [('In Progress', 'In Progress'), ('Pending Student Response', 'Pending Student Response'), ('Resolved', 'Resolved')]


class UserForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=120)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    role = SelectField('Role', choices=[('student', 'Student'), ('staff', 'Staff'), ('admin', 'Admin')], validators=[DataRequired()])
    department = StringField('Department (for staff)', validators=[Optional(), Length(max=100)])
    is_active = BooleanField('Active')
    password = PasswordField('New Password (leave blank to keep current)', validators=[Optional(), Length(min=8)])
    submit = SubmitField('Save User')
    
    def __init__(self, user_id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_id = user_id
    
    def validate_email(self, field):
        user = User.query.filter_by(email=field.data.lower()).first()
        if user and user.id != self.user_id:
            raise ValidationError('Email already registered.')


class ComplaintFilterForm(FlaskForm):
    search = StringField('Search', validators=[Optional(), Length(max=100)])
    status = SelectField('Status', choices=[('', 'All')], validators=[Optional()])
    category = SelectField('Category', choices=[('', 'All')], validators=[Optional()])
    priority = SelectField('Priority', choices=[('', 'All')], validators=[Optional()])
    department = SelectField('Department', choices=[('', 'All')], validators=[Optional()])
    date_from = StringField('From Date (YYYY-MM-DD)', validators=[Optional()])
    date_to = StringField('To Date (YYYY-MM-DD)', validators=[Optional()])
    show_duplicates = BooleanField('Show duplicates only')
    submit = SubmitField('Filter')
    export = SubmitField('Export CSV')
    clear = SubmitField('Clear')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.status.choices += [(s, s) for s in Config.COMPLAINT_STATUSES]
        self.category.choices += [(c, c) for c in Config.COMPLAINT_CATEGORIES]
        self.priority.choices += [(p, p) for p in Config.COMPLAINT_PRIORITIES]
        self.department.choices += [(d, d) for d in Config.DEPARTMENTS]


class AIRequestForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=120)])
    description = TextAreaField('Description', validators=[DataRequired()], render_kw={'rows': 4})
    submit = SubmitField('Get AI Suggestions')