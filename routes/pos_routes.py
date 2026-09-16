"""
Point of Sale (POS) & Billing Controller
Handles unified Mobile + Accessory cart, taxation, discounts, phone exchange deductions,
EMI plan activation, invoice generation, printable receipts, and PDF/Email/WhatsApp dispatch.
"""
import uuid
import threading
from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file, session, current_app
from sqlalchemy import or_
from models import db, Mobile, Accessory, Customer, Invoice, InvoiceItem, ExchangeRecord, PreBooking, Attendance
from routes.auth_routes import login_required, roles_accepted
from services.emi_service import create_emi_schedule
from services.pdf_service import generate_invoice_pdf
from services.notification_service import (
    send_email_invoice, build_whatsapp_invoice_message, get_whatsapp_url
)
from config import Config

pos_bp = Blueprint('pos', __name__, url_prefix='/pos')

def generate_unique_invoice_no():
    today_str = datetime.utcnow().strftime('%Y%m%d')
    unique_suffix = uuid.uuid4().hex[:4].upper()
    return f"INV-{today_str}-{unique_suffix}"

def safe_float(val, default=0.0):
    if val is None:
        return default
    try:
        f = float(val)
        return default if (f != f) else f
    except (ValueError, TypeError):
        return default

def safe_int(val, default=0):
    if val is None:
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default

@pos_bp.route('/billing')
@login_required
@roles_accepted('admin', 'cashier')
def billing():
    customers = Customer.query.order_by(Customer.name.asc()).all()
    mobiles = Mobile.query.filter(or_(Mobile.stock_quantity > 0, Mobile.status == 'reserved')).all()
    accessories = Accessory.query.filter(Accessory.stock_quantity > 0).all()
    
    preorder_id = request.args.get('preorder_id')
    preorder = None
    if preorder_id:
        try:
            preorder = db.session.get(PreBooking, int(preorder_id))
        except Exception:
            preorder = None

    today_attendance = None
    if 'user_id' in session and session.get('role') == 'cashier':
        today_attendance = Attendance.query.filter_by(user_id=session['user_id'], date=date.today()).first()

    return render_template(
        'pos/billing.html',
        customers=customers,
        mobiles=mobiles,
        accessories=accessories,
        preorder=preorder,
        today_attendance=today_attendance,
        today_date=date.today()
    )

@pos_bp.route('/checkout', methods=['POST'])
@login_required
@roles_accepted('admin', 'cashier')
def checkout():
    try:
        data = request.get_json()
        if not data or not data.get('items'):
            return jsonify({'success': False, 'message': 'Cart cannot be empty.'}), 400

        # Customer handling
        customer_id = data.get('customer_id')
        if not customer_id or str(customer_id) == 'new':
            cust_name = (data.get('customer_name') or '').strip() or 'Valued Customer'
            cust_phone = (data.get('customer_phone') or '').strip()
            cust_email = (data.get('customer_email') or '').strip()
            cust_address = (data.get('customer_address') or '').strip()
            
            if not cust_phone:
                return jsonify({'success': False, 'message': 'Customer phone number is required.'}), 400

            # Check if customer with phone already exists
            customer = Customer.query.filter_by(phone=cust_phone).first()
            if not customer:
                customer = Customer(
                    name=cust_name,
                    phone=cust_phone,
                    email=cust_email or None,
                    address=cust_address or None
                )
                db.session.add(customer)
                db.session.flush()
            else:
                if cust_name and cust_name != 'Valued Customer':
                    customer.name = cust_name
                if cust_email:
                    customer.email = cust_email
                if cust_address:
                    customer.address = cust_address
                db.session.flush()
        else:
            cust_pk = safe_int(customer_id, 0)
            customer = db.session.get(Customer, cust_pk) if cust_pk else None
            if not customer:
                return jsonify({'success': False, 'message': 'Customer not found.'}), 404

        invoice_no = generate_unique_invoice_no()
        payment_mode = data.get('payment_mode', 'Cash') or 'Cash'
        tax_rate = safe_float(data.get('tax_rate'), 18.0)
        discount_amount = safe_float(data.get('discount_amount'), 0.0)
        discount_type = data.get('discount_type', 'amount') or 'amount'
        discount_rate = safe_float(data.get('discount_rate'), 0.0)
        exchange_discount = safe_float(data.get('exchange_discount'), 0.0)
        notes = data.get('notes', '') or ''
        if discount_type == 'percent' and discount_rate > 0:
            pct_note = f"Discount: {discount_rate}% (₹{discount_amount:,.2f})"
            notes = f"{notes} | {pct_note}" if notes else pct_note

        # Calculate subtotal & validate stock
        subtotal = 0.0
        invoice_items = []

        for item_data in (data.get('items') or []):
            item_type = item_data.get('type')
            item_id = safe_int(item_data.get('id'), 0)
            qty = max(1, safe_int(item_data.get('qty'), 1))
            unit_price = safe_float(item_data.get('price'), 0.0)

            if item_type == 'mobile':
                mobile = db.session.get(Mobile, item_id)
                if not mobile or mobile.stock_quantity < qty:
                    return jsonify({'success': False, 'message': f"Mobile device '{item_data.get('name')}' is out of stock."}), 400
                
                # Reduce stock
                mobile.stock_quantity -= qty
                if mobile.stock_quantity <= 0:
                    mobile.status = 'sold'

                line_total = unit_price * qty
                subtotal += line_total
                invoice_items.append(InvoiceItem(
                    item_type='mobile',
                    mobile_id=mobile.id,
                    item_name=f"{mobile.brand} {mobile.model} ({mobile.ram}/{mobile.storage})",
                    imei=mobile.imei_1,
                    quantity=qty,
                    unit_price=unit_price,
                    total_price=line_total
                ))

            elif item_type == 'accessory':
                acc = db.session.get(Accessory, item_id)
                if not acc or acc.stock_quantity < qty:
                    return jsonify({'success': False, 'message': f"Accessory '{item_data.get('name')}' has insufficient stock."}), 400
                
                acc.stock_quantity -= qty
                line_total = unit_price * qty
                subtotal += line_total
                invoice_items.append(InvoiceItem(
                    item_type='accessory',
                    accessory_id=acc.id,
                    item_name=acc.name,
                    imei=None,
                    quantity=qty,
                    unit_price=unit_price,
                    total_price=line_total
                ))

        tax_amount = round((subtotal * tax_rate) / 100.0, 2)
        gross_total = subtotal + tax_amount

        # Pre-Order Token Advance Deduction
        preorder_id = data.get('preorder_id')
        token_advance = 0.0
        preorder = None
        if preorder_id:
            try:
                preorder = db.session.get(PreBooking, safe_int(preorder_id, 0))
                if preorder and preorder.status in ['Booked', 'Allocated']:
                    token_advance = safe_float(preorder.token_advance, 0.0)
                    adv_note = f"Pre-Order #{preorder.booking_no} Token Advance Deducted: -₹{token_advance:,.2f}"
                    notes = f"{notes} | {adv_note}" if notes else adv_note
            except Exception:
                preorder = None

        final_total = max(0.0, gross_total - discount_amount - exchange_discount - token_advance)

        payment_status = 'Paid'
        if payment_mode == 'EMI':
            payment_status = 'Partial'

        # Create Invoice
        invoice = Invoice(
            invoice_number=invoice_no,
            customer_id=customer.id,
            user_id=session.get('user_id', 1),
            subtotal=round(subtotal, 2),
            tax_rate=tax_rate,
            tax_amount=tax_amount,
            discount_amount=discount_amount,
            exchange_discount=exchange_discount,
            final_total=round(final_total, 2),
            payment_mode=payment_mode,
            payment_status=payment_status,
            notes=notes
        )
        db.session.add(invoice)
        db.session.flush()

        for inv_item in invoice_items:
            inv_item.invoice_id = invoice.id
            db.session.add(inv_item)

        # Exchange record link if provided
        exchange_data = data.get('exchange_details')
        if exchange_discount > 0 and exchange_data:
            ex_rec = ExchangeRecord(
                customer_id=customer.id,
                invoice_id=invoice.id,
                brand=exchange_data.get('brand', 'Old Device') or 'Old Device',
                model=exchange_data.get('model', 'Unknown Model') or 'Unknown Model',
                imei=exchange_data.get('imei', '') or '',
                original_price=safe_float(exchange_data.get('original_price'), 20000.0),
                age_months=safe_int(exchange_data.get('age_months'), 12),
                storage=exchange_data.get('storage', '64GB') or '64GB',
                battery_health=safe_int(exchange_data.get('battery_health'), 85),
                condition_screen=exchange_data.get('condition_screen', 'Good') or 'Good',
                condition_body=exchange_data.get('condition_body', 'Good') or 'Good',
                ai_estimated_value=safe_float(exchange_data.get('ai_value'), exchange_discount),
                offered_value=exchange_discount,
                status='Applied_To_Bill'
            )
            db.session.add(ex_rec)

        # EMI Setup if payment_mode is EMI
        if payment_mode == 'EMI':
            emi_plan = data.get('emi_plan') or {}
            down_payment = safe_float(emi_plan.get('down_payment'), 0.0)
            tenure_months = safe_int(emi_plan.get('tenure_months'), 6)
            fine_per_cycle = safe_float(emi_plan.get('fine_per_cycle'), 200.0)
            create_emi_schedule(
                invoice_id=invoice.id,
                customer_id=customer.id,
                total_amount=final_total,
                down_payment=down_payment,
                tenure_months=tenure_months,
                fine_per_cycle=fine_per_cycle,
                notes=f"EMI for Invoice #{invoice_no}"
            )

        # Fulfill Pre-Order if attached
        if preorder:
            preorder.status = 'Fulfilled'
            preorder.invoice_id = invoice.id
            preorder.fulfilled_at = datetime.utcnow()
            if preorder.allocated_mobile:
                preorder.allocated_mobile.status = 'sold'
                preorder.allocated_mobile.stock_quantity = max(0, preorder.allocated_mobile.stock_quantity - 1)

        db.session.commit()

        # Automatic Gmail invoice dispatch with PDF attachment
        send_email_opt = data.get('send_email', True)
        target_email = (data.get('customer_email') or (customer.email if customer else None) or '').strip()
        recipient_target = target_email or (Config.MAIL_USERNAME if Config.MAIL_USERNAME else None)
        email_dispatched = False

        if send_email_opt and recipient_target:
            app_ref = current_app._get_current_object()
            inv_id = invoice.id
            def dispatch_mail(app, i_id, to_addr):
                with app.app_context():
                    try:
                        inv = db.session.get(Invoice, i_id)
                        if inv:
                            send_email_invoice(inv, recipient_email=to_addr)
                    except Exception as mail_err:
                        print(f"[POS CHECKOUT MAIL ERROR] {mail_err}")

            threading.Thread(target=dispatch_mail, args=(app_ref, inv_id, recipient_target), daemon=True).start()
            email_dispatched = True

        # WhatsApp link generation with attached PDF download link
        host_url = request.host_url.rstrip('/')
        wa_text = build_whatsapp_invoice_message(invoice, host_url=host_url)
        wa_url = get_whatsapp_url(customer.phone, wa_text)
        pdf_download_url = url_for('pos.public_download_pdf', invoice_number=invoice.invoice_number, _external=True)

        return jsonify({
            'success': True,
            'invoice_id': invoice.id,
            'invoice_number': invoice.invoice_number,
            'customer_name': customer.name,
            'customer_phone': customer.phone,
            'customer_email': customer.email or target_email or '',
            'final_total': invoice.final_total,
            'redirect_url': url_for('pos.view_invoice', invoice_id=invoice.id),
            'pdf_url': pdf_download_url,
            'whatsapp_url': wa_url,
            'whatsapp_message': wa_text,
            'email_sent': email_dispatched,
            'recipient_email': recipient_target,
            'email_message': f"Official bill & PDF attached dispatched to {recipient_target} via Gmail." if email_dispatched else ""
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f"Checkout failed: {str(e)}"}), 500

@pos_bp.route('/receipt/<string:invoice_number>')
def public_receipt(invoice_number):
    """Public customer view of their tax invoice and warranty slip (accessed from WhatsApp)."""
    invoice = Invoice.query.filter_by(invoice_number=invoice_number).first_or_404()
    host_url = request.host_url.rstrip('/')
    wa_text = build_whatsapp_invoice_message(invoice, host_url=host_url)
    wa_url = get_whatsapp_url(invoice.customer.phone if invoice.customer else '', wa_text)
    return render_template('pos/invoice_view.html', invoice=invoice, whatsapp_url=wa_url, config=Config, is_public=True)

@pos_bp.route('/receipt/<string:invoice_number>/pdf')
def public_download_pdf(invoice_number):
    """Direct PDF download link for customers sent via WhatsApp."""
    invoice = Invoice.query.filter_by(invoice_number=invoice_number).first_or_404()
    pdf_buffer = generate_invoice_pdf(invoice)
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"{invoice.invoice_number}.pdf"
    )

@pos_bp.route('/invoices')
@login_required
@roles_accepted('admin', 'cashier')
def invoices_list():
    query = request.args.get('q', '').strip()
    invoices_q = Invoice.query
    if query:
        invoices_q = invoices_q.join(Customer).filter(
            (Invoice.invoice_number.ilike(f'%{query}%')) |
            (Customer.name.ilike(f'%{query}%')) |
            (Customer.phone.ilike(f'%{query}%'))
        )
    invoices = invoices_q.order_by(Invoice.created_at.desc()).all()
    return render_template('pos/invoices_list.html', invoices=invoices, q=query)

@pos_bp.route('/invoices/<int:invoice_id>')
@login_required
@roles_accepted('admin', 'cashier')
def view_invoice(invoice_id):
    invoice = db.session.get(Invoice, invoice_id)
    if not invoice:
        flash("Invoice not found.", "danger")
        return redirect(url_for('pos.invoices_list'))

    host_url = request.host_url.rstrip('/')
    wa_text = build_whatsapp_invoice_message(invoice, host_url=host_url)
    wa_url = get_whatsapp_url(invoice.customer.phone if invoice.customer else '', wa_text)

    return render_template('pos/invoice_view.html', invoice=invoice, whatsapp_url=wa_url, config=Config, is_public=False)

@pos_bp.route('/invoices/<int:invoice_id>/pdf')
@login_required
@roles_accepted('admin', 'cashier')
def download_pdf(invoice_id):
    invoice = db.session.get(Invoice, invoice_id)
    if not invoice:
        flash("Invoice not found.", "danger")
        return redirect(url_for('pos.invoices_list'))

    pdf_buffer = generate_invoice_pdf(invoice)
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"{invoice.invoice_number}.pdf"
    )

@pos_bp.route('/invoices/<int:invoice_id>/send-email', methods=['POST'])
@login_required
@roles_accepted('admin', 'cashier')
def email_invoice_action(invoice_id):
    invoice = db.session.get(Invoice, invoice_id)
    if not invoice:
        return jsonify({'success': False, 'message': 'Invoice not found'}), 404

    data = request.get_json(silent=True) or {}
    target_email = (data.get('email') or request.form.get('email') or (invoice.customer.email if invoice.customer else None) or '').strip() or None

    if target_email and invoice.customer and not invoice.customer.email:
        try:
            invoice.customer.email = target_email
            db.session.commit()
        except Exception:
            pass

    success, msg = send_email_invoice(invoice, recipient_email=target_email)
    return jsonify({'success': success, 'message': msg, 'recipient': target_email})
