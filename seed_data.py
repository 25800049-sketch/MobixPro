"""
Seed Data Script for MOBIX Mobile Shop Management System
Populates realistic initial data: Users, Mobiles with IMEIs, Accessories,
Customers, Active & Overdue EMIs, Mobile Repairs, and Suppliers.
"""
from datetime import date, datetime, timedelta
from config import Config
from models import (
    db, User, Customer, Supplier, Mobile, Accessory,
    Invoice, InvoiceItem, EMIAccount, EMIInstallment,
    RepairTicket, ExchangeRecord, SupplierPurchase,
    PreBooking, LostSaleRequest
)

def seed_database(app):
    with app.app_context():
        db.create_all()

        # Check if users already seeded
        if User.query.first():
            print("Database already contains data. Skipping seeding.")
            return

        print("[INFO] Seeding MOBIX database with realistic demo data...")

        # 1. Users & Roles
        admin = User(username='admin', full_name='Arjun Mehta', role='admin', email='admin@mobix.com', phone='9876500001')
        admin.set_password('admin123')

        cashier = User(username='cashier', full_name='Pooja Nair', role='cashier', email='cashier@mobix.com', phone='9876500002')
        cashier.set_password('cashier123')

        tech = User(username='tech', full_name='Rohan Joshi', role='technician', email='tech@mobix.com', phone='9876500003')
        tech.set_password('tech123')

        db.session.add_all([admin, cashier, tech])
        db.session.flush()

        # 2. Customers
        c1 = Customer(name='Rahul Sharma', phone='9820112345', email='rahul.sharma@gmail.com', address='402, Sunshine Apts, Bandra West, Mumbai')
        c2 = Customer(name='Priya Patel', phone='9898067890', email='priya.patel@yahoo.com', address='12, Navrangpura, Ahmedabad')
        c3 = Customer(name='Amit Verma', phone='9711054321', email='amit.verma@outlook.com', address='B-14, Connaught Place, New Delhi')
        c4 = Customer(name='Sneha Kulkarni', phone='9422098765', email='sneha.k@gmail.com', address='88, Kothrud, Pune')
        c5 = Customer(name='Vikram Reddy', phone='9949011223', email='vikram.reddy@gmail.com', address='Plot 45, Jubilee Hills, Hyderabad')

        db.session.add_all([c1, c2, c3, c4, c5])
        db.session.flush()

        # 3. Suppliers
        s1 = Supplier(company='Apex Tele-Distributors Pvt Ltd', name='Sunil Singhania', phone='9811223344', email='orders@apexdist.in', address='G-12, Electronics Trade Complex, Okhla, New Delhi', balance_due=45000.0)
        s2 = Supplier(company='TechSource Peripherals Hub', name='Karan Malhotra', phone='9822334455', email='sales@techsourcehub.com', address='Shop 18, Lamington Road, Mumbai', balance_due=12500.0)

        db.session.add_all([s1, s2])
        db.session.flush()

        # Inbound Purchases
        p1 = SupplierPurchase(supplier_id=s1.id, invoice_no='INV-APEX-8891', total_amount=150000.0, paid_amount=105000.0, status='Partial', notes='5x iPhone 15 units, 3x Galaxy S24', purchase_date=date.today() - timedelta(days=12))
        p2 = SupplierPurchase(supplier_id=s2.id, invoice_no='INV-TECH-4402', total_amount=35000.0, paid_amount=22500.0, status='Partial', notes='50x 65W Chargers, 30x Tempered Glass', purchase_date=date.today() - timedelta(days=5))
        db.session.add_all([p1, p2])

        # 4. Mobiles Inventory
        mobiles = [
            Mobile(
                brand='Apple', model='iPhone 15 Pro Max',
                imei_1='359128374829101', imei_2='359128374829102',
                ram='8GB', storage='256GB', color='Natural Titanium',
                purchase_price=125000, selling_price=139900,
                stock_quantity=4, warranty_months=12, min_stock_alert=2,
                image_url='/static/img/phones/iphone_15_pro_max.jpg',
                display='6.7" Super Retina XDR OLED, 120Hz ProMotion',
                processor='Apple A17 Pro (3nm)',
                camera='48MP Main + 12MP Ultra-wide + 12MP 5x Telephoto',
                battery='4422 mAh, 25W Fast Charge, MagSafe'
            ),
            Mobile(
                brand='Apple', model='iPhone 14',
                imei_1='359128374829201', imei_2=None,
                ram='6GB', storage='128GB', color='Starlight',
                purchase_price=52000, selling_price=59999,
                stock_quantity=6, warranty_months=12, min_stock_alert=2,
                image_url='/static/img/phones/iphone_14.jpg',
                display='6.1" Super Retina XDR OLED, HDR10',
                processor='Apple A15 Bionic (5nm)',
                camera='12MP Dual Pixel OIS + 12MP Ultra-wide',
                battery='3279 mAh, 20W Fast Charge'
            ),
            Mobile(
                brand='Samsung', model='Galaxy S24 Ultra',
                imei_1='359128374829301', imei_2='359128374829302',
                ram='12GB', storage='256GB', color='Titanium Gray',
                purchase_price=114000, selling_price=129999,
                stock_quantity=3, warranty_months=12, min_stock_alert=2,
                image_url='/static/img/phones/galaxy_s24_ultra.jpg',
                display='6.8" Dynamic LTPO AMOLED 2X, 120Hz, 2600 nits',
                processor='Snapdragon 8 Gen 3 for Galaxy (4nm)',
                camera='200MP OIS + 50MP 5x Periscope + 10MP 3x + 12MP Ultra-wide',
                battery='5000 mAh, 45W Wired, 15W Wireless'
            ),
            Mobile(
                brand='Samsung', model='Galaxy A55 5G',
                imei_1='359128374829401', imei_2='359128374829402',
                ram='8GB', storage='128GB', color='Awesome Iceblue',
                purchase_price=31000, selling_price=36999,
                stock_quantity=1, warranty_months=12, min_stock_alert=2,
                image_url='/static/img/phones/galaxy_a55.jpg',
                display='6.6" Super AMOLED 120Hz Gorilla Glass Victus+',
                processor='Samsung Exynos 1480 (4nm)',
                camera='50MP OIS Main + 12MP Ultra-wide + 5MP Macro',
                battery='5000 mAh, 25W Fast Charging'
            ),
            Mobile(
                brand='OnePlus', model='12',
                imei_1='359128374829501', imei_2='359128374829502',
                ram='12GB', storage='256GB', color='Silky Black',
                purchase_price=57000, selling_price=64999,
                stock_quantity=5, warranty_months=12, min_stock_alert=2,
                image_url='/static/img/phones/oneplus_12.jpg',
                display='6.82" 2K 120Hz ProXDR LTPO AMOLED, 4500 nits',
                processor='Snapdragon 8 Gen 3 (4nm)',
                camera='50MP Sony LYT-808 + 64MP 3x Periscope + 48MP Ultra-wide',
                battery='5400 mAh, 100W SUPERVOOC, 50W AIRVOOC'
            ),
            Mobile(
                brand='OnePlus', model='Nord CE 4 5G',
                imei_1='359128374829601', imei_2='359128374829602',
                ram='8GB', storage='128GB', color='Dark Chrome',
                purchase_price=21000, selling_price=24999,
                stock_quantity=8, warranty_months=12, min_stock_alert=2,
                image_url='/static/img/phones/oneplus_nord_ce_4.jpg',
                display='6.7" Fluid AMOLED, 120Hz, HDR10+',
                processor='Snapdragon 7 Gen 3 (4nm)',
                camera='50MP Sony LYT-600 OIS + 8MP Ultra-wide',
                battery='5500 mAh, 100W SuperVOOC Fast Charge'
            ),
            Mobile(
                brand='Xiaomi', model='Redmi Note 13 Pro+',
                imei_1='359128374829701', imei_2='359128374829702',
                ram='12GB', storage='256GB', color='Fusion Purple',
                purchase_price=27500, selling_price=31999,
                stock_quantity=4, warranty_months=12, min_stock_alert=2,
                image_url='/static/img/phones/redmi_note_13.jpg',
                display='6.67" 1.5K Curved AMOLED, 120Hz, Dolby Vision',
                processor='MediaTek Dimensity 7200 Ultra (4nm)',
                camera='200MP Samsung ISOCELL HP3 OIS + 8MP + 2MP',
                battery='5000 mAh, 120W HyperCharge (19 min 100%)'
            ),
            Mobile(
                brand='Realme', model='12 Pro+ 5G',
                imei_1='359128374829801', imei_2='359128374829802',
                ram='8GB', storage='256GB', color='Submarine Blue',
                purchase_price=25000, selling_price=29999,
                stock_quantity=2, warranty_months=12, min_stock_alert=2,
                image_url='/static/img/phones/realme_12_pro.jpg',
                display='6.7" 120Hz Curved Vision AMOLED',
                processor='Snapdragon 7s Gen 2 (4nm)',
                camera='64MP Periscope OIS + 50MP Sony IMX890 + 8MP',
                battery='5000 mAh, 67W SUPERVOOC Charge'
            ),
            Mobile(
                brand='Vivo', model='V30 Pro 5G',
                imei_1='359128374829901', imei_2='359128374829902',
                ram='8GB', storage='256GB', color='Andaman Blue',
                purchase_price=36000, selling_price=41999,
                stock_quantity=3, warranty_months=12, min_stock_alert=2,
                image_url='/static/img/phones/vivo_v30_pro.jpg',
                display='6.78" 1.5K 3D Curved AMOLED 120Hz, 2800 nits',
                processor='MediaTek Dimensity 8200 (4nm)',
                camera='50MP ZEISS Main + 50MP ZEISS Telephoto + 50MP Ultra-wide',
                battery='5000 mAh, 80W FlashCharge'
            ),
            Mobile(
                brand='Motorola', model='Edge 50 Pro',
                imei_1='359128374830001', imei_2='359128374830002',
                ram='12GB', storage='256GB', color='Luxe Lavender',
                purchase_price=27000, selling_price=31999,
                stock_quantity=5, warranty_months=12, min_stock_alert=2,
                image_url='/static/img/phones/motorola_edge_50_pro.jpg',
                display='6.7" 1.5K 144Hz pOLED, Pantone Validated',
                processor='Snapdragon 7 Gen 3 (4nm)',
                camera='50MP OIS Main + 10MP 3x Telephoto + 13MP Ultra-wide',
                battery='4500 mAh, 125W TurboPower, 50W Wireless'
            )
        ]
        db.session.add_all(mobiles)
        db.session.flush()

        # 5. Accessories Inventory
        accessories = [
            Accessory(name='65W GaN Dual USB-C Fast Charger', category='Chargers', brand='Anker', compatibility='All Type-C Laptops & Mobiles', purchase_price=1400, selling_price=2499, stock_quantity=18, min_stock_alert=5),
            Accessory(name='Apple 20W USB-C Power Adapter', category='Chargers', brand='Apple', compatibility='iPhone 11/12/13/14/15', purchase_price=1250, selling_price=1899, stock_quantity=22, min_stock_alert=5),
            Accessory(name='boAt Rockerz 450 Bluetooth Headset', category='Earphones', brand='boAt', compatibility='Universal Bluetooth', purchase_price=950, selling_price=1499, stock_quantity=14, min_stock_alert=4),
            Accessory(name='OnePlus Buds 3 ANC Earbuds', category='Earphones', brand='OnePlus', compatibility='Universal Bluetooth 5.3', purchase_price=3900, selling_price=5499, stock_quantity=8, min_stock_alert=3),
            Accessory(name='20,000mAh 22.5W Fast Power Bank', category='Power banks', brand='Mi', compatibility='USB-A & Type-C', purchase_price=1350, selling_price=1999, stock_quantity=12, min_stock_alert=4),
            Accessory(name='Heavy-Duty Magnetic Armor Case', category='Cases & Covers', brand='Spigen', compatibility='iPhone 15 Series', purchase_price=450, selling_price=999, stock_quantity=2, min_stock_alert=5), # Low stock!
            Accessory(name='9H Edge-to-Edge Tempered Glass Screen Protector', category='Screen Protectors', brand='GorillaShield', compatibility='Samsung S24 / S23 Series', purchase_price=80, selling_price=299, stock_quantity=45, min_stock_alert=10),
            Accessory(name='100W Braided USB-C to USB-C Fast Cable (2m)', category='Cables', brand='Baseus', compatibility='Type-C High Speed', purchase_price=220, selling_price=599, stock_quantity=30, min_stock_alert=8),
            Accessory(name='Noise ColorFit Pro 5 Smart Watch', category='Smart Watches', brand='Noise', compatibility='Android & iOS', purchase_price=2200, selling_price=3499, stock_quantity=7, min_stock_alert=3)
        ]
        db.session.add_all(accessories)
        db.session.flush()

        # 6. Sample Finished Invoices
        # Invoice 1: Phone + Charger (Cash)
        inv1 = Invoice(
            invoice_number='INV-20260901-A101',
            customer_id=c1.id,
            user_id=cashier.id,
            subtotal=62498.0,
            tax_rate=18.0,
            tax_amount=11249.64,
            discount_amount=1500.0,
            exchange_discount=0.0,
            final_total=72247.64,
            payment_mode='UPI',
            payment_status='Paid',
            created_at=datetime.utcnow() - timedelta(days=6)
        )
        db.session.add(inv1)
        db.session.flush()

        item1_1 = InvoiceItem(invoice_id=inv1.id, item_type='mobile', mobile_id=mobiles[1].id, item_name='Apple iPhone 14 (6GB/128GB)', imei=mobiles[1].imei_1, quantity=1, unit_price=59999.0, total_price=59999.0)
        item1_2 = InvoiceItem(invoice_id=inv1.id, item_type='accessory', accessory_id=accessories[0].id, item_name='65W GaN Dual USB-C Fast Charger', imei=None, quantity=1, unit_price=2499.0, total_price=2499.0)
        db.session.add_all([item1_1, item1_2])

        # Invoice 2: EMI Sale Example (As requested in prompt!)
        # Mobile price = ₹30,000, Down payment = ₹6,000, Remaining = ₹24,000, EMI = ₹4,000 × 6 months
        inv2 = Invoice(
            invoice_number='INV-20260805-E902',
            customer_id=c2.id,
            user_id=cashier.id,
            subtotal=30000.0,
            tax_rate=0.0,
            tax_amount=0.0,
            discount_amount=0.0,
            exchange_discount=0.0,
            final_total=30000.0,
            payment_mode='EMI',
            payment_status='Partial',
            created_at=datetime.utcnow() - timedelta(days=40)
        )
        db.session.add(inv2)
        db.session.flush()

        item2_1 = InvoiceItem(invoice_id=inv2.id, item_type='mobile', mobile_id=mobiles[7].id, item_name='Realme 12 Pro+ 5G (8GB/256GB)', imei=mobiles[7].imei_1, quantity=1, unit_price=30000.0, total_price=30000.0)
        db.session.add(item2_1)

        # EMI Account for Invoice 2
        emi2 = EMIAccount(
            invoice_id=inv2.id,
            customer_id=c2.id,
            total_amount=30000.0,
            down_payment=6000.0,
            principal_remaining=24000.0,
            emi_amount=4000.0,
            tenure_months=6,
            fine_per_cycle=200.0,
            start_date=date.today() - timedelta(days=40),
            status='Overdue',
            notes='Mobile EMI: ₹4,000 x 6 months'
        )
        db.session.add(emi2)
        db.session.flush()

        # Installment 1: Paid on time
        inst1 = EMIInstallment(
            emi_account_id=emi2.id,
            installment_no=1,
            due_date=date.today() - timedelta(days=10),
            amount=4000.0,
            fine_amount=0.0,
            paid_amount=4000.0,
            payment_date=date.today() - timedelta(days=12),
            payment_mode='UPI',
            status='paid'
        )
        # Installment 2: Overdue with ₹200 Late Fine! (Demonstrating prompt's requirement)
        # "EMI = ₹4,000, Fine = ₹200, Amount due = ₹4,200"
        inst2 = EMIInstallment(
            emi_account_id=emi2.id,
            installment_no=2,
            due_date=date.today() - timedelta(days=2),
            amount=4000.0,
            fine_amount=200.0,
            paid_amount=0.0,
            status='overdue'
        )
        # Installments 3 to 6: Pending future
        db.session.add_all([inst1, inst2])
        for idx in range(3, 7):
            inst_pending = EMIInstallment(
                emi_account_id=emi2.id,
                installment_no=idx,
                due_date=date.today() + timedelta(days=28 * (idx - 2)),
                amount=4000.0,
                fine_amount=0.0,
                paid_amount=0.0,
                status='pending'
            )
            db.session.add(inst_pending)

        # Update customer balance with remaining principal + fine
        c2.outstanding_balance = 20000.0 + 200.0  # 5 unpaid installments + 200 fine

        # 7. Mobile Repair Tickets
        rep1 = RepairTicket(
            ticket_no='REP-260902-7A12',
            customer_id=c3.id,
            technician_id=tech.id,
            brand='OnePlus',
            model='OnePlus 11R',
            imei='359918273645019',
            problem_description='Outer display cracked after accidental drop, touch responding irregularly.',
            estimated_cost=6500.0,
            final_cost=6500.0,
            advance_paid=2000.0,
            status='Repairing',
            parts_used='Original OnePlus Fluid AMOLED Display Panel',
            technician_notes='Screen disassembled, UV glue cured, undergoing touch calibration.',
            warranty_days=60
        )

        rep2 = RepairTicket(
            ticket_no='REP-260905-9B34',
            customer_id=c4.id,
            technician_id=tech.id,
            brand='Apple',
            model='iPhone 12',
            imei='359918273645882',
            problem_description='Battery health degraded to 72%, device throttles and shuts down at 20%.',
            estimated_cost=3200.0,
            final_cost=3200.0,
            advance_paid=1000.0,
            status='Ready',
            parts_used='OEM High-Capacity 2815mAh Battery + Waterproof Gasket',
            technician_notes='Replaced battery. Health shows 100%. Device passed 24hr discharge test. Ready for pickup.',
            warranty_days=90
        )

        rep3 = RepairTicket(
            ticket_no='REP-260906-3C56',
            customer_id=c5.id,
            technician_id=tech.id,
            brand='Samsung',
            model='Galaxy S21 FE',
            imei='359918273645112',
            problem_description='Type-C port loose, fast charging not engaging.',
            estimated_cost=1200.0,
            advance_paid=0.0,
            status='Diagnosing',
            warranty_days=30
        )

        db.session.add_all([rep1, rep2, rep3])

        # 8. Exchange Records
        ex1 = ExchangeRecord(
            customer_id=c1.id,
            invoice_id=inv1.id,
            brand='OnePlus',
            model='OnePlus 9 5G',
            imei='351182736450091',
            original_price=49999.0,
            age_months=24,
            storage='128GB',
            battery_health=82,
            condition_screen='Minor Scratches',
            condition_body='Good',
            ai_estimated_value=12400.0,
            offered_value=11000.0,
            status='Evaluated'
        )
        db.session.add(ex1)

        # 9. Flagship Pre-Orders & Priority Queue
        pb1 = PreBooking(
            booking_no='PB-2026-0001',
            customer_id=c1.id,
            brand='Apple',
            model='iPhone 16 Pro Max',
            variant='256GB - Desert Titanium',
            color='Desert Titanium',
            storage='256GB',
            expected_price=144900.0,
            token_advance=5000.0,
            payment_mode='UPI',
            payment_status='Paid',
            booking_source='In-Store',
            queue_priority=1,
            status='Booked',
            expected_delivery_date=date.today() + timedelta(days=7),
            notes='Requested launch day pickup'
        )

        pb2 = PreBooking(
            booking_no='PB-2026-0002',
            customer_id=c2.id,
            brand='Samsung',
            model='Galaxy S25 Ultra',
            variant='512GB - Titanium Silver',
            color='Titanium Silver',
            storage='512GB',
            expected_price=134999.0,
            token_advance=5000.0,
            payment_mode='UPI',
            payment_status='Paid',
            booking_source='Online_Self_Book',
            queue_priority=1,
            status='Booked',
            expected_delivery_date=date.today() + timedelta(days=10),
            notes='Self-booked via online showcase'
        )

        pb3 = PreBooking(
            booking_no='PB-2026-0003',
            customer_id=c3.id,
            brand='OnePlus',
            model='OnePlus 12 5G',
            variant='256GB - Flowy Emerald',
            color='Flowy Emerald',
            storage='256GB',
            expected_price=64999.0,
            token_advance=2000.0,
            payment_mode='Cash',
            payment_status='Paid',
            booking_source='In-Store',
            queue_priority=1,
            status='Allocated',
            allocated_mobile_id=m3.id if 'm3' in locals() else None,
            expected_delivery_date=date.today() + timedelta(days=2),
            notes='Handset arrived and reserved in safe'
        )
        if 'm3' in locals():
            m3.status = 'reserved'

        db.session.add_all([pb1, pb2, pb3])

        # 10. Lost Sales Demands
        ls1 = LostSaleRequest(
            customer_name='Rohan Verma',
            customer_phone='9876543219',
            customer_email='rohan.v@gmail.com',
            brand='Google',
            model='Pixel 9 Pro Fold',
            variant='256GB Obsidian',
            max_budget=172999.0,
            status='Pending',
            notes='Customer looking for foldable Pixel. Needs fast delivery.'
        )

        ls2 = LostSaleRequest(
            customer_name='Priya Shah',
            customer_phone='9811223344',
            customer_email='priyashah@gmail.com',
            brand='Nothing',
            model='Phone (2a) Plus',
            variant='256GB Grey',
            max_budget=29999.0,
            status='Pending',
            notes='Walk-in customer, out of stock during weekend.'
        )

        db.session.add_all([ls1, ls2])

        db.session.commit()
        print("[SUCCESS] Seed completed successfully! All demo data created.")

if __name__ == '__main__':
    from flask import Flask
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    seed_database(app)
