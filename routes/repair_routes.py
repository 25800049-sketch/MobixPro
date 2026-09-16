"""
Mobile Repair Service Controller
Handles repair ticketing, lifecycle pipeline (Received -> Diagnosing -> Repairing -> Ready -> Delivered),
technician notes, parts consumption, and WhatsApp status updates.
"""
import uuid
from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from models import db, RepairTicket, Customer, User, Invoice, InvoiceItem, Attendance
from routes.auth_routes import login_required, roles_accepted
from services.notification_service import build_whatsapp_repair_message, get_whatsapp_url

repair_bp = Blueprint('repairs', __name__, url_prefix='/repairs')

def generate_repair_ticket_no():
    suffix = uuid.uuid4().hex[:4].upper()
    return f"REP-{datetime.utcnow().strftime('%y%m%d')}-{suffix}"

@repair_bp.route('/')
@login_required
@roles_accepted('admin', 'technician')
def repair_list():
    status_filter = request.args.get('status', '').strip()
    query = request.args.get('q', '').strip()

    repairs_q = RepairTicket.query.join(Customer)
    if status_filter:
        repairs_q = repairs_q.filter(RepairTicket.status == status_filter)
    if query:
        repairs_q = repairs_q.filter(
            (RepairTicket.ticket_no.ilike(f'%{query}%')) |
            (RepairTicket.model.ilike(f'%{query}%')) |
            (Customer.name.ilike(f'%{query}%')) |
            (Customer.phone.ilike(f'%{query}%'))
        )

    tickets = repairs_q.order_by(RepairTicket.created_at.desc()).all()
    technicians = User.query.filter(User.role.in_(['technician', 'admin'])).all()
    customers = Customer.query.order_by(Customer.name.asc()).all()

    # Status counts
    counts = {
        'Received': RepairTicket.query.filter_by(status='Received').count(),
        'Diagnosing': RepairTicket.query.filter_by(status='Diagnosing').count(),
        'Repairing': RepairTicket.query.filter_by(status='Repairing').count(),
        'Ready': RepairTicket.query.filter_by(status='Ready').count(),
        'Delivered': RepairTicket.query.filter_by(status='Delivered').count()
    }

    # Fetch today's attendance for the logged-in user
    today_attendance = None
    if 'user_id' in session:
        today_attendance = Attendance.query.filter_by(user_id=session['user_id'], date=date.today()).first()

    return render_template(
        'repairs/repair_list.html',
        tickets=tickets,
        technicians=technicians,
        customers=customers,
        selected_status=status_filter,
        q=query,
        counts=counts,
        today_attendance=today_attendance,
        today_date=date.today()
    )

@repair_bp.route('/create', methods=['POST'])
@login_required
@roles_accepted('admin', 'technician')
def create_ticket():
    try:
        customer_id = request.form.get('customer_id')
        if not customer_id or customer_id == 'new':
            cust_name = request.form.get('customer_name', '').strip()
            cust_phone = request.form.get('customer_phone', '').strip()
            if not cust_phone:
                flash("Customer phone is required.", "danger")
                return redirect(url_for('repairs.repair_list'))
            customer = Customer(name=cust_name or 'Walk-in', phone=cust_phone)
            db.session.add(customer)
            db.session.flush()
        else:
            customer = db.session.get(Customer, int(customer_id))

        ticket = RepairTicket(
            ticket_no=generate_repair_ticket_no(),
            customer_id=customer.id,
            technician_id=int(request.form.get('technician_id')) if request.form.get('technician_id') else None,
            brand=request.form.get('brand', '').strip(),
            model=request.form.get('model', '').strip(),
            imei=request.form.get('imei', '').strip() or None,
            problem_description=request.form.get('problem_description', '').strip(),
            estimated_cost=float(request.form.get('estimated_cost', 0)),
            advance_paid=float(request.form.get('advance_paid', 0)),
            status='Received',
            warranty_days=int(request.form.get('warranty_days', 30))
        )
        db.session.add(ticket)
        db.session.commit()
        flash(f"Repair Ticket #{ticket.ticket_no} generated successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error creating ticket: {str(e)}", "danger")

    return redirect(url_for('repairs.repair_list'))

@repair_bp.route('/<int:ticket_id>/update-status', methods=['POST'])
@login_required
@roles_accepted('admin', 'technician')
def update_ticket_status(ticket_id):
    ticket = db.session.get(RepairTicket, ticket_id)
    if not ticket:
        flash("Repair ticket not found.", "danger")
        return redirect(url_for('repairs.repair_list'))

    new_status = request.form.get('status')
    if new_status in ['Received', 'Diagnosing', 'Repairing', 'Ready', 'Delivered']:
        ticket.status = new_status
        if new_status == 'Delivered':
            ticket.delivery_date = date.today()
        
    if request.form.get('final_cost'):
        ticket.final_cost = float(request.form.get('final_cost'))
    if request.form.get('technician_notes'):
        ticket.technician_notes = request.form.get('technician_notes').strip()
    if request.form.get('parts_used'):
        ticket.parts_used = request.form.get('parts_used').strip()

    db.session.commit()
    flash(f"Updated Ticket #{ticket.ticket_no} to {ticket.status}.", "success")
    return redirect(url_for('repairs.repair_list'))

@repair_bp.route('/<int:ticket_id>/collect-payment', methods=['POST'])
@login_required
@roles_accepted('admin', 'technician')
def collect_payment(ticket_id):
    ticket = db.session.get(RepairTicket, ticket_id)
    if not ticket:
        flash("Repair ticket not found.", "danger")
        return redirect(url_for('repairs.repair_list'))

    try:
        amount = float(request.form.get('payment_amount', 0))
        payment_mode = request.form.get('payment_mode', 'Cash')
        new_status = request.form.get('update_status')
        notes = request.form.get('payment_notes', '').strip()

        if amount <= 0:
            flash("Please enter a valid payment amount greater than zero.", "danger")
            return redirect(url_for('repairs.repair_list'))

        # Increment collected amount
        ticket.advance_paid = (ticket.advance_paid or 0.0) + amount
        ticket.payment_mode = payment_mode

        effective_cost = ticket.final_cost if (ticket.final_cost and ticket.final_cost > 0) else ticket.estimated_cost
        if ticket.advance_paid >= effective_cost - 0.01:
            ticket.payment_status = 'Paid'
        else:
            ticket.payment_status = 'Partial'

        # Lifecycle update if requested
        if new_status in ['Ready', 'Delivered']:
            ticket.status = new_status
            if new_status == 'Delivered':
                ticket.delivery_date = date.today()

        if notes:
            existing = ticket.technician_notes or ''
            ticket.technician_notes = f"{existing} | Paid ₹{amount:,.2f} via {payment_mode}: {notes}".strip(' | ')

        # Create paid Invoice record for POS accounting & collections ledger
        inv_no = f"INV-REP-{ticket.ticket_no.replace('REP-', '')}"
        existing_inv = Invoice.query.filter_by(invoice_number=inv_no).first()
        if not existing_inv:
            inv = Invoice(
                invoice_number=inv_no,
                customer_id=ticket.customer_id,
                user_id=session.get('user_id', ticket.technician_id or 1),
                subtotal=amount,
                tax_rate=0.0,
                tax_amount=0.0,
                discount_amount=0.0,
                exchange_discount=0.0,
                final_total=amount,
                payment_mode=payment_mode,
                payment_status='Paid',
                notes=f"Repair Payment Receipt: #{ticket.ticket_no} ({ticket.brand} {ticket.model})"
            )
            db.session.add(inv)
            db.session.flush()

            inv_item = InvoiceItem(
                invoice_id=inv.id,
                item_type='repair',
                item_name=f"Repair Service: {ticket.brand} {ticket.model}",
                imei=ticket.imei or '',
                quantity=1,
                unit_price=amount,
                total_price=amount
            )
            db.session.add(inv_item)

        db.session.commit()
        flash(f"Payment of ₹{amount:,.2f} recorded successfully via {payment_mode}! Ticket #{ticket.ticket_no} balance is now ₹{max(0.0, effective_cost - ticket.advance_paid):,.2f}.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error processing payment: {str(e)}", "danger")

    return redirect(url_for('repairs.repair_list'))

@repair_bp.route('/<int:ticket_id>/receipt')
@login_required
@roles_accepted('admin', 'technician')
def repair_receipt(ticket_id):
    ticket = db.session.get(RepairTicket, ticket_id)
    if not ticket:
        flash("Repair ticket not found.", "danger")
        return redirect(url_for('repairs.repair_list'))

    effective_cost = ticket.final_cost if (ticket.final_cost and ticket.final_cost > 0) else ticket.estimated_cost
    balance_due = max(0.0, effective_cost - (ticket.advance_paid or 0.0))

    return render_template(
        'repairs/repair_receipt.html',
        ticket=ticket,
        effective_cost=effective_cost,
        balance_due=balance_due
    )

@repair_bp.route('/<int:ticket_id>/whatsapp-url')
@login_required
@roles_accepted('admin', 'technician')
def get_repair_whatsapp(ticket_id):
    ticket = db.session.get(RepairTicket, ticket_id)
    if not ticket or not ticket.customer:
        return jsonify({'success': False, 'message': 'Ticket not found'}), 404

    msg = build_whatsapp_repair_message(ticket)
    url = get_whatsapp_url(ticket.customer.phone, msg)
    return jsonify({'success': True, 'url': url})

@repair_bp.route('/api/track')
def api_track():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({'success': False, 'message': 'Please enter a ticket number, IMEI, or phone.'}), 400

    clean_q = q.replace('#', '').strip()

    # 1. Search by exact or partial ticket_no / IMEI
    ticket = RepairTicket.query.filter(
        (RepairTicket.ticket_no.ilike(f"%{clean_q}%")) |
        (RepairTicket.imei.ilike(f"%{clean_q}%"))
    ).order_by(RepairTicket.created_at.desc()).first()

    # 2. Handle pasted inputs with multiple prefixes like "REP-10REP-260910-EA46"
    if not ticket and 'REP-' in clean_q.upper():
        parts = [f"REP-{p.strip('-')}" for p in clean_q.upper().split('REP-') if p.strip('-')]
        for candidate in reversed(parts):
            ticket = RepairTicket.query.filter(
                (RepairTicket.ticket_no.ilike(f"%{candidate}%")) |
                (RepairTicket.ticket_no == candidate)
            ).first()
            if ticket:
                break

    # 3. Search by customer phone or customer name
    if not ticket:
        ticket = RepairTicket.query.join(Customer).filter(
            (Customer.phone.ilike(f"%{clean_q}%")) |
            (Customer.name.ilike(f"%{clean_q}%"))
        ).order_by(RepairTicket.created_at.desc()).first()

    if not ticket:
        return jsonify({'success': False, 'message': f"No repair job found for '{q}'"}), 404

    data = ticket.to_dict()

    # Map status to progress percentage and badge class
    status_config = {
        'Received': {'percent': 25, 'badge_class': 'badge-info', 'step_label': 'Received & Logged'},
        'Diagnosing': {'percent': 50, 'badge_class': 'badge-warning', 'step_label': 'Under Diagnostics'},
        'Repairing': {'percent': 75, 'badge_class': 'badge-primary', 'step_label': 'Repair in Progress'},
        'Ready': {'percent': 100, 'badge_class': 'badge-success', 'step_label': 'QC Passed & Ready for Pickup'},
        'Delivered': {'percent': 100, 'badge_class': 'badge-secondary', 'step_label': 'Delivered to Customer'}
    }
    cfg = status_config.get(ticket.status, {'percent': 50, 'badge_class': 'badge-primary', 'step_label': ticket.status})
    data['progress_percent'] = cfg['percent']
    data['badge_class'] = cfg['badge_class']
    data['step_label'] = cfg['step_label']

    return jsonify({'success': True, 'ticket': data})

