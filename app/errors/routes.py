from flask import Blueprint, render_template

errors_bp = Blueprint('errors', __name__)


@errors_bp.route('/forbidden')
def forbidden():
    return render_template('errors/403.html'), 403


@errors_bp.route('/not-found')
def not_found():
    return render_template('errors/404.html'), 404


@errors_bp.route('/server-error')
def server_error():
    return render_template('errors/500.html'), 500