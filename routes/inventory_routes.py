"""
Inventory Management Blueprint
Handles Mobile devices with IMEI tracking and Accessories with category management.
"""
import threading
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from models import db, Mobile, Accessory, PreBooking
from routes.auth_routes import login_required, roles_accepted
from services.notification_service import send_email_stock_arrival, async_send_stock_arrival

inventory_bp = Blueprint('inventory', __name__, url_prefix='/inventory')

# ==================== MOBILES ====================

@inventory_bp.route('/mobiles')
@login_required
@roles_accepted('admin', 'cashier')
def mobiles_list():
    query = request.args.get('q', '').strip()
    brand_filter = request.args.get('brand', '').strip()
    
    mobiles_q = Mobile.query
    if query:
        mobiles_q = mobiles_q.filter(
            (Mobile.model.ilike(f'%{query}%')) |
            (Mobile.brand.ilike(f'%{query}%')) |
            (Mobile.imei_1.ilike(f'%{query}%')) |
            (Mobile.imei_2.ilike(f'%{query}%'))
        )
    if brand_filter:
        mobiles_q = mobiles_q.filter(Mobile.brand.ilike(brand_filter))
        
    mobiles = mobiles_q.order_by(Mobile.created_at.desc()).all()
    brands = db.session.query(Mobile.brand).distinct().all()
    brand_list = [b[0] for b in brands if b[0]]

    return render_template('inventory/mobiles.html', mobiles=mobiles, brands=brand_list, q=query, selected_brand=brand_filter)

@inventory_bp.route('/mobiles/add', methods=['POST'])
@login_required
@roles_accepted('admin', 'cashier')
def add_mobile():
    try:
        brand = request.form.get('brand', '').strip()
        model = request.form.get('model', '').strip()
        imei_1 = request.form.get('imei_1', '').strip()
        imei_2 = request.form.get('imei_2', '').strip()
        ram = request.form.get('ram', '').strip()
        storage = request.form.get('storage', '').strip()
        color = request.form.get('color', '').strip()
        purchase_price = float(request.form.get('purchase_price', 0))
        selling_price = float(request.form.get('selling_price', 0))
        stock_quantity = int(request.form.get('stock_quantity', 1))
        warranty_months = int(request.form.get('warranty_months', 12))
        min_stock_alert = int(request.form.get('min_stock_alert', 2))

        image_url = request.form.get('image_url', '').strip() or None
        display = request.form.get('display', '').strip() or '6.7" AMOLED 120Hz'
        processor = request.form.get('processor', '').strip() or 'Octa-core 5G Processor'
        camera = request.form.get('camera', '').strip() or '50MP OIS Camera'
        battery = request.form.get('battery', '').strip() or '5000 mAh Fast Charging'

        # Check duplicate IMEI
        existing = Mobile.query.filter_by(imei_1=imei_1).first()
        if existing:
            flash(f"Mobile with IMEI-1 '{imei_1}' already exists in inventory!", "danger")
            return redirect(url_for('inventory.mobiles_list'))

        mobile = Mobile(
            brand=brand,
            model=model,
            imei_1=imei_1,
            imei_2=imei_2 or None,
            ram=ram,
            storage=storage,
            color=color,
            purchase_price=purchase_price,
            selling_price=selling_price,
            stock_quantity=stock_quantity,
            image_url=image_url,
            display=display,
            processor=processor,
            camera=camera,
            battery=battery,
            warranty_months=warranty_months,
            min_stock_alert=min_stock_alert,
            status='in_stock'
        )
        db.session.add(mobile)
        db.session.commit()

        # Check for waiting pre-orders for this brand and model
        waiting_booking = PreBooking.query.filter(
            PreBooking.status == 'Booked',
            PreBooking.brand.ilike(brand),
            PreBooking.model.ilike(f"%{model}%")
        ).order_by(PreBooking.queue_priority.asc(), PreBooking.created_at.asc()).first()

        if waiting_booking:
            waiting_booking.allocated_mobile_id = mobile.id
            waiting_booking.status = 'Allocated'
            mobile.status = 'reserved'
            db.session.commit()

            if waiting_booking.customer and waiting_booking.customer.email:
                try:
                    host_url = request.host_url
                    send_email_stock_arrival(waiting_booking, recipient_email=waiting_booking.customer.email, host_url=host_url)
                except Exception as mail_err:
                    print(f"[STOCK ARRIVAL INVENTORY ERROR] {mail_err}")

            flash(f"Added {brand} {model} (IMEI: {imei_1}). Auto-allocated to Pre-Order #{waiting_booking.booking_no} and stock arrival email sent via Gmail!", "success")
        else:
            flash(f"Added {brand} {model} (IMEI: {imei_1}) to inventory successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error adding mobile: {str(e)}", "danger")

    return redirect(url_for('inventory.mobiles_list'))

@inventory_bp.route('/mobiles/<int:mobile_id>/edit', methods=['POST'])
@login_required
@roles_accepted('admin', 'cashier')
def edit_mobile(mobile_id):
    mobile = db.session.get(Mobile, mobile_id)
    if not mobile:
        flash("Mobile device not found.", "danger")
        return redirect(url_for('inventory.mobiles_list'))

    try:
        mobile.brand = request.form.get('brand', mobile.brand)
        mobile.model = request.form.get('model', mobile.model)
        mobile.imei_1 = request.form.get('imei_1', mobile.imei_1)
        mobile.imei_2 = request.form.get('imei_2', mobile.imei_2)
        mobile.ram = request.form.get('ram', mobile.ram)
        mobile.storage = request.form.get('storage', mobile.storage)
        mobile.color = request.form.get('color', mobile.color)
        mobile.purchase_price = float(request.form.get('purchase_price', mobile.purchase_price))
        mobile.selling_price = float(request.form.get('selling_price', mobile.selling_price))
        mobile.stock_quantity = int(request.form.get('stock_quantity', mobile.stock_quantity))
        mobile.image_url = request.form.get('image_url', mobile.image_url)
        mobile.display = request.form.get('display', mobile.display)
        mobile.processor = request.form.get('processor', mobile.processor)
        mobile.camera = request.form.get('camera', mobile.camera)
        mobile.battery = request.form.get('battery', mobile.battery)
        mobile.warranty_months = int(request.form.get('warranty_months', mobile.warranty_months))
        mobile.min_stock_alert = int(request.form.get('min_stock_alert', mobile.min_stock_alert))
        mobile.status = 'in_stock' if mobile.stock_quantity > 0 else 'sold'

        db.session.commit()
        flash(f"Updated {mobile.brand} {mobile.model} successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error updating mobile: {str(e)}", "danger")

    return redirect(url_for('inventory.mobiles_list'))

@inventory_bp.route('/mobiles/<int:mobile_id>/delete', methods=['POST'])
@login_required
@roles_accepted('admin')
def delete_mobile(mobile_id):
    mobile = db.session.get(Mobile, mobile_id)
    if mobile:
        db.session.delete(mobile)
        db.session.commit()
        flash("Mobile removed from inventory.", "info")
    return redirect(url_for('inventory.mobiles_list'))

# ==================== ACCESSORIES ====================

@inventory_bp.route('/accessories')
@login_required
@roles_accepted('admin', 'cashier')
def accessories_list():
    query = request.args.get('q', '').strip()
    category_filter = request.args.get('category', '').strip()

    acc_q = Accessory.query
    if query:
        acc_q = acc_q.filter(
            (Accessory.name.ilike(f'%{query}%')) |
            (Accessory.brand.ilike(f'%{query}%'))
        )
    if category_filter:
        acc_q = acc_q.filter_by(category=category_filter)

    accessories = acc_q.order_by(Accessory.created_at.desc()).all()
    categories = [
        'Chargers', 'Earphones', 'Power banks', 'Cases & Covers',
        'Screen Protectors', 'Cables', 'Smart Watches', 'Adapters', 'Other Accessories'
    ]

    return render_template(
        'inventory/accessories.html',
        accessories=accessories,
        categories=categories,
        q=query,
        selected_category=category_filter
    )

@inventory_bp.route('/accessories/add', methods=['POST'])
@login_required
@roles_accepted('admin', 'cashier')
def add_accessory():
    try:
        name = request.form.get('name', '').strip()
        category = request.form.get('category', 'Other Accessories')
        brand = request.form.get('brand', '').strip()
        compatibility = request.form.get('compatibility', 'Universal').strip()
        purchase_price = float(request.form.get('purchase_price', 0))
        selling_price = float(request.form.get('selling_price', 0))
        stock_quantity = int(request.form.get('stock_quantity', 0))
        min_stock_alert = int(request.form.get('min_stock_alert', 5))

        acc = Accessory(
            name=name,
            category=category,
            brand=brand,
            compatibility=compatibility,
            purchase_price=purchase_price,
            selling_price=selling_price,
            stock_quantity=stock_quantity,
            min_stock_alert=min_stock_alert
        )
        db.session.add(acc)
        db.session.commit()
        flash(f"Added accessory '{name}' to stock successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error adding accessory: {str(e)}", "danger")

    return redirect(url_for('inventory.accessories_list'))

@inventory_bp.route('/accessories/<int:acc_id>/edit', methods=['POST'])
@login_required
@roles_accepted('admin', 'cashier')
def edit_accessory(acc_id):
    acc = db.session.get(Accessory, acc_id)
    if not acc:
        flash("Accessory not found.", "danger")
        return redirect(url_for('inventory.accessories_list'))

    try:
        acc.name = request.form.get('name', acc.name)
        acc.category = request.form.get('category', acc.category)
        acc.brand = request.form.get('brand', acc.brand)
        acc.compatibility = request.form.get('compatibility', acc.compatibility)
        acc.purchase_price = float(request.form.get('purchase_price', acc.purchase_price))
        acc.selling_price = float(request.form.get('selling_price', acc.selling_price))
        acc.stock_quantity = int(request.form.get('stock_quantity', acc.stock_quantity))
        acc.min_stock_alert = int(request.form.get('min_stock_alert', acc.min_stock_alert))

        db.session.commit()
        flash(f"Updated accessory '{acc.name}'.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error updating accessory: {str(e)}", "danger")

    return redirect(url_for('inventory.accessories_list'))

@inventory_bp.route('/accessories/<int:acc_id>/adjust-stock', methods=['POST'])
@login_required
@roles_accepted('admin', 'cashier')
def adjust_accessory_stock(acc_id):
    acc = db.session.get(Accessory, acc_id)
    if not acc:
        return jsonify({'success': False, 'message': 'Not found'}), 404
        
    change = int(request.form.get('change', 0))
    acc.stock_quantity = max(0, acc.stock_quantity + change)
    db.session.commit()
    return jsonify({
        'success': True,
        'new_stock': acc.stock_quantity,
        'min_stock_alert': acc.min_stock_alert,
        'is_low_stock': acc.stock_quantity <= acc.min_stock_alert
    })

@inventory_bp.route('/accessories/<int:acc_id>/delete', methods=['POST'])
@login_required
@roles_accepted('admin')
def delete_accessory(acc_id):
    acc = db.session.get(Accessory, acc_id)
    if acc:
        name = acc.name
        db.session.delete(acc)
        db.session.commit()
        flash(f"Accessory '{name}' removed from stock.", "info")
    else:
        flash("Accessory not found.", "danger")
    return redirect(url_for('inventory.accessories_list'))

# ==================== SEARCH API FOR POS ====================

@inventory_bp.route('/api/search')
@login_required
@roles_accepted('admin', 'cashier')
def search_items_api():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])

    results = []
    # Search mobiles in stock
    mobiles = Mobile.query.filter(
        Mobile.stock_quantity > 0,
        (Mobile.model.ilike(f'%{query}%')) |
        (Mobile.brand.ilike(f'%{query}%')) |
        (Mobile.imei_1.ilike(f'%{query}%')) |
        (Mobile.imei_2.ilike(f'%{query}%'))
    ).limit(8).all()

    for m in mobiles:
        results.append({
            'id': m.id,
            'type': 'mobile',
            'name': f"{m.brand} {m.model} ({m.ram}/{m.storage}, {m.color})",
            'imei': m.imei_1,
            'price': m.selling_price,
            'stock': m.stock_quantity,
            'warranty': f"{m.warranty_months} Months"
        })

    # Search accessories in stock
    accessories = Accessory.query.filter(
        Accessory.stock_quantity > 0,
        (Accessory.name.ilike(f'%{query}%')) |
        (Accessory.brand.ilike(f'%{query}%')) |
        (Accessory.category.ilike(f'%{query}%'))
    ).limit(8).all()

    for a in accessories:
        results.append({
            'id': a.id,
            'type': 'accessory',
            'name': f"{a.name} ({a.category})",
            'imei': '',
            'price': a.selling_price,
            'stock': a.stock_quantity,
            'warranty': "7 Days"
        })

    return jsonify(results)
