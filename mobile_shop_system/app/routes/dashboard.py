from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import db, User, Customer, Bill, EMI, Product, Repair, Supplier
from datetime import datetime, timedelta
import json

bp = Blueprint('dashboard', __name__)

@bp.route('/dashboard')
@login_required
def dashboard_home():
    today = datetime.utcnow().date()
    this_month_start = today.replace(day=1)
    
    today_sales = Bill.query.filter(
        Bill.bill_date >= today,
        Bill.is_cancelled == False
    ).with_entities(db.func.sum(Bill.total_amount)).scalar() or 0
    
    total_sales = Bill.query.filter(Bill.is_cancelled == False).with_entities(db.func.sum(Bill.total_amount)).scalar() or 0
    
    pending_emi = EMI.query.filter(EMI.status == 'pending').count()
    overdue_emi = EMI.query.filter(EMI.due_date < today, EMI.status.in_(['pending', 'partial'])).count()
    
    low_stock = Product.query.filter(Product.quantity_in_stock <= Product.min_stock_level, Product.is_active == True).count()
    repair_orders = Repair.query.filter(Repair.status.in_(['received', 'diagnosing', 'in_progress', 'waiting_parts'])).count()
    supplier_due = Supplier.query.with_entities(db.func.sum(Supplier.current_balance)).scalar() or 0
    
    recent_transactions = Bill.query.filter(Bill.is_cancelled == False).order_by(Bill.created_at.desc()).limit(10).all()
    recent_emis = EMI.query.filter(EMI.status.in_(['pending', 'overdue'])).order_by(EMI.due_date.asc()).limit(5).all()
    
    monthly_sales_data = []
    for i in range(6):
        month_start = (this_month_start - timedelta(days=30*i)).replace(day=1)
        if i == 0:
            month_end = today
        else:
            month_end = (this_month_start - timedelta(days=30*(i+1))).replace(day=1) - timedelta(days=1)
        month_sales = Bill.query.filter(
            Bill.bill_date >= month_start,
            Bill.bill_date <= month_end,
            Bill.is_cancelled == False
        ).with_entities(db.func.sum(Bill.total_amount)).scalar() or 0
        monthly_sales_data.append({'month': month_start.strftime('%b %Y'), 'sales': float(month_sales)})
    monthly_sales_data.reverse()
    
    return render_template('dashboard.html',
        today_sales=today_sales, total_sales=total_sales,
        pending_emi=pending_emi, overdue_emi=overdue_emi, low_stock=low_stock,
        repair_orders=repair_orders, supplier_due=supplier_due,
        recent_transactions=recent_transactions, recent_emis=recent_emis,
        monthly_sales_data=json.dumps(monthly_sales_data) if monthly_sales_data else '[]')