"""
EMI Management & Auto-Fine Engine
Handles EMI schedule creation, monthly installment tracking,
automatic overdue identification, and late penalty fine calculations.
"""
from datetime import date, datetime, timedelta
from config import Config
from models import db, EMIAccount, EMIInstallment, Customer

def add_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, 28) # safe calendar day
    return date(year, month, day)

def create_emi_schedule(invoice_id, customer_id, total_amount, down_payment, tenure_months, fine_per_cycle=200.0, notes=None):
    """
    Creates an EMI account and calculates monthly installment breakdown.
    Example: Total = 30,000, Down = 6,000 -> Remaining = 24,000
    Tenure = 6 months -> EMI = 4,000/month
    """
    remaining_principal = float(total_amount) - float(down_payment)
    if remaining_principal <= 0:
        raise ValueError("Down payment cannot be greater than or equal to total amount for EMI.")

    emi_monthly = round(remaining_principal / int(tenure_months), 2)

    emi_acc = EMIAccount(
        invoice_id=invoice_id,
        customer_id=customer_id,
        total_amount=total_amount,
        down_payment=down_payment,
        principal_remaining=remaining_principal,
        emi_amount=emi_monthly,
        tenure_months=tenure_months,
        fine_per_cycle=fine_per_cycle,
        start_date=date.today(),
        status='Active',
        notes=notes
    )
    db.session.add(emi_acc)
    db.session.flush() # get emi_acc.id

    # Create monthly installments
    today = date.today()
    for month_idx in range(1, tenure_months + 1):
        due_d = add_months(today, month_idx)
        inst = EMIInstallment(
            emi_account_id=emi_acc.id,
            installment_no=month_idx,
            due_date=due_d,
            amount=emi_monthly,
            fine_amount=0.0,
            paid_amount=0.0,
            status='pending'
        )
        db.session.add(inst)

    # Update customer outstanding balance
    cust = db.session.get(Customer, customer_id)
    if cust:
        cust.outstanding_balance = (cust.outstanding_balance or 0.0) + remaining_principal

    db.session.commit()
    return emi_acc

def refresh_all_overdue_emis(fine_default=200.0):
    """
    Scans all active EMI installments.
    If due_date < today and status == 'pending':
      - mark status as 'overdue'
      - apply fine_per_cycle (default ₹200) if not already applied
    Updates parent EMI account status and returns count of updated items.
    """
    today = date.today()
    overdue_count = 0
    
    installments = EMIInstallment.query.filter(
        EMIInstallment.status.in_(['pending', 'overdue']),
        EMIInstallment.due_date < today
    ).all()

    for inst in installments:
        account = inst.account
        account_fine = account.fine_per_cycle if account else fine_default
        
        if inst.status != 'overdue' or inst.fine_amount == 0:
            inst.status = 'overdue'
            if inst.fine_amount == 0:
                inst.fine_amount = account_fine
                # Also adjust customer outstanding balance with the fine
                if account and account.customer:
                    account.customer.outstanding_balance += account_fine
            overdue_count += 1
            
        if account:
            account.status = 'Overdue'

    db.session.commit()
    return overdue_count

import json
import uuid
from config import Config

def pay_installment(installment_id, paid_amount, payment_mode='UPI'):
    """
    Records payment for an installment, clears overdue status if satisfied,
    and updates remaining EMI account balance.
    """
    inst = db.session.get(EMIInstallment, installment_id)
    if not inst:
        return False, "Installment not found"

    account = inst.account
    total_needed = (inst.amount + inst.fine_amount) - inst.paid_amount
    
    amount_to_pay = min(float(paid_amount), total_needed)
    inst.paid_amount += amount_to_pay
    inst.payment_date = date.today()
    inst.payment_mode = payment_mode

    if inst.paid_amount >= (inst.amount + inst.fine_amount):
        inst.status = 'paid'

    # Deduct from customer's outstanding balance
    if account and account.customer:
        account.customer.outstanding_balance = max(0.0, account.customer.outstanding_balance - amount_to_pay)
        account.principal_remaining = max(0.0, account.principal_remaining - min(amount_to_pay, inst.amount))

    # Check if all installments for account are paid
    account.update_status()

    db.session.commit()
    return True, "Payment recorded successfully"


def calculate_customer_credit_score(customer_id):
    """Calculates customer CIBIL-style credit score and risk tier."""
    customer = db.session.get(Customer, customer_id)
    if not customer:
        return {
            'score': 700,
            'tier': 'Tier-B',
            'tier_label': 'Moderate Risk (New Customer)',
            'badge_class': 'badge-warning',
            'max_recommended_emi': 50000.0,
            'down_payment_min_pct': 25
        }
    return customer.get_credit_profile()

