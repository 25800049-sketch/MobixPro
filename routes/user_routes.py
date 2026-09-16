"""
User & Staff Management Controller
Admin control for store staff, cashiers, and technicians.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, User
from routes.auth_routes import login_required, roles_accepted

user_bp = Blueprint('users', __name__, url_prefix='/users')

@user_bp.route('/')
@login_required
@roles_accepted('admin')
def users_list():
    users = User.query.order_by(User.role, User.full_name).all()
    return render_template('users/index.html', users=users)

@user_bp.route('/add', methods=['POST'])
@login_required
@roles_accepted('admin')
def add_user():
    username = request.form.get('username', '').strip()
    full_name = request.form.get('full_name', '').strip()
    role = request.form.get('role', 'cashier').strip()
    email = request.form.get('email', '').strip()
    phone = request.form.get('phone', '').strip()
    password = request.form.get('password', '').strip()

    if not username or not password or not full_name:
        flash('Username, Full Name, and Password are required.', 'danger')
        return redirect(url_for('users.users_list'))

    if User.query.filter_by(username=username).first():
        flash(f'Username "{username}" is already taken.', 'danger')
        return redirect(url_for('users.users_list'))

    new_user = User(
        username=username,
        full_name=full_name,
        role=role,
        email=email,
        phone=phone
    )
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    flash(f'Staff member {full_name} ({role.capitalize()}) registered successfully!', 'success')
    return redirect(url_for('users.users_list'))

@user_bp.route('/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@roles_accepted('admin')
def toggle_status(user_id):
    user = db.session.get(User, user_id)
    if user:
        if user.username == 'admin':
            flash('Default admin user cannot be deactivated.', 'danger')
        else:
            user.is_active = not user.is_active
            db.session.commit()
            status_text = 'activated' if user.is_active else 'deactivated'
            flash(f'User {user.full_name} has been {status_text}.', 'info')
    return redirect(url_for('users.users_list'))
