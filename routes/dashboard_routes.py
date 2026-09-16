"""
Dashboard & Analytics Controller
Provides real-time business metrics, KPI cards, low-stock warnings,
EMI overdue notifications, and Chart.js analytics.
"""
from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, jsonify, redirect, url_for, session
from sqlalchemy import func
from models import db, Mobile, Accessory, Invoice, InvoiceItem, EMIAccount, EMIInstallment, RepairTicket, Supplier, Customer
from routes.auth_routes import login_required, roles_accepted
from services.emi_service import refresh_all_overdue_emis

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    if session.get('role') == 'technician':
        return redirect(url_for('repairs.repair_list'))

    # Trigger auto-overdue fine recalculation
    refresh_all_overdue_emis()

    today_start = datetime.combine(date.today(), datetime.min.time())
    
    # 1. Sales Metrics
    total_sales = db.session.query(func.sum(Invoice.final_total)).scalar() or 0.0
    today_sales = db.session.query(func.sum(Invoice.final_total)).filter(Invoice.created_at >= today_start).scalar() or 0.0
    total_invoices_count = Invoice.query.count()
    today_invoices_count = Invoice.query.filter(Invoice.created_at >= today_start).count()

    # 2. Customers
    total_customers_count = Customer.query.count()

    # 3. EMI Metrics
    active_emis_count = EMIAccount.query.filter_by(status='Active').count()
    overdue_emis_count = EMIAccount.query.filter_by(status='Overdue').count()
    
    overdue_installments = EMIInstallment.query.filter(
        EMIInstallment.status == 'overdue'
    ).all()
    total_overdue_amount = sum(inst.total_due for inst in overdue_installments)

    # 4. Inventory & Low-Stock Alerts
    total_mobile_models = Mobile.query.count()
    total_accessory_items = Accessory.query.count()
    total_mobiles = db.session.query(func.sum(Mobile.stock_quantity)).scalar() or 0
    total_accessories = db.session.query(func.sum(Accessory.stock_quantity)).scalar() or 0
    
    low_stock_mobiles = Mobile.query.filter(Mobile.stock_quantity <= Mobile.min_stock_alert).all()
    low_stock_accessories = Accessory.query.filter(Accessory.stock_quantity <= Accessory.min_stock_alert).all()
    total_low_stock = len(low_stock_mobiles) + len(low_stock_accessories)

    # 5. Repair Orders
    active_repairs_count = RepairTicket.query.filter(RepairTicket.status.notin_(['Delivered'])).count()
    ready_repairs_count = RepairTicket.query.filter_by(status='Ready').count()

    # 6. Supplier Dues
    total_supplier_dues = db.session.query(func.sum(Supplier.balance_due)).scalar() or 0.0

    # 7. Recent Invoices & Repairs
    recent_invoices = Invoice.query.order_by(Invoice.created_at.desc()).limit(7).all()
    recent_repairs = RepairTicket.query.order_by(RepairTicket.created_at.desc()).limit(5).all()

    kpi_data = {
        'total_products': total_mobile_models + total_accessory_items,
        'in_stock': total_mobiles + total_accessories,
        'total_sales': round(total_sales, 2),
        'total_customers': total_customers_count,
        'today_sales': round(today_sales, 2),
        'today_invoices': today_invoices_count,
        'total_invoices': total_invoices_count,
        'active_emis': active_emis_count,
        'overdue_emis': overdue_emis_count,
        'total_overdue_amount': round(total_overdue_amount, 2),
        'total_inventory': total_mobiles + total_accessories,
        'low_stock_count': total_low_stock,
        'active_repairs': active_repairs_count,
        'ready_repairs': ready_repairs_count,
        'supplier_dues': round(total_supplier_dues, 2)
    }

    return render_template(
        'dashboard.html',
        kpi=kpi_data,
        low_stock_mobiles=low_stock_mobiles,
        low_stock_accessories=low_stock_accessories,
        recent_invoices=recent_invoices,
        recent_repairs=recent_repairs,
        overdue_installments=overdue_installments[:6]
    )

@dashboard_bp.route('/api/dashboard/charts')
@login_required
@roles_accepted('admin', 'cashier')
def charts_api():
    """Returns dynamic data for Chart.js (7-day sales and brand breakdown)."""
    # Last 7 days sales
    dates = []
    daily_sales = []
    daily_counts = []

    today = date.today()
    for i in range(6, -1, -1):
        target_d = today - timedelta(days=i)
        start_d = datetime.combine(target_d, datetime.min.time())
        end_d = datetime.combine(target_d, datetime.max.time())
        
        sum_sales = db.session.query(func.sum(Invoice.final_total)).filter(
            Invoice.created_at >= start_d,
            Invoice.created_at <= end_d
        ).scalar() or 0.0

        count_inv = Invoice.query.filter(
            Invoice.created_at >= start_d,
            Invoice.created_at <= end_d
        ).count()

        dates.append(target_d.strftime('%b %d'))
        daily_sales.append(round(sum_sales, 2))
        daily_counts.append(count_inv)

    # Category & Brand breakdown
    brand_counts = db.session.query(Mobile.brand, func.sum(Mobile.stock_quantity))\
        .group_by(Mobile.brand).order_by(func.sum(Mobile.stock_quantity).desc()).limit(5).all()
    
    brand_labels = [b[0] for b in brand_counts] if brand_counts else ['Apple', 'Samsung', 'OnePlus', 'Xiaomi', 'Realme']
    brand_values = [b[1] or 1 for b in brand_counts] if brand_counts else [35, 28, 20, 15, 10]

    return jsonify({
        'sales_trend': {
            'labels': dates,
            'sales': daily_sales,
            'counts': daily_counts
        },
        'brand_split': {
            'labels': brand_labels,
            'values': brand_values
        }
    })
