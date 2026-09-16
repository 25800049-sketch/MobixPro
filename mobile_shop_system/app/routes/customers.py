from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import db, Customer, Bill, EMI, Repair, Exchange
from datetime import datetime
import datetime as dt

bp = Blueprint('customers', __name__)

@bp.route('/customers')
@login_required
def customer_list():
    customers = Customer.query.filter_by(is_active=True).order_by(Customer.created_at.desc()).all()
    return render_template('customers.html', customers=customers)

@bp.route('/customers/add', methods=['POST'])
@login_required
def add_customer():
    from app.models import Customer
    code = request.form.get('customer_code')
    if Customer.query.filter_by(customer_code=code).first():
        flash('Customer code already exists', 'danger')
        return redirect(url_for('customers.customer_list'))
    c = Customer(
        customer_code=code, first_name=request.form.get('first_name'),
        last_name=request.form.get('last_name'), email=request.form.get('email'),
        phone=request.form.get('phone'), alternate_phone=request.form.get('alt_phone'),
        address=request.form.get('address'), city=request.form.get('city'),
        state=request.form.get('state'), pincode=request.form.get('pincode'),
        gst_number=request.form.get('gst')
    )
    db.session.add(c)
    db.session.commit()
    flash('Customer added successfully', 'success')
    return redirect(url_for('customers.customer_list'))

@bp.route('/customers/edit/<int:id>', methods=['POST'])
@login_required
def edit_customer(id):
    c = Customer.query.get_or_404(id)
    c.first_name = request.form.get('first_name')
    c.last_name = request.form.get('last_name')
    c.email = request.form.get('email')
    c.phone = request.form.get('phone')
    c.alternate_phone = request.form.get('alt_phone')
    c.address = request.form.get('address')
    c.city = request.form.get('city')
    c.state = request.form.get('state')
    c.pincode = request.form.get('pincode')
    c.gst_number = request.form.get('gst')
    db.session.commit()
    flash('Customer updated', 'success')
    return redirect(url_for('customers.customer_list'))

@bp.route('/customers/delete/<int:id>')
@login_required
def delete_customer(id):
    c = Customer.query.get_or_404(id)
    c.is_active = False
    db.session.commit()
    flash('Customer deactivated', 'info')
    return redirect(url_for('customers.customer_list'))

@bp.route('/customers/view/<int:id>')
@login_required
def customer_view(id):
    c = Customer.query.get_or_404(id)
    bills = Bill.query.filter_by(customer_id=id).order_by(Bill.created_at.desc()).limit(20).all()
    emis = EMI.query.filter_by(customer_id=id).order_by(EMI.created_at.desc()).all()
    repairs = Repair.query.filter_by(customer_id=id).order_by(Repair.created_at.desc()).all()
    exchanges = Exchange.query.filter_by(customer_id=id).order_by(Exchange.created_at.desc()).all()
    return render_template('customer_view.html', customer=c, bills=bills, emis=emis, repairs=repairs, exchanges=exchanges)