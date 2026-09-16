"""
Customer Relationship Management Controller
Handles Customer records, 360-degree timeline (Purchases, EMIs, Repairs),
and outstanding balance tracking.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import db, Customer
from routes.auth_routes import login_required, roles_accepted

customer_bp = Blueprint('customers', __name__, url_prefix='/customers')

@customer_bp.route('/')
@login_required
@roles_accepted('admin', 'cashier')
def customer_list():
    query = request.args.get('q', '').strip()
    customers_q = Customer.query
    if query:
        customers_q = customers_q.filter(
            (Customer.name.ilike(f'%{query}%')) |
            (Customer.phone.ilike(f'%{query}%')) |
            (Customer.email.ilike(f'%{query}%'))
        )
    customers = customers_q.order_by(Customer.created_at.desc()).all()
    return render_template('customers/customer_list.html', customers=customers, q=query)

@customer_bp.route('/add', methods=['POST'])
@login_required
@roles_accepted('admin', 'cashier')
def add_customer():
    name = request.form.get('name', '').strip()
    phone = request.form.get('phone', '').strip()
    email = request.form.get('email', '').strip()
    address = request.form.get('address', '').strip()

    if not name or not phone:
        flash("Customer name and phone number are required.", "danger")
        return redirect(url_for('customers.customer_list'))

    existing = Customer.query.filter_by(phone=phone).first()
    if existing:
        flash(f"Customer with phone {phone} already exists ({existing.name}).", "warning")
        return redirect(url_for('customers.customer_detail', customer_id=existing.id))

    customer = Customer(name=name, phone=phone, email=email or None, address=address or None)
    db.session.add(customer)
    db.session.commit()
    flash(f"Customer '{name}' registered successfully.", "success")
    return redirect(url_for('customers.customer_list'))

@customer_bp.route('/<int:customer_id>')
@login_required
@roles_accepted('admin', 'cashier')
def customer_detail(customer_id):
    customer = db.session.get(Customer, customer_id)
    if not customer:
        flash("Customer record not found.", "danger")
        return redirect(url_for('customers.customer_list'))

    return render_template('customers/customer_detail.html', customer=customer)

@customer_bp.route('/<int:customer_id>/edit', methods=['POST'])
@login_required
@roles_accepted('admin', 'cashier')
def edit_customer(customer_id):
    customer = db.session.get(Customer, customer_id)
    if not customer:
        flash("Customer not found.", "danger")
        return redirect(url_for('customers.customer_list'))

    customer.name = request.form.get('name', customer.name)
    customer.phone = request.form.get('phone', customer.phone)
    customer.email = request.form.get('email', customer.email)
    customer.address = request.form.get('address', customer.address)
    db.session.commit()
    flash("Customer profile updated.", "success")
    return redirect(url_for('customers.customer_detail', customer_id=customer.id))

@customer_bp.route('/api/add', methods=['POST'])
@login_required
@roles_accepted('admin', 'cashier')
def api_add_customer():
    data = request.get_json() or request.form
    name = (data.get('name') or '').strip()
    phone = (data.get('phone') or '').strip()
    email = (data.get('email') or '').strip()
    address = (data.get('address') or '').strip()

    if not name or not phone:
        return jsonify({'success': False, 'message': 'Customer name and phone number are required.'}), 400

    existing = Customer.query.filter_by(phone=phone).first()
    if existing:
        if name and name != 'Valued Customer':
            existing.name = name
        if email:
            existing.email = email
        if address:
            existing.address = address
        db.session.commit()
        return jsonify({
            'success': True,
            'is_existing': True,
            'message': f"Customer with phone {phone} already registered. Selected '{existing.name}'.",
            'customer': existing.to_dict()
        })

    customer = Customer(
        name=name,
        phone=phone,
        email=email or None,
        address=address or None
    )
    db.session.add(customer)
    db.session.commit()
    return jsonify({
        'success': True,
        'is_existing': False,
        'message': f"Customer '{customer.name}' registered successfully!",
        'customer': customer.to_dict()
    })

@customer_bp.route('/api/lookup')
@login_required
@roles_accepted('admin', 'cashier')
def api_lookup_customer():
    phone = (request.args.get('phone') or '').strip()
    if not phone or len(phone) < 3:
        return jsonify({'found': False})
    
    customer = Customer.query.filter(Customer.phone.ilike(f"%{phone}%")).first()
    if customer:
        return jsonify({'found': True, 'customer': customer.to_dict()})
    return jsonify({'found': False})
