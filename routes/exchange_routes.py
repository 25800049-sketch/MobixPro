"""
AI Exchange & Old Phone Valuation Controller
Calculates machine learning depreciation valuation for trade-ins.
"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from models import db, ExchangeRecord, Customer
from routes.auth_routes import login_required, roles_accepted
from services.ai_valuation import valuation_engine

exchange_bp = Blueprint('exchange', __name__, url_prefix='/exchange')

@exchange_bp.route('/')
@login_required
@roles_accepted('admin', 'cashier')
def exchange_page():
    records = ExchangeRecord.query.order_by(ExchangeRecord.created_at.desc()).limit(15).all()
    customers = Customer.query.order_by(Customer.name.asc()).all()
    return render_template('exchange/exchange.html', records=records, customers=customers)

@exchange_bp.route('/api/predict', methods=['POST'])
@login_required
@roles_accepted('admin', 'cashier')
def predict_valuation():
    """AI Endpoint to predict fair market valuation and exchange quote."""
    try:
        data = request.get_json() or request.form
        
        brand = data.get('brand', 'Samsung')
        model_name = data.get('model', 'Galaxy Phone')
        original_price = float(data.get('original_price', 25000))
        age_months = int(data.get('age_months', 12))
        storage = data.get('storage', '128GB')
        battery_health = int(data.get('battery_health', 85))
        screen_condition = data.get('screen_condition', 'Good')
        body_condition = data.get('body_condition', 'Good')
        camera_ok = str(data.get('camera_ok', 'true')).lower() in ('true', '1', 'on')
        biometrics_ok = str(data.get('biometrics_ok', 'true')).lower() in ('true', '1', 'on')

        result = valuation_engine.evaluate_phone(
            brand=brand,
            model_name=model_name,
            original_price=original_price,
            age_months=age_months,
            storage_str=storage,
            battery_health=battery_health,
            screen_cond=screen_condition,
            body_cond=body_condition,
            camera_ok=camera_ok,
            biometrics_ok=biometrics_ok
        )
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@exchange_bp.route('/save-record', methods=['POST'])
@login_required
def save_record():
    try:
        customer_id = request.form.get('customer_id')
        brand = request.form.get('brand')
        model = request.form.get('model')
        imei = request.form.get('imei')
        original_price = float(request.form.get('original_price', 20000))
        age_months = int(request.form.get('age_months', 12))
        storage = request.form.get('storage', '128GB')
        battery_health = int(request.form.get('battery_health', 85))
        condition_screen = request.form.get('condition_screen', 'Good')
        condition_body = request.form.get('condition_body', 'Good')
        ai_estimated_value = float(request.form.get('ai_estimated_value', 0))
        offered_value = float(request.form.get('offered_value', 0))

        record = ExchangeRecord(
            customer_id=int(customer_id) if customer_id and customer_id != 'new' else None,
            brand=brand,
            model=model,
            imei=imei or None,
            original_price=original_price,
            age_months=age_months,
            storage=storage,
            battery_health=battery_health,
            condition_screen=condition_screen,
            condition_body=condition_body,
            ai_estimated_value=ai_estimated_value,
            offered_value=offered_value,
            status='Evaluated'
        )
        db.session.add(record)
        db.session.commit()
        flash(f"Valuation recorded for {brand} {model} (Offered: ₹{offered_value:,.2f}).", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error saving valuation: {str(e)}", "danger")

    return redirect(url_for('exchange.exchange_page'))
