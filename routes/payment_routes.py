"""
Payments Controller
Unified transactions, payment receipts, and collection breakdown (Cash, UPI, Card, EMI).
"""
from flask import Blueprint, render_template, request
from sqlalchemy import func
from models import db, Invoice, EMIInstallment, EMIAccount, RepairTicket
from routes.auth_routes import login_required, roles_accepted

payment_bp = Blueprint('payments', __name__, url_prefix='/payments')

@payment_bp.route('/')
@login_required
@roles_accepted('admin', 'cashier')
def payments_list():
    # 1. Total Collections
    total_invoice_payments = db.session.query(func.sum(Invoice.final_total)).filter_by(payment_status='Paid').scalar() or 0.0
    total_emi_collected = db.session.query(func.sum(EMIInstallment.amount + EMIInstallment.fine_amount)).filter_by(status='paid').scalar() or 0.0
    
    # 2. Method breakdown from Invoices
    cash_total = db.session.query(func.sum(Invoice.final_total)).filter(Invoice.payment_mode.ilike('%cash%')).scalar() or 0.0
    upi_total = db.session.query(func.sum(Invoice.final_total)).filter(Invoice.payment_mode.ilike('%upi%')).scalar() or 0.0
    card_total = db.session.query(func.sum(Invoice.final_total)).filter(Invoice.payment_mode.ilike('%card%')).scalar() or 0.0

    # 3. Recent Transactions
    recent_invoices = Invoice.query.order_by(Invoice.created_at.desc()).limit(20).all()
    paid_installments = EMIInstallment.query.join(EMIAccount).filter(
        EMIInstallment.status == 'paid'
    ).order_by(EMIInstallment.payment_date.desc()).limit(10).all()

    return render_template(
        'payments/index.html',
        total_collections=round(total_invoice_payments + total_emi_collected, 2),
        cash_total=round(cash_total, 2),
        upi_total=round(upi_total, 2),
        card_total=round(card_total, 2),
        emi_collected=round(total_emi_collected, 2),
        recent_invoices=recent_invoices,
        paid_installments=paid_installments
    )
