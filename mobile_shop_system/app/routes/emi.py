from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.models import db, EMI, Bill, Customer
from datetime import datetime, timedelta

bp = Blueprint('emi', __name__)

@bp.route('/emi')
@login_required
def emi_list():
    emi_list = EMI.query.order_by(EMI.created_at.desc()).all()
    for e in emi_list:
        e.fine_amount = e.calculate_fine()
    return render_template('emi.html', emi_list=emi_list)

@bp.route('/emi/pay/<int:emi_id>', methods=['POST'])
@login_required
def emi_pay(emi_id):
    emi = EMI.query.get_or_404(emi_id)
    amount = float(request.form.get('amount', emi.total_amount))
    from app.models import Payment
    pay = Payment(bill_id=emi.bill_id, customer_id=emi.customer_id, amount=amount, payment_mode='emi')
    emi.paid_amount += amount
    emi.balance_amount = emi.total_amount - emi.paid_amount
    emi.status = 'paid' if emi.balance_amount <= 0 else 'partial'
    emi.paid_date = datetime.utcnow()
    emi.payment_id = pay.id
    db.session.add(pay)
    db.session.commit()
    flash('EMI payment recorded', 'success')
    return redirect(url_for('emi.emi_list'))

@bp.route('/emi/overdue')
@login_required
def emi_overdue():
    today = datetime.utcnow().date()
    overdue = EMI.query.filter(EMI.due_date < today, EMI.status.in_(['pending', 'partial'])).all()
    for e in overdue:
        e.fine_amount = e.calculate_fine()
    return render_template('emi_overdue.html', overdue=overdue)