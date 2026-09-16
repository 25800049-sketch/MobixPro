from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.models import db, Bill, BillItem, Customer, Product, Payment, EMI, Category, Supplier, Exchange
from datetime import datetime, timedelta
import uuid

bp = Blueprint('billing', __name__)

@bp.route('/billing')
@login_required
def billing_list():
    bills = Bill.query.order_by(Bill.created_at.desc()).limit(50).all()
    return render_template('billing.html', bills=bills)

@bp.route('/billing/new')
@login_required
def new_bill():
    customers = Customer.query.filter_by(is_active=True).all()
    products = Product.query.filter_by(is_active=True).all()
    categories = Category.query.filter_by(is_active=True).all()
    return render_template('new_bill.html', customers=customers, products=products, categories=categories)

@bp.route('/billing/create', methods=['POST'])
@login_required
def create_bill():
    from app.models import Bill, BillItem, Payment, EMI, Customer
    customer_id = int(request.form.get('customer_id'))
    payment_mode = request.form.get('payment_mode', 'cash')
    emi_months = int(request.form.get('emi_months', 0))
    discount = float(request.form.get('discount', 0))
    items = request.form.getlist('items[]')
    
    c = Customer.query.get_or_404(customer_id)
    bill_no = f"INV-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    
    subtotal = 0
    tax_amount = 0
    
    bill = Bill(
        bill_number=bill_no, customer_id=customer_id,
        user_id=current_user.id, bill_type='sale',
        payment_mode=payment_mode, discount=discount,
        emi_months=emi_months,
        emi_interest_rate=12.0 if emi_months > 0 else 0
    )
    
    if emi_months > 0:
        bill.payment_status = 'emi'
    else:
        bill.payment_status = 'pending' if payment_mode != 'cash' else 'pending'
    
    db.session.add(bill)
    
    for item_data in items:
        if not item_data:
            continue
        data = item_data.split(',')
        product_id = int(data[0])
        qty = int(data[1])
        p = Product.query.get(product_id)
        if not p or p.quantity_in_stock < qty:
            continue
        item_total = p.selling_price * qty
        tax = item_total * (p.tax_percentage / 100)
        subtotal += item_total
        tax_amount += tax
        
        p.quantity_in_stock -= qty
        
        item = BillItem(
            bill_id=bill.id, product_id=product_id,
            quantity=qty, unit_price=p.selling_price,
            tax_percentage=p.tax_percentage, total_price=item_total
        )
        db.session.add(item)
    
    bill.subtotal = subtotal
    bill.tax_amount = tax_amount
    bill.total_amount = subtotal + tax_amount - discount
    bill.balance_amount = bill.total_amount
    bill.paid_amount = bill.total_amount if payment_mode == 'cash' else 0
    
    if payment_mode == 'cash' and bill.total_amount > 0:
        pay = Payment(bill_id=bill.id, customer_id=customer_id, amount=bill.total_amount, payment_mode='cash')
        bill.paid_amount = bill.total_amount
        bill.balance_amount = 0
        bill.payment_status = 'paid'
        db.session.add(pay)
    
    if emi_months > 0:
        total_after_discount = bill.total_amount
        principal = total_after_discount
        per_month = round(total_after_discount / emi_months, 2)
        for m in range(1, emi_months + 1):
            due_date = datetime.utcnow().date() + timedelta(days=30 * m)
            emi = EMI(
                emi_number=f"EMI-{bill.id}-{m}", bill_id=bill.id,
                customer_id=customer_id, emi_month=m,
                due_date=due_date, principal_amount=per_month,
                interest_amount=round(per_month * bill.emi_interest_rate / 100, 2),
                total_amount=round(per_month + (per_month * bill.emi_interest_rate / 100), 2)
            )
            db.session.add(emi)
        bill.payment_status = 'emi'
    
    db.session.commit()
    
    if emi_months > 0:
        flash(f'Bill {bill_no} created with {emi_months}-month EMI', 'success')
    else:
        flash(f'Bill {bill_no} created successfully', 'success')
    
    return redirect(url_for('billing.bill_view', bill_id=bill.id))

@bp.route('/billing/view/<int:bill_id>')
@login_required
def bill_view(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    items = BillItem.query.filter_by(bill_id=bill_id).all()
    payments = Payment.query.filter_by(bill_id=bill_id).all()
    emis = EMI.query.filter_by(bill_id=bill_id).all()
    return render_template('bill_view.html', bill=bill, items=items, payments=payments, emis=emis)

@bp.route('/billing/pay', methods=['POST'])
@login_required
def bill_payment():
    from app.models import Bill, Payment
    bill_id = int(request.form.get('bill_id'))
    amount = float(request.form.get('amount'))
    payment_mode = request.form.get('payment_mode', 'cash')
    bill = Bill.query.get_or_404(bill_id)
    
    pay = Payment(bill_id=bill_id, customer_id=bill.customer_id, amount=amount, payment_mode=payment_mode)
    bill.paid_amount += amount
    bill.balance_amount = bill.total_amount - bill.paid_amount
    bill.payment_status = 'paid' if bill.balance_amount <= 0 else 'partial'
    db.session.add(pay)
    db.session.commit()
    flash('Payment recorded', 'success')
    return redirect(url_for('billing.bill_view', bill_id=bill_id))

@bp.route('/billing/cashier')
@login_required
def cashier_pos():
    customers = Customer.query.filter_by(is_active=True).all()
    products = Product.query.filter_by(is_active=True).all()
    return render_template('pos.html', customers=customers, products=products)