from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='cashier')  # 'admin', 'cashier', 'technician'
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Salary & Attendance settings
    monthly_salary = db.Column(db.Float, default=18000.0)
    daily_rate = db.Column(db.Float, default=692.31)
    salary_type = db.Column(db.String(20), default='monthly')  # 'monthly', 'daily_wage'

    # Relationships
    invoices = db.relationship('Invoice', backref='cashier', lazy=True)
    assigned_repairs = db.relationship('RepairTicket', backref='technician', lazy=True)
    attendances = db.relationship('Attendance', backref='user', lazy=True, cascade="all, delete-orphan")
    salary_advances = db.relationship('SalaryAdvance', backref='user', lazy=True, cascade="all, delete-orphan")
    payroll_records = db.relationship('PayrollRecord', backref='user', lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'full_name': self.full_name,
            'role': self.role,
            'email': self.email,
            'phone': self.phone,
            'is_active': self.is_active,
            'monthly_salary': self.monthly_salary or 18000.0,
            'daily_rate': self.daily_rate or 692.31,
            'salary_type': self.salary_type or 'monthly'
        }


class Customer(db.Model):
    __tablename__ = 'customers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=False, index=True)
    email = db.Column(db.String(120), nullable=True)
    address = db.Column(db.Text, nullable=True)
    outstanding_balance = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    invoices = db.relationship('Invoice', backref='customer', lazy=True, order_by='desc(Invoice.created_at)')
    emi_accounts = db.relationship('EMIAccount', backref='customer', lazy=True)
    repairs = db.relationship('RepairTicket', backref='customer', lazy=True, order_by='desc(RepairTicket.created_at)')
    exchanges = db.relationship('ExchangeRecord', backref='customer', lazy=True)
    pre_bookings = db.relationship('PreBooking', backref='customer', lazy=True, order_by='desc(PreBooking.created_at)')

    def get_credit_profile(self):
        """
        Calculates CIBIL-style credit score (300-900), risk tier, and repayment statistics.
        Tier-A (750-900): Low Risk / Excellent
        Tier-B (600-749): Moderate Risk
        Tier-C (300-599): High Risk / Defaulter Warning
        """
        base_score = 720 # Baseline for registered customer
        
        # 1. Past invoice spending history factor
        total_spent = sum((inv.final_total or 0.0) for inv in self.invoices)
        order_count = len(self.invoices)
        base_score += min(50, order_count * 10)
        
        # 2. EMI repayment behavior factor
        all_installments = []
        for acc in self.emi_accounts:
            all_installments.extend(acc.installments)

        total_installments = len(all_installments)
        paid_on_time = 0
        overdue_count = 0
        severe_overdue_count = 0 # overdue >= 15 days
        today = date.today()

        for inst in all_installments:
            if inst.status == 'paid':
                paid_on_time += 1
                base_score += 15
            elif inst.status == 'overdue':
                overdue_count += 1
                base_score -= 40
                if inst.due_date and (today - inst.due_date).days >= 15:
                    severe_overdue_count += 1
                    base_score -= 60

        # 3. Debt-to-Spend balance factor
        active_debt = self.outstanding_balance or 0.0
        if total_spent > 0:
            debt_ratio = active_debt / total_spent
            if debt_ratio > 0.6:
                base_score -= 50
            elif debt_ratio < 0.2 and active_debt == 0:
                base_score += 30

        # Clamp between 300 and 900
        score = max(300, min(900, round(base_score)))

        if score >= 750:
            tier = 'Tier-A'
            tier_label = 'Excellent (Low Risk)'
            badge_class = 'badge-success'
            max_recommended_emi = 120000.0
            down_payment_min_pct = 0 # 0% down-payment eligible
        elif score >= 600:
            tier = 'Tier-B'
            tier_label = 'Moderate Risk'
            badge_class = 'badge-warning'
            max_recommended_emi = 50000.0
            down_payment_min_pct = 25 # 25% down-payment
        else:
            tier = 'Tier-C'
            tier_label = 'High Risk (Defaulter Alert)'
            badge_class = 'badge-danger'
            max_recommended_emi = 20000.0
            down_payment_min_pct = 50 # 50%+ down-payment or guarantor

        on_time_ratio = round((paid_on_time / total_installments * 100), 1) if total_installments > 0 else 100.0

        return {
            'score': score,
            'tier': tier,
            'tier_label': tier_label,
            'badge_class': badge_class,
            'total_spent': round(total_spent, 2),
            'active_debt': round(active_debt, 2),
            'total_installments': total_installments,
            'paid_on_time': paid_on_time,
            'overdue_count': overdue_count,
            'severe_overdue_count': severe_overdue_count,
            'on_time_ratio': on_time_ratio,
            'max_recommended_emi': max_recommended_emi,
            'down_payment_min_pct': down_payment_min_pct
        }

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'phone': self.phone,
            'email': self.email or '',
            'address': self.address or '',
            'outstanding_balance': round(self.outstanding_balance or 0, 2),
            'created_at': self.created_at.strftime('%Y-%m-%d')
        }


class Supplier(db.Model):
    __tablename__ = 'suppliers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    company = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    address = db.Column(db.Text, nullable=True)
    balance_due = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    purchases = db.relationship('SupplierPurchase', backref='supplier', lazy=True, order_by='desc(SupplierPurchase.purchase_date)')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'company': self.company,
            'phone': self.phone,
            'email': self.email or '',
            'address': self.address or '',
            'balance_due': round(self.balance_due or 0, 2)
        }


class Mobile(db.Model):
    __tablename__ = 'mobiles'

    id = db.Column(db.Integer, primary_key=True)
    brand = db.Column(db.String(64), nullable=False, index=True)
    model = db.Column(db.String(100), nullable=False, index=True)
    imei_1 = db.Column(db.String(30), unique=True, nullable=False, index=True)
    imei_2 = db.Column(db.String(30), nullable=True)
    ram = db.Column(db.String(20), nullable=False)  # e.g., '8GB'
    storage = db.Column(db.String(20), nullable=False)  # e.g., '128GB'
    color = db.Column(db.String(40), nullable=False)
    purchase_price = db.Column(db.Float, nullable=False)
    selling_price = db.Column(db.Float, nullable=False)
    stock_quantity = db.Column(db.Integer, default=1)
    image_url = db.Column(db.String(350), nullable=True)
    display = db.Column(db.String(120), nullable=True, default='6.7" FHD+ AMOLED 120Hz')
    processor = db.Column(db.String(120), nullable=True, default='Octa-core 5G Processor')
    camera = db.Column(db.String(120), nullable=True, default='50MP OIS Triple Rear Camera')
    battery = db.Column(db.String(80), nullable=True, default='5000 mAh Fast Charging')
    warranty_months = db.Column(db.Integer, default=12)
    status = db.Column(db.String(20), default='in_stock')  # 'in_stock', 'sold', 'reserved'
    min_stock_alert = db.Column(db.Integer, default=2)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'brand': self.brand,
            'model': self.model,
            'imei_1': self.imei_1,
            'imei_2': self.imei_2 or '',
            'ram': self.ram,
            'storage': self.storage,
            'color': self.color,
            'purchase_price': self.purchase_price,
            'selling_price': self.selling_price,
            'stock_quantity': self.stock_quantity,
            'image_url': self.image_url or 'https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=400&auto=format&fit=crop&q=80',
            'display': self.display or '6.7" AMOLED 120Hz',
            'processor': self.processor or 'Octa-core 5G Processor',
            'camera': self.camera or '50MP OIS Camera',
            'battery': self.battery or '5000 mAh Battery',
            'warranty_months': self.warranty_months,
            'status': self.status,
            'is_low_stock': self.stock_quantity <= self.min_stock_alert
        }


class Accessory(db.Model):
    __tablename__ = 'accessories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    category = db.Column(db.String(60), nullable=False, index=True)  # Chargers, Earphones, Cases, etc.
    brand = db.Column(db.String(60), nullable=True)
    compatibility = db.Column(db.String(120), nullable=True)
    purchase_price = db.Column(db.Float, nullable=False)
    selling_price = db.Column(db.Float, nullable=False)
    stock_quantity = db.Column(db.Integer, default=0)
    min_stock_alert = db.Column(db.Integer, default=5)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'brand': self.brand or '',
            'compatibility': self.compatibility or 'Universal',
            'purchase_price': self.purchase_price,
            'selling_price': self.selling_price,
            'stock_quantity': self.stock_quantity,
            'min_stock_alert': self.min_stock_alert,
            'is_low_stock': self.stock_quantity <= self.min_stock_alert
        }


class Invoice(db.Model):
    __tablename__ = 'invoices'

    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    subtotal = db.Column(db.Float, default=0.0)
    tax_rate = db.Column(db.Float, default=18.0)  # GST %
    tax_amount = db.Column(db.Float, default=0.0)
    discount_amount = db.Column(db.Float, default=0.0)
    exchange_discount = db.Column(db.Float, default=0.0)
    final_total = db.Column(db.Float, default=0.0)
    
    payment_mode = db.Column(db.String(30), default='Cash')  # Cash, UPI, Card, EMI, Split
    payment_status = db.Column(db.String(20), default='Paid')  # Paid, Partial, Pending
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Relationships
    items = db.relationship('InvoiceItem', backref='invoice', lazy=True, cascade='all, delete-orphan')
    emi_account = db.relationship('EMIAccount', backref='invoice', uselist=False, lazy=True)
    exchange_record = db.relationship('ExchangeRecord', backref='invoice', uselist=False, lazy=True)
    pre_booking = db.relationship('PreBooking', backref='invoice', uselist=False, lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'invoice_number': self.invoice_number,
            'customer_name': self.customer.name if self.customer else 'Guest Customer',
            'customer_phone': self.customer.phone if self.customer else '',
            'cashier_name': self.cashier.full_name if self.cashier else 'System',
            'subtotal': round(self.subtotal, 2),
            'tax_amount': round(self.tax_amount, 2),
            'discount_amount': round(self.discount_amount, 2),
            'exchange_discount': round(self.exchange_discount, 2),
            'final_total': round(self.final_total, 2),
            'payment_mode': self.payment_mode,
            'payment_status': self.payment_status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M')
        }


class InvoiceItem(db.Model):
    __tablename__ = 'invoice_items'

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    item_type = db.Column(db.String(20), nullable=False)  # 'mobile', 'accessory'
    mobile_id = db.Column(db.Integer, db.ForeignKey('mobiles.id'), nullable=True)
    accessory_id = db.Column(db.Integer, db.ForeignKey('accessories.id'), nullable=True)
    item_name = db.Column(db.String(150), nullable=False)
    imei = db.Column(db.String(50), nullable=True)
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'item_type': self.item_type,
            'item_name': self.item_name,
            'imei': self.imei or '',
            'quantity': self.quantity,
            'unit_price': self.unit_price,
            'total_price': self.total_price
        }


class EMIAccount(db.Model):
    __tablename__ = 'emi_accounts'

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    down_payment = db.Column(db.Float, default=0.0)
    principal_remaining = db.Column(db.Float, nullable=False)
    emi_amount = db.Column(db.Float, nullable=False)
    tenure_months = db.Column(db.Integer, nullable=False)
    fine_per_cycle = db.Column(db.Float, default=200.0)  # Default ₹200 penalty for overdue
    start_date = db.Column(db.Date, default=date.today)
    status = db.Column(db.String(20), default='Active')  # 'Active', 'Completed', 'Overdue'
    notes = db.Column(db.String(200), nullable=True)

    # Relationships
    installments = db.relationship('EMIInstallment', backref='account', lazy=True, cascade='all, delete-orphan', order_by='EMIInstallment.installment_no')

    @property
    def max_days_overdue(self):
        today = date.today()
        days_list = [(today - i.due_date).days for i in self.installments if i.status == 'overdue' and i.due_date < today]
        return max(days_list) if days_list else 0

    @property
    def target_device_imei(self):
        if self.invoice and self.invoice.items:
            for it in self.invoice.items:
                if it.item_type == 'mobile' and it.imei:
                    return it.imei
        return '358901234567890'

    @property
    def target_device_name(self):
        if self.invoice and self.invoice.items:
            for it in self.invoice.items:
                if it.item_type == 'mobile':
                    return it.item_name
        return 'Financed Smartphone'

    def update_status(self):
        overdues = any(i.status == 'overdue' for i in self.installments)
        pending = any(i.status == 'pending' for i in self.installments)
        if overdues:
            self.status = 'Overdue'
        elif not pending:
            self.status = 'Completed'
        else:
            self.status = 'Active'

    def to_dict(self):
        return {
            'id': self.id,
            'invoice_number': self.invoice.invoice_number if self.invoice else '',
            'customer_name': self.customer.name if self.customer else '',
            'customer_phone': self.customer.phone if self.customer else '',
            'total_amount': self.total_amount,
            'down_payment': self.down_payment,
            'principal_remaining': self.principal_remaining,
            'emi_amount': self.emi_amount,
            'tenure_months': self.tenure_months,
            'fine_per_cycle': self.fine_per_cycle,
            'status': self.status,
            'start_date': self.start_date.strftime('%Y-%m-%d'),
            'max_days_overdue': self.max_days_overdue,
            'target_device_imei': self.target_device_imei,
            'target_device_name': self.target_device_name
        }


class EMIInstallment(db.Model):
    __tablename__ = 'emi_installments'

    id = db.Column(db.Integer, primary_key=True)
    emi_account_id = db.Column(db.Integer, db.ForeignKey('emi_accounts.id'), nullable=False)
    installment_no = db.Column(db.Integer, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    fine_amount = db.Column(db.Float, default=0.0)
    paid_amount = db.Column(db.Float, default=0.0)
    payment_date = db.Column(db.Date, nullable=True)
    payment_mode = db.Column(db.String(30), nullable=True)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'paid', 'overdue'

    @property
    def total_due(self):
        return round((self.amount + self.fine_amount) - self.paid_amount, 2)

    def to_dict(self):
        return {
            'id': self.id,
            'installment_no': self.installment_no,
            'due_date': self.due_date.strftime('%Y-%m-%d'),
            'amount': self.amount,
            'fine_amount': self.fine_amount,
            'paid_amount': self.paid_amount,
            'total_due': self.total_due,
            'payment_date': self.payment_date.strftime('%Y-%m-%d') if self.payment_date else '',
            'status': self.status
        }


class RepairTicket(db.Model):
    __tablename__ = 'repair_tickets'

    id = db.Column(db.Integer, primary_key=True)
    ticket_no = db.Column(db.String(40), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    technician_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    brand = db.Column(db.String(60), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    imei = db.Column(db.String(30), nullable=True)
    problem_description = db.Column(db.Text, nullable=False)
    
    estimated_cost = db.Column(db.Float, default=0.0)
    final_cost = db.Column(db.Float, default=0.0)
    advance_paid = db.Column(db.Float, default=0.0)
    
    status = db.Column(db.String(30), default='Received', index=True)
    # Statuses: 'Received' -> 'Diagnosing' -> 'Repairing' -> 'Ready' -> 'Delivered'
    
    parts_used = db.Column(db.Text, nullable=True)
    technician_notes = db.Column(db.Text, nullable=True)
    warranty_days = db.Column(db.Integer, default=30)
    delivery_date = db.Column(db.Date, nullable=True)
    payment_status = db.Column(db.String(20), default='Pending')  # 'Pending', 'Partial', 'Paid'
    payment_mode = db.Column(db.String(30), default='Cash')      # 'Cash', 'UPI', 'Card'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        effective_cost = self.final_cost if (self.final_cost and self.final_cost > 0) else self.estimated_cost
        bal = max(0.0, effective_cost - (self.advance_paid or 0.0))
        return {
            'id': self.id,
            'ticket_no': self.ticket_no,
            'customer_name': self.customer.name if self.customer else '',
            'customer_phone': self.customer.phone if self.customer else '',
            'technician_name': self.technician.full_name if self.technician else 'Unassigned',
            'brand': self.brand,
            'model': self.model,
            'imei': self.imei or '',
            'problem_description': self.problem_description,
            'estimated_cost': self.estimated_cost,
            'final_cost': self.final_cost,
            'advance_paid': self.advance_paid,
            'balance_due': round(bal, 2),
            'status': self.status,
            'payment_status': self.payment_status or ('Paid' if bal <= 0.01 else ('Partial' if self.advance_paid > 0 else 'Pending')),
            'payment_mode': self.payment_mode or 'Cash',
            'parts_used': self.parts_used or '',
            'technician_notes': self.technician_notes or '',
            'warranty_days': self.warranty_days,
            'delivery_date': self.delivery_date.strftime('%Y-%m-%d') if self.delivery_date else '',
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M')
        }


class ExchangeRecord(db.Model):
    __tablename__ = 'exchange_records'

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=True)
    
    brand = db.Column(db.String(60), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    imei = db.Column(db.String(30), nullable=True)
    original_price = db.Column(db.Float, default=20000.0)
    age_months = db.Column(db.Integer, default=12)
    storage = db.Column(db.String(20), default='64GB')
    battery_health = db.Column(db.Integer, default=85)
    
    condition_screen = db.Column(db.String(40), default='Good')  # Flawless, Minor Scratches, Cracked, Touch Issues
    condition_body = db.Column(db.String(40), default='Good')    # Mint, Good, Scratched, Dented
    camera_working = db.Column(db.Boolean, default=True)
    face_or_touch_id = db.Column(db.Boolean, default=True)
    
    ai_estimated_value = db.Column(db.Float, nullable=False)
    offered_value = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='Evaluated')  # 'Evaluated', 'Accepted', 'Applied_To_Bill'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'customer_name': self.customer.name if self.customer else 'Guest',
            'brand': self.brand,
            'model': self.model,
            'imei': self.imei or '',
            'original_price': self.original_price,
            'age_months': self.age_months,
            'battery_health': self.battery_health,
            'condition_screen': self.condition_screen,
            'ai_estimated_value': round(self.ai_estimated_value, 2),
            'offered_value': round(self.offered_value, 2),
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M')
        }


class SupplierPurchase(db.Model):
    __tablename__ = 'supplier_purchases'

    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    invoice_no = db.Column(db.String(50), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    paid_amount = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='Paid')  # 'Paid', 'Partial', 'Pending'
    notes = db.Column(db.Text, nullable=True)
    purchase_date = db.Column(db.Date, default=date.today)

    @property
    def balance_amount(self):
        return max(0.0, self.total_amount - self.paid_amount)

    def to_dict(self):
        return {
            'id': self.id,
            'supplier_name': self.supplier.name if self.supplier else '',
            'company': self.supplier.company if self.supplier else '',
            'invoice_no': self.invoice_no,
            'total_amount': self.total_amount,
            'paid_amount': self.paid_amount,
            'balance_amount': self.balance_amount,
            'status': self.status,
            'purchase_date': self.purchase_date.strftime('%Y-%m-%d')
        }


class Attendance(db.Model):
    __tablename__ = 'attendance'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default='present')  # 'present', 'half_day', 'absent', 'leave'
    check_in = db.Column(db.String(10), nullable=True)  # e.g. '09:30'
    check_out = db.Column(db.String(10), nullable=True) # e.g. '19:00'
    notes = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'date', name='uq_user_attendance_date'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user.full_name if self.user else '',
            'role': self.user.role if self.user else '',
            'date': self.date.strftime('%Y-%m-%d'),
            'status': self.status,
            'check_in': self.check_in,
            'check_out': self.check_out,
            'notes': self.notes
        }


class SalaryAdvance(db.Model):
    __tablename__ = 'salary_advances'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, default=date.today)
    reason = db.Column(db.String(255), nullable=True)
    is_settled = db.Column(db.Boolean, default=False)
    payroll_record_id = db.Column(db.Integer, db.ForeignKey('payroll_records.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user.full_name if self.user else '',
            'amount': self.amount,
            'date': self.date.strftime('%Y-%m-%d'),
            'reason': self.reason,
            'is_settled': self.is_settled
        }


class PayrollRecord(db.Model):
    __tablename__ = 'payroll_records'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    month_year = db.Column(db.String(7), nullable=False)  # 'YYYY-MM', e.g. '2026-09'
    total_working_days = db.Column(db.Integer, default=26)
    present_days = db.Column(db.Float, default=0.0)
    half_days = db.Column(db.Integer, default=0)
    paid_leaves = db.Column(db.Float, default=0.0)
    effective_work_days = db.Column(db.Float, default=0.0)
    base_salary = db.Column(db.Float, nullable=False)
    daily_wage = db.Column(db.Float, nullable=False)
    earned_salary = db.Column(db.Float, nullable=False)
    bonus_incentive = db.Column(db.Float, default=0.0)
    advances_deducted = db.Column(db.Float, default=0.0)
    net_salary = db.Column(db.Float, nullable=False)
    payment_status = db.Column(db.String(20), default='Paid')  # 'Paid', 'Pending'
    payment_date = db.Column(db.Date, default=date.today)
    payment_method = db.Column(db.String(50), default='Cash')  # 'Cash', 'Bank Transfer', 'UPI'
    notes = db.Column(db.Text, nullable=True)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)

    advances = db.relationship('SalaryAdvance', backref='payroll_record', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user.full_name if self.user else '',
            'role': self.user.role if self.user else '',
            'month_year': self.month_year,
            'total_working_days': self.total_working_days,
            'present_days': self.present_days,
            'half_days': self.half_days,
            'paid_leaves': self.paid_leaves,
            'effective_work_days': self.effective_work_days,
            'base_salary': self.base_salary,
            'daily_wage': round(self.daily_wage, 2),
            'earned_salary': round(self.earned_salary, 2),
            'bonus_incentive': self.bonus_incentive,
            'advances_deducted': self.advances_deducted,
            'net_salary': round(self.net_salary, 2),
            'payment_status': self.payment_status,
            'payment_date': self.payment_date.strftime('%Y-%m-%d') if self.payment_date else '',
            'payment_method': self.payment_method
        }


class PreBooking(db.Model):
    __tablename__ = 'pre_bookings'

    id = db.Column(db.Integer, primary_key=True)
    booking_no = db.Column(db.String(40), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    
    brand = db.Column(db.String(60), nullable=False, index=True)  # Apple, Samsung, OnePlus, Google
    model = db.Column(db.String(100), nullable=False, index=True) # iPhone 16 Pro Max, Galaxy S25 Ultra
    variant = db.Column(db.String(80), nullable=False)           # 256GB - Desert Titanium
    color = db.Column(db.String(50), nullable=True)
    storage = db.Column(db.String(30), nullable=True)
    
    expected_price = db.Column(db.Float, default=0.0)
    token_advance = db.Column(db.Float, nullable=False, default=2000.0)
    payment_mode = db.Column(db.String(30), default='UPI')       # Cash, UPI, Card, Online UPI, Pay at Store
    payment_status = db.Column(db.String(20), default='Paid')     # Paid, Pending
    booking_source = db.Column(db.String(30), default='In-Store') # 'In-Store', 'Online_Self_Book'
    
    queue_priority = db.Column(db.Integer, default=1)             # 1, 2, 3...
    status = db.Column(db.String(30), default='Booked', index=True) # Booked, Allocated, Fulfilled, Cancelled
    
    allocated_mobile_id = db.Column(db.Integer, db.ForeignKey('mobiles.id'), nullable=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=True)
    
    expected_delivery_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    fulfilled_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    allocated_mobile = db.relationship('Mobile', backref=db.backref('pre_booking', uselist=False), foreign_keys=[allocated_mobile_id])

    @property
    def remaining_balance(self):
        return max(0.0, (self.expected_price or 0.0) - (self.token_advance or 0.0))

    def to_dict(self):
        return {
            'id': self.id,
            'booking_no': self.booking_no,
            'customer_id': self.customer_id,
            'customer_name': self.customer.name if self.customer else 'Unknown',
            'customer_phone': self.customer.phone if self.customer else '',
            'customer_email': self.customer.email if self.customer else '',
            'brand': self.brand,
            'model': self.model,
            'variant': self.variant,
            'color': self.color or '',
            'storage': self.storage or '',
            'expected_price': self.expected_price,
            'token_advance': self.token_advance,
            'remaining_balance': self.remaining_balance,
            'payment_mode': self.payment_mode,
            'payment_status': self.payment_status,
            'booking_source': self.booking_source,
            'queue_priority': self.queue_priority,
            'status': self.status,
            'allocated_mobile_id': self.allocated_mobile_id,
            'allocated_imei': self.allocated_mobile.imei_1 if self.allocated_mobile else '',
            'invoice_id': self.invoice_id,
            'invoice_no': self.invoice.invoice_number if self.invoice else '',
            'expected_delivery_date': self.expected_delivery_date.strftime('%Y-%m-%d') if self.expected_delivery_date else '',
            'notes': self.notes or '',
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M'),
            'fulfilled_at': self.fulfilled_at.strftime('%Y-%m-%d %H:%M') if self.fulfilled_at else ''
        }


class LostSaleRequest(db.Model):
    __tablename__ = 'lost_sales_requests'

    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(120), nullable=False)
    customer_phone = db.Column(db.String(20), nullable=False, index=True)
    customer_email = db.Column(db.String(120), nullable=True)
    brand = db.Column(db.String(60), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    variant = db.Column(db.String(80), nullable=True)
    max_budget = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(20), default='Pending', index=True) # Pending, Notified, Purchased, Cancelled
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'customer_name': self.customer_name,
            'customer_phone': self.customer_phone,
            'customer_email': self.customer_email or '',
            'brand': self.brand,
            'model': self.model,
            'variant': self.variant or '',
            'max_budget': self.max_budget or 0.0,
            'status': self.status,
            'notes': self.notes or '',
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M')
        }

