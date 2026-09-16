"""
Payroll & Attendance Controller
Handles daily staff attendance marking, salary advance records,
attendance-based salary computation, and printable payslip views.
"""
from datetime import date, datetime
import calendar
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, User, Attendance, SalaryAdvance, PayrollRecord
from routes.auth_routes import login_required, roles_accepted
from services.payroll_service import (
    compute_month_attendance,
    calculate_employee_salary,
    finalize_payroll,
    get_month_date_range
)

payroll_bp = Blueprint('payroll', __name__, url_prefix='/payroll')


@payroll_bp.route('/attendance', methods=['GET'])
@login_required
@roles_accepted('admin', 'cashier', 'technician')
def attendance_page():
    """Daily Attendance Register view. Read-only for Cashier & Technician; editable by Admin.
    - Cashier views only cashier attendance.
    - Technician views only technician attendance.
    - Admin manages Cashiers and Technicians (Admin does not have attendance).
    """
    date_str = request.args.get('date', date.today().strftime('%Y-%m-%d'))
    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        selected_date = date.today()
        date_str = selected_date.strftime('%Y-%m-%d')

    user_role = session.get('role')
    is_admin = (user_role == 'admin')
    role_filter = request.args.get('role_filter', '').strip()

    # Role-based attendance filtering:
    # 1. Cashier sees only cashiers
    # 2. Technician sees only technicians
    # 3. Admin does not have attendance; sees Cashiers and Technicians
    if user_role == 'cashier':
        users = User.query.filter_by(is_active=True, role='cashier').order_by(User.full_name).all()
    elif user_role == 'technician':
        users = User.query.filter_by(is_active=True, role='technician').order_by(User.full_name).all()
    else:
        # Admin view - excludes admin (admin does not have attendance)
        if role_filter in ['cashier', 'technician']:
            users = User.query.filter_by(is_active=True, role=role_filter).order_by(User.full_name).all()
        else:
            users = User.query.filter(
                User.is_active == True,
                User.role.in_(['cashier', 'technician'])
            ).order_by(User.role, User.full_name).all()

    user_ids = [u.id for u in users]

    # Existing attendance for selected_date restricted to shown users
    if user_ids:
        attendance_records = Attendance.query.filter(
            Attendance.date == selected_date,
            Attendance.user_id.in_(user_ids)
        ).all()
    else:
        attendance_records = []

    attendance_map = {rec.user_id: rec for rec in attendance_records}

    # Summary metrics for displayed staff on selected date
    present_cnt = sum(1 for rec in attendance_records if rec.status == 'present')
    half_day_cnt = sum(1 for rec in attendance_records if rec.status == 'half_day')
    absent_cnt = sum(1 for rec in attendance_records if rec.status == 'absent')
    leave_cnt = sum(1 for rec in attendance_records if rec.status == 'leave')

    # Total counts for admin role filter bar
    cashier_count = User.query.filter_by(is_active=True, role='cashier').count()
    technician_count = User.query.filter_by(is_active=True, role='technician').count()

    return render_template(
        'payroll/attendance.html',
        selected_date=selected_date,
        date_str=date_str,
        users=users,
        attendance_map=attendance_map,
        present_cnt=present_cnt,
        half_day_cnt=half_day_cnt,
        absent_cnt=absent_cnt,
        leave_cnt=leave_cnt,
        is_admin=is_admin,
        role_filter=role_filter,
        user_role=user_role,
        cashier_count=cashier_count,
        technician_count=technician_count
    )


@payroll_bp.route('/attendance/mark', methods=['POST'])
@login_required
@roles_accepted('admin')
def mark_attendance():
    """Bulk or single day attendance submission. Exclusive to Admin.
    Admin does not have attendance - only records attendance for Cashiers & Technicians.
    """
    date_str = request.form.get('date', date.today().strftime('%Y-%m-%d'))
    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        selected_date = date.today()
        date_str = selected_date.strftime('%Y-%m-%d')

    action = request.form.get('action')
    # Admin does NOT have attendance - only Cashiers and Technicians
    users = User.query.filter(
        User.is_active == True,
        User.role.in_(['cashier', 'technician'])
    ).all()

    if action == 'mark_all_present':
        for u in users:
            rec = Attendance.query.filter_by(user_id=u.id, date=selected_date).first()
            if not rec:
                rec = Attendance(user_id=u.id, date=selected_date)
                db.session.add(rec)
            rec.status = 'present'
        db.session.commit()
        flash(f'Marked all {len(users)} staff members (Cashiers & Technicians) as Present for {selected_date.strftime("%d-%b-%Y")}.', 'success')
        return redirect(url_for('payroll.attendance_page', date=date_str))

    # Standard form submission for each staff user (excluding admin)
    updated_count = 0
    for u in users:
        status_val = request.form.get(f'status_{u.id}')
        if status_val:
            rec = Attendance.query.filter_by(user_id=u.id, date=selected_date).first()
            if not rec:
                rec = Attendance(user_id=u.id, date=selected_date)
                db.session.add(rec)
            rec.status = status_val
            rec.check_in = request.form.get(f'check_in_{u.id}', '').strip() or None
            rec.check_out = request.form.get(f'check_out_{u.id}', '').strip() or None
            rec.notes = request.form.get(f'notes_{u.id}', '').strip() or None
            updated_count += 1

    db.session.commit()
    flash(f'Attendance recorded for {updated_count} staff members on {selected_date.strftime("%d-%b-%Y")}.', 'success')
    return redirect(url_for('payroll.attendance_page', date=date_str))


@payroll_bp.route('/salary', methods=['GET'])
@login_required
@roles_accepted('admin')
def salary_page():
    """Monthly Salary Calculation & Payroll Overview."""
    today = date.today()
    month = int(request.args.get('month', today.month))
    year = int(request.args.get('year', today.year))
    working_days = int(request.args.get('working_days', 26))

    users = User.query.filter_by(is_active=True).order_by(User.role, User.full_name).all()

    # Calculate salary breakdown for every staff member
    payroll_summaries = []
    total_payroll_cost = 0.0
    total_advances_deducted = 0.0

    for u in users:
        calc = calculate_employee_salary(
            user_id=u.id,
            year=year,
            month=month,
            total_working_days=working_days
        )
        payroll_summaries.append(calc)
        total_payroll_cost += calc['net_salary']
        total_advances_deducted += calc['advances_deducted']

    # Fetch recent finalized payroll records
    month_str = f"{year:04d}-{month:02d}"
    finalized_records = PayrollRecord.query.filter_by(month_year=month_str).all()

    # Fetch unsettled salary advances
    unsettled_advances = SalaryAdvance.query.filter_by(is_settled=False).order_by(SalaryAdvance.date.desc()).all()

    return render_template(
        'payroll/salary.html',
        month=month,
        year=year,
        working_days=working_days,
        month_name=calendar.month_name[month],
        users=users,
        payroll_summaries=payroll_summaries,
        total_payroll_cost=round(total_payroll_cost, 2),
        total_advances_deducted=round(total_advances_deducted, 2),
        finalized_records=finalized_records,
        unsettled_advances=unsettled_advances
    )


@payroll_bp.route('/generate', methods=['POST'])
@login_required
@roles_accepted('admin')
def generate_payroll():
    """Generate and finalize monthly payslip record for an employee."""
    user_id = int(request.form.get('user_id'))
    month = int(request.form.get('month', date.today().month))
    year = int(request.form.get('year', date.today().year))
    working_days = int(request.form.get('working_days', 26))
    bonus = float(request.form.get('bonus', 0.0) or 0.0)
    payment_method = request.form.get('payment_method', 'Cash')
    payment_status = request.form.get('payment_status', 'Paid')
    notes = request.form.get('notes', '').strip()

    user = db.session.get(User, user_id)
    if not user:
        flash('Staff user not found.', 'danger')
        return redirect(url_for('payroll.salary_page', month=month, year=year))

    record = finalize_payroll(
        user_id=user_id,
        year=year,
        month=month,
        total_working_days=working_days,
        bonus=bonus,
        payment_method=payment_method,
        payment_status=payment_status,
        notes=notes
    )

    flash(f"Generated Payslip for {user.full_name}! Net Salary: ₹{record.net_salary:,.2f}", "success")
    return redirect(url_for('payroll.payslip', record_id=record.id))


@payroll_bp.route('/payslip/<int:record_id>', methods=['GET'])
@login_required
@roles_accepted('admin', 'cashier')
def payslip(record_id):
    """View and print clean, branded payslip."""
    record = db.session.get(PayrollRecord, record_id)
    if not record:
        flash('Payroll record not found.', 'danger')
        return redirect(url_for('payroll.salary_page'))

    # Parse month and year from record.month_year (e.g. '2026-09')
    parts = record.month_year.split('-')
    year = int(parts[0])
    month = int(parts[1])
    month_name = calendar.month_name[month]

    return render_template(
        'payroll/payslip.html',
        record=record,
        year=year,
        month=month,
        month_name=month_name
    )


@payroll_bp.route('/advances/add', methods=['POST'])
@login_required
@roles_accepted('admin')
def add_advance():
    """Record salary advance paid to an employee."""
    user_id = int(request.form.get('user_id'))
    amount = float(request.form.get('amount', 0.0))
    reason = request.form.get('reason', '').strip()
    date_str = request.form.get('date', date.today().strftime('%Y-%m-%d'))

    try:
        adv_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        adv_date = date.today()

    user = db.session.get(User, user_id)
    if not user or amount <= 0:
        flash('Invalid staff member or amount.', 'danger')
        return redirect(url_for('payroll.salary_page'))

    advance = SalaryAdvance(
        user_id=user_id,
        amount=amount,
        date=adv_date,
        reason=reason,
        is_settled=False
    )
    db.session.add(advance)
    db.session.commit()

    flash(f'Recorded salary advance of ₹{amount:,.2f} for {user.full_name}.', 'success')
    return redirect(url_for('payroll.salary_page'))


@payroll_bp.route('/staff/<int:user_id>/salary-config', methods=['POST'])
@login_required
@roles_accepted('admin')
def update_salary_config(user_id):
    """Update base salary and rate configuration for a staff member."""
    user = db.session.get(User, user_id)
    if not user:
        flash('Staff user not found.', 'danger')
        return redirect(url_for('payroll.salary_page'))

    monthly_salary = float(request.form.get('monthly_salary', 18000.0) or 18000.0)
    salary_type = request.form.get('salary_type', 'monthly')
    daily_rate = float(request.form.get('daily_rate', 0.0) or 0.0)

    if daily_rate <= 0:
        daily_rate = round(monthly_salary / 26, 2)

    user.monthly_salary = monthly_salary
    user.salary_type = salary_type
    user.daily_rate = daily_rate
    db.session.commit()

    flash(f"Updated salary configuration for {user.full_name}: ₹{monthly_salary:,.2f}/mo (₹{daily_rate:,.2f}/day).", "success")
    return redirect(url_for('payroll.salary_page'))
