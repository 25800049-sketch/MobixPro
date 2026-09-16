"""
Payroll and Attendance Calculation Service
Handles attendance aggregation, daily rate computation, salary advance deductions,
and monthly payroll/payslip generation.
"""
from datetime import date, datetime
import calendar
from models import db, User, Attendance, SalaryAdvance, PayrollRecord

def get_month_date_range(year: int, month: int):
    """Return start date and end date for a given year and month."""
    _, num_days = calendar.monthrange(year, month)
    start_date = date(year, month, 1)
    end_date = date(year, month, num_days)
    return start_date, end_date

def compute_month_attendance(user_id: int, year: int, month: int):
    """
    Summarize attendance counts and effective paid days for an employee in a given month.
    """
    start_date, end_date = get_month_date_range(year, month)
    
    records = Attendance.query.filter(
        Attendance.user_id == user_id,
        Attendance.date >= start_date,
        Attendance.date <= end_date
    ).all()

    present_count = 0.0
    half_day_count = 0
    leave_count = 0.0
    absent_count = 0

    for rec in records:
        status = (rec.status or '').lower()
        if status == 'present':
            present_count += 1.0
        elif status == 'half_day':
            half_day_count += 1
        elif status == 'leave':
            leave_count += 1.0
        elif status == 'absent':
            absent_count += 1

    effective_days = present_count + (half_day_count * 0.5) + leave_count

    return {
        'total_records_marked': len(records),
        'present_days': present_count,
        'half_days': half_day_count,
        'paid_leaves': leave_count,
        'absent_days': absent_count,
        'effective_days': round(effective_days, 1),
        'records': records
    }

def get_unsettled_advances(user_id: int, year: int, month: int):
    """
    Retrieve unsettled salary advances for this employee up to the end of the specified month.
    """
    _, end_date = get_month_date_range(year, month)
    advances = SalaryAdvance.query.filter(
        SalaryAdvance.user_id == user_id,
        SalaryAdvance.is_settled == False,
        SalaryAdvance.date <= end_date
    ).all()
    
    total_advance = sum(a.amount for a in advances)
    return round(total_advance, 2), advances

def calculate_employee_salary(user_id: int, year: int, month: int, total_working_days: int = 26, bonus: float = 0.0):
    """
    Calculate an employee's salary based on attendance for the given month.
    Formula:
      Daily Wage = Base Salary / Total Working Days (26)
      Effective Days = Full Present + (Half Days * 0.5) + Paid Leaves
      Earned Gross = Effective Days * Daily Wage
      Net Payable = Earned Gross + Bonus - Advances Taken
    """
    user = db.session.get(User, user_id)
    if not user:
        raise ValueError(f"User with ID {user_id} not found.")

    base_salary = float(user.monthly_salary or 18000.0)
    total_working_days = max(1, int(total_working_days))
    bonus = max(0.0, float(bonus))

    if getattr(user, 'salary_type', 'monthly') == 'daily_wage' and user.daily_rate:
        daily_rate = float(user.daily_rate)
    else:
        daily_rate = round(base_salary / total_working_days, 2)

    # 1. Attendance aggregation
    att_summary = compute_month_attendance(user_id, year, month)
    effective_days = att_summary['effective_days']

    # 2. Earned Gross
    earned_salary = round(effective_days * daily_rate, 2)

    # 3. Advances
    advances_amount, advance_objs = get_unsettled_advances(user_id, year, month)

    # 4. Net In-Hand
    net_salary = max(0.0, round(earned_salary + bonus - advances_amount, 2))

    month_str = f"{year:04d}-{month:02d}"

    # Check if a payroll record already exists
    existing_payroll = PayrollRecord.query.filter_by(user_id=user_id, month_year=month_str).first()

    return {
        'user': user,
        'user_id': user.id,
        'user_name': user.full_name,
        'role': user.role,
        'month_year': month_str,
        'year': year,
        'month': month,
        'month_name': calendar.month_name[month],
        'total_working_days': total_working_days,
        'present_days': att_summary['present_days'],
        'half_days': att_summary['half_days'],
        'paid_leaves': att_summary['paid_leaves'],
        'absent_days': att_summary['absent_days'],
        'effective_work_days': effective_days,
        'base_salary': base_salary,
        'daily_wage': daily_rate,
        'earned_salary': earned_salary,
        'bonus_incentive': bonus,
        'advances_deducted': advances_amount,
        'advances_list': advance_objs,
        'net_salary': net_salary,
        'existing_record': existing_payroll
    }

def finalize_payroll(user_id: int, year: int, month: int, total_working_days: int = 26,
                     bonus: float = 0.0, payment_method: str = 'Cash', payment_status: str = 'Paid', notes: str = ''):
    """
    Finalize and commit a monthly payroll record for an employee, marking associated advances as settled.
    """
    calc = calculate_employee_salary(user_id, year, month, total_working_days, bonus)
    month_str = calc['month_year']

    record = PayrollRecord.query.filter_by(user_id=user_id, month_year=month_str).first()
    if not record:
        record = PayrollRecord(
            user_id=user_id,
            month_year=month_str
        )
        db.session.add(record)

    record.total_working_days = calc['total_working_days']
    record.present_days = calc['present_days']
    record.half_days = calc['half_days']
    record.paid_leaves = calc['paid_leaves']
    record.effective_work_days = calc['effective_work_days']
    record.base_salary = calc['base_salary']
    record.daily_wage = calc['daily_wage']
    record.earned_salary = calc['earned_salary']
    record.bonus_incentive = calc['bonus_incentive']
    record.advances_deducted = calc['advances_deducted']
    record.net_salary = calc['net_salary']
    record.payment_status = payment_status
    record.payment_date = date.today()
    record.payment_method = payment_method
    record.notes = notes
    record.generated_at = datetime.utcnow()

    db.session.flush()

    # Mark all included advances as settled and link to this payroll record
    for adv in calc['advances_list']:
        adv.is_settled = True
        adv.payroll_record_id = record.id

    db.session.commit()
    return record
