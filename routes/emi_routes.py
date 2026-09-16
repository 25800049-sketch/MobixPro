"""
EMI Management Controller
Tracks customer EMI plans, overdue fines, payment collections, and payment history.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import db, EMIAccount, EMIInstallment, Customer
from routes.auth_routes import login_required, roles_accepted
from config import Config
from services.emi_service import (
    refresh_all_overdue_emis, pay_installment,
    calculate_customer_credit_score
)

emi_bp = Blueprint('emi', __name__, url_prefix='/emi')

@emi_bp.route('/')
@login_required
@roles_accepted('admin', 'cashier')
def emi_list():
    # Scan and refresh fines whenever viewing EMI page
    refresh_all_overdue_emis()

    status_filter = request.args.get('status', '').strip()
    query = request.args.get('q', '').strip()

    accounts_q = EMIAccount.query.join(Customer)
    if status_filter:
        accounts_q = accounts_q.filter(EMIAccount.status == status_filter)
    if query:
        accounts_q = accounts_q.filter(
            (Customer.name.ilike(f'%{query}%')) |
            (Customer.phone.ilike(f'%{query}%'))
        )

    accounts = accounts_q.order_by(EMIAccount.start_date.desc()).all()
    
    overdue_count = EMIAccount.query.filter_by(status='Overdue').count()
    active_count = EMIAccount.query.filter_by(status='Active').count()
    completed_count = EMIAccount.query.filter_by(status='Completed').count()

    # Pre-calculate credit profiles for badge rendering
    credit_profiles = {}
    for acc in accounts:
        if acc.customer:
            credit_profiles[acc.customer_id] = acc.customer.get_credit_profile()

    return render_template(
        'emi/emi_list.html',
        accounts=accounts,
        selected_status=status_filter,
        q=query,
        overdue_count=overdue_count,
        active_count=active_count,
        completed_count=completed_count,
        credit_profiles=credit_profiles
    )

@emi_bp.route('/<int:account_id>')
@login_required
@roles_accepted('admin', 'cashier')
def emi_detail(account_id):
    account = db.session.get(EMIAccount, account_id)
    if not account:
        flash("EMI Account not found.", "danger")
        return redirect(url_for('emi.emi_list'))

    refresh_all_overdue_emis()

    credit_profile = account.customer.get_credit_profile() if account.customer else None

    return render_template(
        'emi/emi_detail.html',
        account=account,
        credit_profile=credit_profile,
        config=Config
    )

@emi_bp.route('/api/customer-credit/<int:customer_id>')
@login_required
@roles_accepted('admin', 'cashier')
def get_customer_credit_api(customer_id):
    """JSON API for real-time POS credit evaluation."""
    profile = calculate_customer_credit_score(customer_id)
    return jsonify({'success': True, 'credit_profile': profile, 'profile': profile})

@emi_bp.route('/pay-installment/<int:installment_id>', methods=['POST'])
@login_required
@roles_accepted('admin', 'cashier')
def collect_payment(installment_id):
    amount = float(request.form.get('paid_amount', 0))
    payment_mode = request.form.get('payment_mode', 'UPI')
    
    success, msg = pay_installment(installment_id, amount, payment_mode)
    if success:
        flash(f"Payment of ₹{amount:,.2f} recorded successfully.", "success")
    else:
        flash(f"Failed to record payment: {msg}", "danger")

    installment = db.session.get(EMIInstallment, installment_id)
    if installment:
        return redirect(url_for('emi.emi_detail', account_id=installment.emi_account_id))
    return redirect(url_for('emi.emi_list'))

@emi_bp.route('/refresh-fines', methods=['POST'])
@login_required
@roles_accepted('admin', 'cashier')
def refresh_fines():
    updated = refresh_all_overdue_emis()
    flash(f"Scanned all active EMIs: {updated} overdue installment(s) identified and late fine applied.", "info")
    return redirect(url_for('emi.emi_list'))
