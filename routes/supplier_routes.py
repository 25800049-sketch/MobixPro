"""
Supplier Management Controller
Tracks vendor registrations, inbound stock purchases, and outstanding dues.
"""
from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Supplier, SupplierPurchase
from routes.auth_routes import login_required, roles_accepted

supplier_bp = Blueprint('suppliers', __name__, url_prefix='/suppliers')

@supplier_bp.route('/')
@login_required
@roles_accepted('admin')
def supplier_list():
    query = request.args.get('q', '').strip()
    suppliers_q = Supplier.query
    if query:
        suppliers_q = suppliers_q.filter(
            (Supplier.name.ilike(f'%{query}%')) |
            (Supplier.company.ilike(f'%{query}%')) |
            (Supplier.phone.ilike(f'%{query}%'))
        )
    suppliers = suppliers_q.order_by(Supplier.created_at.desc()).all()
    recent_purchases = SupplierPurchase.query.order_by(SupplierPurchase.purchase_date.desc()).limit(10).all()

    total_dues = sum(s.balance_due for s in suppliers)
    return render_template('suppliers/supplier_list.html', suppliers=suppliers, recent_purchases=recent_purchases, total_dues=total_dues, q=query)

@supplier_bp.route('/add', methods=['POST'])
@login_required
@roles_accepted('admin')
def add_supplier():
    name = request.form.get('name', '').strip()
    company = request.form.get('company', '').strip()
    phone = request.form.get('phone', '').strip()
    email = request.form.get('email', '').strip()
    address = request.form.get('address', '').strip()

    if not name or not company or not phone:
        flash("Supplier name, company, and phone are required.", "danger")
        return redirect(url_for('suppliers.supplier_list'))

    supplier = Supplier(
        name=name,
        company=company,
        phone=phone,
        email=email or None,
        address=address or None
    )
    db.session.add(supplier)
    db.session.commit()
    flash(f"Supplier '{company}' added successfully.", "success")
    return redirect(url_for('suppliers.supplier_list'))

@supplier_bp.route('/purchase/add', methods=['POST'])
@login_required
@roles_accepted('admin')
def add_purchase():
    supplier_id = int(request.form.get('supplier_id'))
    supplier = db.session.get(Supplier, supplier_id)
    if not supplier:
        flash("Supplier not found.", "danger")
        return redirect(url_for('suppliers.supplier_list'))

    invoice_no = request.form.get('invoice_no', '').strip()
    total_amount = float(request.form.get('total_amount', 0))
    paid_amount = float(request.form.get('paid_amount', 0))
    notes = request.form.get('notes', '')

    balance = max(0.0, total_amount - paid_amount)
    status = 'Paid' if balance == 0 else ('Partial' if paid_amount > 0 else 'Pending')

    purchase = SupplierPurchase(
        supplier_id=supplier.id,
        invoice_no=invoice_no,
        total_amount=total_amount,
        paid_amount=paid_amount,
        status=status,
        notes=notes,
        purchase_date=date.today()
    )
    db.session.add(purchase)

    # Update supplier balance due
    supplier.balance_due += balance
    db.session.commit()

    flash(f"Purchase invoice #{invoice_no} recorded for {supplier.company}.", "success")
    return redirect(url_for('suppliers.supplier_list'))
