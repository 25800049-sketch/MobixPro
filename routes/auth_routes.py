"""
Authentication and Role-Based Access Control (RBAC)
Supports Admin, Cashier, and Technician roles.
"""
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g
from models import db, User

auth_bp = Blueprint('auth', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def roles_accepted(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('auth.login'))
            user_role = session.get('role', '')
            if user_role not in roles and 'admin' != user_role:
                flash(f"Access Denied: Your role '{user_role.capitalize()}' does not have permission for this action.", "danger")
                return redirect(url_for('dashboard.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        role = session.get('role')
        if role == 'technician':
            return redirect(url_for('repairs.repair_list'))
        elif role == 'cashier':
            return redirect(url_for('pos.billing'))
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        user = User.query.filter((User.username == username) | (User.email == username)).first()
        if user and user.check_password(password):
            if not user.is_active:
                flash("Your account has been deactivated. Please contact administrator.", "danger")
                return render_template('login.html')

            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            session['full_name'] = user.full_name
            
            flash(f"Welcome back, {user.full_name}! Signed in as {user.role.capitalize()}.", "success")
            next_page = request.args.get('next')

            if user.role == 'technician':
                default_target = url_for('repairs.repair_list')
            elif user.role == 'cashier':
                default_target = url_for('pos.billing')
            else:
                default_target = url_for('dashboard.index')

            return redirect(next_page or default_target)
        else:
            flash("Invalid username or password. Please try again.", "danger")

    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    user_name = session.get('full_name', 'User')
    session.clear()
    flash(f"Successfully signed out. Have a productive day, {user_name}!", "info")
    return redirect(url_for('auth.login'))
