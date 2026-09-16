"""
Pre-Orders, Priority Queue Waitlist & Lost Sales Recovery Blueprint
Handles:
- In-Store Staff Booking Console (/preorders)
- FIFO Auto-Allocation Engine for Incoming Stock
- Printable Token Advance Slips & WhatsApp Dispatches
- Lost Sales & Wanted Devices Tracker
- Public Customer Self-Booking Portal (/prebook)
- Public Live Digital Booking Pass & Status Tracker (/prebook/pass/<booking_no>)
"""
from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from sqlalchemy import func, or_
from models import db, PreBooking, LostSaleRequest, Customer, Mobile, Invoice
from routes.auth_routes import login_required, roles_accepted
import threading
from services.notification_service import (
    build_whatsapp_preorder_confirmation,
    build_whatsapp_stock_arrival_alert,
    build_whatsapp_lost_sale_alert,
    get_whatsapp_url,
    send_email_preorder_confirmation,
    send_email_stock_arrival,
    async_send_preorder_confirmation,
    async_send_stock_arrival
)
from config import Config

# Staff Console Blueprint
preorder_bp = Blueprint('preorders', __name__, url_prefix='/preorders')

# Public Customer Portal Blueprint
public_prebook_bp = Blueprint('prebook', __name__, url_prefix='/prebook')


def generate_booking_number():
    """Generates sequential PB-YYYY-XXXX booking number ensuring uniqueness."""
    year = datetime.utcnow().year
    prefix = f"PB-{year}-"
    matching = PreBooking.query.filter(PreBooking.booking_no.like(f"{prefix}%")).all()
    max_seq = 0
    for b in matching:
        parts = b.booking_no.split('-')
        if len(parts) >= 3:
            try:
                num = int(parts[-1])
                if num > max_seq:
                    max_seq = num
            except ValueError:
                pass
    seq = max_seq + 1
    while PreBooking.query.filter_by(booking_no=f"{prefix}{seq:04d}").first() is not None:
        seq += 1
    return f"{prefix}{seq:04d}"


def calculate_next_queue_priority(brand, model):
    """Calculates next sequential priority rank for a given flagship model."""
    active_max = db.session.query(func.max(PreBooking.queue_priority)).filter(
        PreBooking.brand.ilike(brand.strip()),
        PreBooking.model.ilike(model.strip()),
        PreBooking.status.in_(['Booked', 'Allocated'])
    ).scalar()
    return (active_max or 0) + 1


# =========================================================================
# 🏪 IN-STORE STAFF BOOKING CONSOLE (/preorders)
# =========================================================================

@preorder_bp.route('/')
@login_required
@roles_accepted('admin', 'cashier')
def index():
    status_filter = request.args.get('status', '').strip()
    brand_filter = request.args.get('brand', '').strip()
    search = request.args.get('q', '').strip()

    query = PreBooking.query
    if status_filter:
        query = query.filter(PreBooking.status == status_filter)
    if brand_filter:
        query = query.filter(PreBooking.brand.ilike(f"%{brand_filter}%"))
    if search:
        query = query.join(Customer).filter(
            or_(
                PreBooking.booking_no.ilike(f"%{search}%"),
                PreBooking.model.ilike(f"%{search}%"),
                Customer.name.ilike(f"%{search}%"),
                Customer.phone.ilike(f"%{search}%")
            )
        )

    bookings = query.order_by(PreBooking.queue_priority.asc(), PreBooking.created_at.desc()).all()

    # Pre-generate WhatsApp click URLs for staff convenience
    whatsapp_urls = {}
    host_url = request.host_url
    for b in bookings:
        if b.customer and b.customer.phone:
            if b.status == 'Allocated':
                msg = build_whatsapp_stock_arrival_alert(b, host_url=host_url)
            else:
                msg = build_whatsapp_preorder_confirmation(b, host_url=host_url)
            whatsapp_urls[b.id] = get_whatsapp_url(b.customer.phone, msg)

    # Aggregated KPIs
    total_bookings = PreBooking.query.count()
    total_advance_collected = db.session.query(func.sum(PreBooking.token_advance)).filter(PreBooking.status != 'Cancelled').scalar() or 0.0
    awaiting_stock_count = PreBooking.query.filter_by(status='Booked').count()
    ready_pickup_count = PreBooking.query.filter_by(status='Allocated').count()
    fulfilled_count = PreBooking.query.filter_by(status='Fulfilled').count()

    # Lost sales list
    lost_sales = LostSaleRequest.query.order_by(LostSaleRequest.created_at.desc()).limit(20).all()
    lost_sales_pending_count = LostSaleRequest.query.filter_by(status='Pending').count()

    # Available in-stock mobiles that can be manually allocated
    available_mobiles = Mobile.query.filter_by(status='in_stock').all()

    # Unique brands for filtering
    brands = [r[0] for r in db.session.query(PreBooking.brand).distinct().all() if r[0]]

    return render_template(
        'preorders/index.html',
        bookings=bookings,
        whatsapp_urls=whatsapp_urls,
        total_bookings=total_bookings,
        total_advance_collected=total_advance_collected,
        awaiting_stock_count=awaiting_stock_count,
        ready_pickup_count=ready_pickup_count,
        fulfilled_count=fulfilled_count,
        lost_sales=lost_sales,
        lost_sales_pending_count=lost_sales_pending_count,
        available_mobiles=available_mobiles,
        brands=brands,
        selected_status=status_filter,
        selected_brand=brand_filter,
        search_query=search
    )


@preorder_bp.route('/create', methods=['POST'])
@login_required
@roles_accepted('admin', 'cashier')
def create_booking():
    """Cashier/Admin creates a walk-in or phone pre-booking."""
    try:
        cust_name = request.form.get('customer_name', '').strip()
        cust_phone = request.form.get('customer_phone', '').strip()
        cust_email = request.form.get('customer_email', '').strip() or None
        cust_address = request.form.get('customer_address', '').strip() or None

        brand = request.form.get('brand', '').strip()
        model = request.form.get('model', '').strip()
        storage = request.form.get('storage', '256GB').strip()
        color = request.form.get('color', 'Default').strip()
        variant = f"{storage} - {color}"

        expected_price = float(request.form.get('expected_price', 0) or 0)
        token_advance = float(request.form.get('token_advance', 2000) or 2000)
        payment_mode = request.form.get('payment_mode', 'UPI')
        notes = request.form.get('notes', '').strip() or None
        delivery_date_raw = request.form.get('expected_delivery_date', '').strip()
        expected_delivery = datetime.strptime(delivery_date_raw, '%Y-%m-%d').date() if delivery_date_raw else None

        if not cust_name or not cust_phone or not brand or not model:
            flash("Please fill in all mandatory customer and flagship details.", "error")
            return redirect(url_for('preorders.index'))

        # Find or create customer
        customer = Customer.query.filter_by(phone=cust_phone).first()
        if not customer:
            customer = Customer(name=cust_name, phone=cust_phone, email=cust_email, address=cust_address)
            db.session.add(customer)
            db.session.flush()
        else:
            if cust_name:
                customer.name = cust_name
            if cust_email:
                customer.email = cust_email
            if cust_address:
                customer.address = cust_address

        booking_no = generate_booking_number()
        priority = calculate_next_queue_priority(brand, model)

        booking = PreBooking(
            booking_no=booking_no,
            customer_id=customer.id,
            brand=brand,
            model=model,
            variant=variant,
            color=color,
            storage=storage,
            expected_price=expected_price,
            token_advance=token_advance,
            payment_mode=payment_mode,
            payment_status='Paid',
            booking_source='In-Store',
            queue_priority=priority,
            status='Booked',
            expected_delivery_date=expected_delivery,
            notes=notes
        )
        db.session.add(booking)
        db.session.commit()

        # Dispatch pre-order confirmation to customer via Gmail
        target_email = (cust_email or (customer.email if customer else None) or '').strip()
        email_status_note = ""
        if target_email:
            try:
                host_url = request.host_url
                ok, mail_res = send_email_preorder_confirmation(booking, recipient_email=target_email, host_url=host_url)
                if ok:
                    email_status_note = f" ✉️ Confirmation email sent to {target_email} via Gmail."
                else:
                    email_status_note = f" ⚠️ Gmail note: {mail_res}"
            except Exception as mail_err:
                print(f"[PREORDER MAIL ERROR] {mail_err}")
                email_status_note = f" ⚠️ Gmail delivery error: {str(mail_err)}"
        else:
            email_status_note = " (Note: No customer email provided for Gmail alert)"

        flash(f"Pre-Order #{booking_no} registered successfully! Assigned Queue Rank: #{priority}.{email_status_note}", "success")
        return redirect(url_for('preorders.index'))

    except Exception as e:
        db.session.rollback()
        flash(f"Failed to create pre-booking: {str(e)}", "error")
        return redirect(url_for('preorders.index'))


@preorder_bp.route('/auto-allocate', methods=['POST'])
@login_required
@roles_accepted('admin', 'cashier')
def auto_allocate():
    """
    Automated FIFO Allocation Engine:
    Finds in-stock mobiles and pairs them to the highest-priority waiting bookings.
    Marks paired mobile as 'reserved' and booking as 'Allocated'.
    """
    try:
        # Get unallocated waiting bookings ordered by queue priority
        waiting_bookings = PreBooking.query.filter_by(status='Booked')\
                                           .order_by(PreBooking.queue_priority.asc(), PreBooking.created_at.asc()).all()

        allocated_count = 0

        newly_allocated_bookings = []

        for booking in waiting_bookings:
            # Find an available in-stock mobile matching brand and model
            candidate = Mobile.query.filter(
                Mobile.brand.ilike(booking.brand),
                Mobile.model.ilike(f"%{booking.model}%"),
                Mobile.status == 'in_stock',
                Mobile.stock_quantity > 0
            ).first()

            if candidate:
                booking.allocated_mobile_id = candidate.id
                booking.status = 'Allocated'
                candidate.status = 'reserved'
                allocated_count += 1
                newly_allocated_bookings.append(booking)

        db.session.commit()

        # Send stock arrival Gmail alert to all allocated customers
        email_sent_count = 0
        if newly_allocated_bookings:
            host_url = request.host_url
            for b in newly_allocated_bookings:
                target_email = b.customer.email if (b.customer and b.customer.email) else None
                if target_email:
                    try:
                        ok, _ = send_email_stock_arrival(b, recipient_email=target_email, host_url=host_url)
                        if ok:
                            email_sent_count += 1
                    except Exception as mail_err:
                        print(f"[STOCK ARRIVAL MAIL ERROR] {mail_err}")

        if allocated_count > 0:
            mail_txt = f" Stock arrival alerts sent to {email_sent_count} customer(s) via Gmail." if email_sent_count > 0 else ""
            flash(f"⚡ Successfully auto-allocated {allocated_count} incoming flagship handset(s) to waiting pre-orders!{mail_txt}", "success")
        else:
            flash("No matching in-stock handsets found for waiting pre-orders. Inward new stock first.", "info")

        return redirect(url_for('preorders.index'))

    except Exception as e:
        db.session.rollback()
        flash(f"Auto-allocation error: {str(e)}", "error")
        return redirect(url_for('preorders.index'))


@preorder_bp.route('/<int:booking_id>/allocate', methods=['POST'])
@login_required
@roles_accepted('admin', 'cashier')
def manual_allocate(booking_id):
    """Manually pairs a specific in-stock phone IMEI to a booking."""
    booking = db.session.get(PreBooking, booking_id)
    if not booking:
        flash("Booking record not found.", "error")
        return redirect(url_for('preorders.index'))

    mobile_id = request.form.get('mobile_id')
    if not mobile_id:
        flash("Please select an available device.", "error")
        return redirect(url_for('preorders.index'))

    mobile = db.session.get(Mobile, int(mobile_id))
    if not mobile or mobile.status != 'in_stock':
        flash("Selected device is no longer available in stock.", "error")
        return redirect(url_for('preorders.index'))

    # If previously had an allocated mobile, release it
    if booking.allocated_mobile:
        booking.allocated_mobile.status = 'in_stock'

    booking.allocated_mobile_id = mobile.id
    booking.status = 'Allocated'
    mobile.status = 'reserved'
    db.session.commit()

    # Dispatch stock arrival email via Gmail
    target_email = booking.customer.email if (booking.customer and booking.customer.email) else None
    email_note = ""
    if target_email:
        try:
            host_url = request.host_url
            ok, err = send_email_stock_arrival(booking, recipient_email=target_email, host_url=host_url)
            if ok:
                email_note = f" ✉️ Stock arrival alert sent to {target_email} via Gmail!"
            else:
                email_note = f" ⚠️ Gmail note: {err}"
        except Exception as mail_err:
            print(f"[MANUAL ALLOCATE MAIL ERROR] {mail_err}")
            email_note = f" ⚠️ Gmail error: {str(mail_err)}"
    else:
        email_note = " (Customer has no email address for Gmail alert)"

    flash(f"Device {mobile.brand} {mobile.model} (IMEI: {mobile.imei_1}) assigned to Booking #{booking.booking_no}.{email_note}", "success")
    return redirect(url_for('preorders.index'))


@preorder_bp.route('/<int:booking_id>/cancel', methods=['POST'])
@login_required
@roles_accepted('admin', 'cashier')
def cancel_booking(booking_id):
    """Cancels booking, releases reserved device back to stock, and records refund."""
    booking = db.session.get(PreBooking, booking_id)
    if not booking:
        flash("Booking not found.", "error")
        return redirect(url_for('preorders.index'))

    # Release device if reserved
    if booking.allocated_mobile:
        booking.allocated_mobile.status = 'in_stock'
        booking.allocated_mobile_id = None

    refund_reason = request.form.get('reason', 'Customer requested cancellation')
    booking.status = 'Cancelled'
    booking.notes = f"{booking.notes or ''} | CANCELLED: {refund_reason} (Token Advance ₹{booking.token_advance:,.2f} refunded)".strip(" | ")
    db.session.commit()

    flash(f"Booking #{booking.booking_no} has been cancelled. Advance refund recorded.", "info")
    return redirect(url_for('preorders.index'))


@preorder_bp.route('/receipt/<int:booking_id>')
def booking_receipt(booking_id):
    """Printable official Pre-Booking Token Slip / Voucher (Thermal & A4)."""
    booking = db.session.get(PreBooking, booking_id)
    if not booking:
        flash("Booking not found.", "error")
        return redirect(url_for('preorders.index'))

    return render_template('preorders/booking_receipt.html', booking=booking, config=Config)


@preorder_bp.route('/<int:booking_id>/send-email', methods=['POST'])
@login_required
@roles_accepted('admin', 'cashier')
def send_email_notification(booking_id):
    """Dispatches Pre-Order Confirmation or Stock Arrived notification via Gmail."""
    booking = db.session.get(PreBooking, booking_id)
    if not booking:
        flash("Booking record not found.", "error")
        return redirect(url_for('preorders.index'))

    if not booking.customer or not booking.customer.email:
        flash(f"Customer '{booking.customer.name if booking.customer else 'Unknown'}' does not have an email address registered.", "warning")
        return redirect(url_for('preorders.index'))

    host_url = request.host_url
    if booking.status == 'Allocated':
        success, msg = send_email_stock_arrival(booking, booking.customer.email, host_url)
    else:
        success, msg = send_email_preorder_confirmation(booking, booking.customer.email, host_url)

    if success:
        flash(f"Notification email dispatched to {booking.customer.email} via Gmail.", "success")
    else:
        flash(f"Email delivery issue: {msg}", "danger")

    return redirect(url_for('preorders.index'))


@preorder_bp.route('/lost-sales/create', methods=['POST'])
@login_required
@roles_accepted('admin', 'cashier')
def create_lost_sale():
    """Quick 10-second intake for out-of-stock customer inquiries."""
    try:
        name = request.form.get('customer_name', '').strip()
        phone = request.form.get('customer_phone', '').strip()
        email = request.form.get('customer_email', '').strip() or None
        brand = request.form.get('brand', '').strip()
        model = request.form.get('model', '').strip()
        variant = request.form.get('variant', '').strip() or None
        budget = float(request.form.get('max_budget', 0) or 0)
        notes = request.form.get('notes', '').strip() or None

        if not name or not phone or not brand or not model:
            flash("Please enter customer name, phone, brand and requested model.", "error")
            return redirect(url_for('preorders.index'))

        req = LostSaleRequest(
            customer_name=name,
            customer_phone=phone,
            customer_email=email,
            brand=brand,
            model=model,
            variant=variant,
            max_budget=budget,
            status='Pending',
            notes=notes
        )
        db.session.add(req)
        db.session.commit()

        flash(f"Lost sale demand captured for '{brand} {model}'. We will alert customer when restocked!", "success")
        return redirect(url_for('preorders.index'))
    except Exception as e:
        db.session.rollback()
        flash(f"Error logging request: {str(e)}", "error")
        return redirect(url_for('preorders.index'))


@preorder_bp.route('/lost-sales/<int:request_id>/status', methods=['POST'])
@login_required
@roles_accepted('admin', 'cashier')
def update_lost_sale_status(request_id):
    req = db.session.get(LostSaleRequest, request_id)
    if req:
        new_status = request.form.get('status', 'Pending')
        req.status = new_status
        db.session.commit()
        flash("Status updated.", "success")
    return redirect(url_for('preorders.index'))


@preorder_bp.route('/lost-sales/<int:request_id>/delete', methods=['POST'])
@login_required
@roles_accepted('admin')
def delete_lost_sale(request_id):
    req = db.session.get(LostSaleRequest, request_id)
    if req:
        db.session.delete(req)
        db.session.commit()
        flash("Record removed.", "info")
    return redirect(url_for('preorders.index'))


# =========================================================================
# 📱 PUBLIC CUSTOMER SELF-BOOKING PORTAL (/prebook)
# =========================================================================

@public_prebook_bp.route('/')
def public_showcase():
    """
    Public flagship landing page where customers browse upcoming launches
    and pre-book directly from their mobile phones.
    """
    flagships = [
        {
            'brand': 'Apple',
            'model': 'iPhone 16 Pro Max',
            'tagline': 'All-New Titanium Design with A18 Pro Bionic & Camera Control',
            'display': '6.9" Super Retina XDR OLED 120Hz ProMotion',
            'processor': 'Apple A18 Pro (3nm)',
            'camera': '48MP Fusion + 48MP Ultra-Wide + 5x Telephoto',
            'battery': '4,685 mAh with MagSafe Fast Charge',
            'image': '/static/img/phones/iphone_15_pro_max.jpg',
            'expected_price': 144900,
            'min_token': 5000,
            'colors': ['Desert Titanium', 'Natural Titanium', 'White Titanium', 'Black Titanium'],
            'storages': ['256GB', '512GB', '1TB'],
            'launch_status': 'Pre-Orders Open • Ships Soon'
        },
        {
            'brand': 'Samsung',
            'model': 'Galaxy S25 Ultra',
            'tagline': 'Galaxy AI Powered by Snapdragon 8 Elite & S-Pen',
            'display': '6.8" Dynamic AMOLED 2X QHD+ 120Hz',
            'processor': 'Snapdragon 8 Elite (3nm)',
            'camera': '200MP Quad Camera with 100x Space Zoom',
            'battery': '5,000 mAh with 45W Super Fast Charge 2.0',
            'image': '/static/img/phones/galaxy_s24_ultra.jpg',
            'expected_price': 134999,
            'min_token': 5000,
            'colors': ['Titanium Silver', 'Titanium Black', 'Titanium Blue', 'Titanium Gray'],
            'storages': ['256GB', '512GB', '1TB'],
            'launch_status': 'Pre-Orders Open • Ships Soon'
        },
        {
            'brand': 'OnePlus',
            'model': 'OnePlus 13 5G',
            'tagline': 'Hasselblad Flagship with 6,000 mAh Glacier Battery',
            'display': '6.82" 2K Oriental Screen 120Hz LTPO',
            'processor': 'Snapdragon 8 Elite Octa-Core',
            'camera': '50MP Sony LYT-808 Tri-Camera System',
            'battery': '6,000 mAh Silicon-Carbon with 100W SUPERVOOC',
            'image': '/static/img/phones/oneplus_12.jpg',
            'expected_price': 69999,
            'min_token': 2000,
            'colors': ['Midnight Black', 'Emerald Green', 'Arctic White'],
            'storages': ['256GB', '512GB'],
            'launch_status': 'Pre-Orders Open • Limited Launch Batch'
        },
        {
            'brand': 'Google',
            'model': 'Pixel 9 Pro XL',
            'tagline': 'Gemini Nano AI Integration & Pro Camera Magic',
            'display': '6.8" Super Actua OLED 1-120Hz',
            'processor': 'Google Tensor G4 with Titan M2',
            'camera': '50MP Triple Pro Camera with Super Res Zoom 30x',
            'battery': '5,060 mAh Fast Wireless Charging',
            'image': 'https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=600&auto=format&fit=crop&q=80',
            'expected_price': 124999,
            'min_token': 3000,
            'colors': ['Obsidian', 'Porcelain', 'Hazel', 'Rose Quartz'],
            'storages': ['128GB', '256GB', '512GB'],
            'launch_status': 'Pre-Orders Open • Official Store Guarantee'
        }
    ]

    return render_template('preorders/public_prebook.html', flagships=flagships, config=Config)


@public_prebook_bp.route('/submit', methods=['POST'])
def public_submit():
    """Customer self-books online from their phone."""
    try:
        cust_name = request.form.get('name', '').strip()
        cust_phone = request.form.get('phone', '').strip()
        cust_email = request.form.get('email', '').strip() or None
        cust_address = request.form.get('city_address', '').strip() or None

        brand = request.form.get('brand', '').strip()
        model = request.form.get('model', '').strip()
        storage = request.form.get('storage', '256GB').strip()
        color = request.form.get('color', 'Default').strip()
        variant = f"{storage} - {color}"

        expected_price = float(request.form.get('expected_price', 0) or 0)
        token_advance = float(request.form.get('token_advance', 2000) or 2000)
        pay_option = request.form.get('payment_option', 'upi')  # 'upi' or 'store'

        if not cust_name or not cust_phone or not brand or not model:
            flash("Please fill in your name, mobile number, and device preference.", "error")
            return redirect(url_for('prebook.public_showcase'))

        # Customer matching or creation
        customer = Customer.query.filter_by(phone=cust_phone).first()
        if not customer:
            customer = Customer(name=cust_name, phone=cust_phone, email=cust_email, address=cust_address)
            db.session.add(customer)
            db.session.flush()

        booking_no = generate_booking_number()
        priority = calculate_next_queue_priority(brand, model)

        pay_mode_label = 'Online UPI' if pay_option == 'upi' else 'Pay at Store'
        pay_status_label = 'Paid' if pay_option == 'upi' else 'Pending'

        booking = PreBooking(
            booking_no=booking_no,
            customer_id=customer.id,
            brand=brand,
            model=model,
            variant=variant,
            color=color,
            storage=storage,
            expected_price=expected_price,
            token_advance=token_advance,
            payment_mode=pay_mode_label,
            payment_status=pay_status_label,
            booking_source='Online_Self_Book',
            queue_priority=priority,
            status='Booked',
            notes=f"Self-booked via Public Portal on {datetime.utcnow().strftime('%d-%b-%Y')}"
        )
        db.session.add(booking)
        db.session.commit()

        # Dispatch pre-order confirmation to customer via Gmail
        if customer.email:
            try:
                host_url = request.host_url
                send_email_preorder_confirmation(booking, recipient_email=customer.email, host_url=host_url)
            except Exception as mail_err:
                print(f"[ONLINE PREORDER MAIL ERROR] {mail_err}")

        return redirect(url_for('prebook.digital_pass', booking_no=booking_no))

    except Exception as e:
        db.session.rollback()
        flash(f"Booking could not be processed: {str(e)}", "error")
        return redirect(url_for('prebook.public_showcase'))


@public_prebook_bp.route('/pass/<booking_no>')
def digital_pass(booking_no):
    """
    Public live digital pass for the customer showing real-time queue position,
    payment voucher, and pickup instructions.
    """
    booking = PreBooking.query.filter_by(booking_no=booking_no).first()
    if not booking:
        flash("Booking record not found.", "error")
        return redirect(url_for('prebook.public_showcase'))

    # Build UPI payment link for token advance or balance
    upi_pa = Config.UPI_ID if hasattr(Config, 'UPI_ID') and Config.UPI_ID else "mobix@icici"
    upi_pn = Config.SHOP_NAME.replace(" ", "%20")
    upi_link = f"upi://pay?pa={upi_pa}&pn={upi_pn}&am={booking.token_advance}&cu=INR&tn=Booking_{booking.booking_no}"

    # WhatsApp share link
    host_url = request.host_url
    wa_msg = build_whatsapp_preorder_confirmation(booking, host_url=host_url)
    wa_url = get_whatsapp_url(booking.customer.phone, wa_msg)

    return render_template(
        'preorders/public_pass.html',
        booking=booking,
        upi_link=upi_link,
        whatsapp_url=wa_url,
        config=Config
    )


@public_prebook_bp.route('/track')
def track_lookup():
    """Search for existing pre-order by booking number or phone."""
    q = request.args.get('q', '').strip()
    if q:
        booking = PreBooking.query.join(Customer).filter(
            or_(PreBooking.booking_no.ilike(f"%{q}%"), Customer.phone == q)
        ).order_by(PreBooking.created_at.desc()).first()
        if booking:
            return redirect(url_for('prebook.digital_pass', booking_no=booking.booking_no))
        flash(f"No active pre-order found matching '{q}'. Please verify your phone or booking number.", "error")

    return render_template('preorders/public_pass.html', booking=None, config=Config)


@public_prebook_bp.route('/pass/<booking_no>/cancel', methods=['POST'])
def public_cancel(booking_no):
    """Customer cancels their pre-booking online from digital pass."""
    booking = PreBooking.query.filter_by(booking_no=booking_no).first()
    if not booking:
        flash("Booking record not found.", "error")
        return redirect(url_for('prebook.public_showcase'))

    if booking.status in ['Fulfilled', 'Cancelled']:
        flash(f"This pre-order is already marked as {booking.status}.", "info")
        return redirect(url_for('prebook.digital_pass', booking_no=booking_no))

    # Release device if reserved
    if booking.allocated_mobile:
        booking.allocated_mobile.status = 'in_stock'
        booking.allocated_mobile_id = None

    reason = request.form.get('reason', 'Cancelled online by customer').strip()
    booking.status = 'Cancelled'
    booking.notes = f"{booking.notes or ''} | CANCELLED ONLINE: {reason} (Advance ₹{booking.token_advance:,.2f} refund pending store claim)".strip(" | ")
    db.session.commit()

    flash(f"Pre-Order #{booking.booking_no} has been cancelled successfully. Please visit our store or call {Config.SHOP_PHONE} to collect your advance refund.", "info")
    return redirect(url_for('prebook.digital_pass', booking_no=booking_no))

