"""
Automated Verification Suite for MOBIX Mobile Shop System
Validates database integrity, authentication, POS billing, EMI calculations,
AI valuation model, and PDF generation.
"""
import unittest
from datetime import date, timedelta
from app import create_app
from models import db, User, Mobile, Accessory, Customer, Invoice, EMIAccount, EMIInstallment, RepairTicket, PreBooking, LostSaleRequest
import json
from services.ai_valuation import valuation_engine
from services.emi_service import (
    create_emi_schedule, refresh_all_overdue_emis, pay_installment,
    calculate_customer_credit_score
)
from services.pdf_service import generate_invoice_pdf
from services.notification_service import build_whatsapp_invoice_message, build_whatsapp_repair_message

class MobixSystemTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()

    def test_01_database_and_seed_data(self):
        with self.app.app_context():
            user_count = User.query.count()
            mobile_count = Mobile.query.count()
            accessory_count = Accessory.query.count()
            customer_count = Customer.query.count()

            print(f"\n[Test 1] Seeding check: Users={user_count}, Mobiles={mobile_count}, Accessories={accessory_count}, Customers={customer_count}")
            self.assertGreaterEqual(user_count, 3)
            self.assertGreaterEqual(mobile_count, 5)
            self.assertGreaterEqual(accessory_count, 5)
            self.assertGreaterEqual(customer_count, 3)

    def test_02_authentication_roles(self):
        # Test Admin login
        res = self.client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Arjun Mehta', res.data)

        # Test Cashier login
        self.client.get('/logout')
        res_cashier = self.client.post('/login', data={'username': 'cashier', 'password': 'cashier123'}, follow_redirects=True)
        self.assertEqual(res_cashier.status_code, 200)
        self.assertIn(b'Pooja Nair', res_cashier.data)

    def test_03_ai_valuation_engine(self):
        # Predict price for a 14-month old Samsung Galaxy
        result = valuation_engine.evaluate_phone(
            brand='Samsung',
            model_name='Galaxy S22',
            original_price=52000,
            age_months=14,
            storage_str='128GB',
            battery_health=85,
            screen_cond='Minor Scratches',
            body_cond='Good',
            camera_ok=True,
            biometrics_ok=True
        )
        print(f"\n[Test 3] AI Valuation for Samsung S22 (Orig Rs. 52,000): Market=Rs. {result['ai_estimated_market_value']:,.2f}, Store Offer=Rs. {result['offered_exchange_value']:,.2f}")
        self.assertGreater(result['ai_estimated_market_value'], 10000)
        self.assertLess(result['ai_estimated_market_value'], 52000)
        self.assertGreater(result['offered_exchange_value'], 8000)

    def test_04_pos_checkout_flow(self):
        # Login as cashier
        self.client.post('/login', data={'username': 'cashier', 'password': 'cashier123'})
        
        with self.app.app_context():
            mobile = Mobile.query.filter(Mobile.stock_quantity > 1).first()
            acc = Accessory.query.filter(Accessory.stock_quantity > 2).first()
            initial_mob_stock = mobile.stock_quantity
            initial_acc_stock = acc.stock_quantity
            mob_id = mobile.id
            acc_id = acc.id

        payload = {
            'customer_id': 'new',
            'customer_name': 'Test Checkout Customer',
            'customer_phone': '9988776655',
            'customer_email': 'testcust@gmail.com',
            'payment_mode': 'Cash',
            'tax_rate': 18.0,
            'discount_amount': 500.0,
            'exchange_discount': 0.0,
            'items': [
                {'id': mob_id, 'type': 'mobile', 'name': 'Test Mobile', 'price': 30000.0, 'qty': 1},
                {'id': acc_id, 'type': 'accessory', 'name': 'Test Charger', 'price': 1500.0, 'qty': 1}
            ]
        }

        res = self.client.post('/pos/checkout', json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        invoice_id = data['invoice_id']
        print(f"\n[Test 4] POS Checkout created Invoice #{data['invoice_number']}")

        # Verify stock was decremented
        with self.app.app_context():
            updated_mob = db.session.get(Mobile, mob_id)
            updated_acc = db.session.get(Accessory, acc_id)
            self.assertEqual(updated_mob.stock_quantity, initial_mob_stock - 1)
            self.assertEqual(updated_acc.stock_quantity, initial_acc_stock - 1)

            # Test ReportLab PDF generator on this invoice
            inv = db.session.get(Invoice, invoice_id)
            pdf_bytes = generate_invoice_pdf(inv)
            self.assertGreater(len(pdf_bytes.getvalue()), 1000)
            print(f"[Test 4] Generated valid PDF invoice size: {len(pdf_bytes.getvalue())} bytes")

    def test_05_emi_schedule_and_auto_fine(self):
        with self.app.app_context():
            cust = Customer.query.first()
            inv = Invoice.query.first()

            # Mobile price = ₹30,000, Down payment = ₹6,000, Remaining = ₹24,000, EMI = ₹4,000 × 6 months
            emi_acc = create_emi_schedule(
                invoice_id=inv.id,
                customer_id=cust.id,
                total_amount=30000.0,
                down_payment=6000.0,
                tenure_months=6,
                fine_per_cycle=200.0
            )
            self.assertEqual(emi_acc.emi_amount, 4000.0)
            self.assertEqual(len(emi_acc.installments), 6)

            # Simulate 1 installment becoming past due date
            inst1 = emi_acc.installments[0]
            inst1.due_date = date.today() - timedelta(days=5)
            db.session.commit()

            # Run auto-overdue scanner
            overdue_found = refresh_all_overdue_emis()
            self.assertGreaterEqual(overdue_found, 1)

            # Check fine applied: amount 4000, fine 200 -> total 4200
            db.session.refresh(inst1)
            self.assertEqual(inst1.status, 'overdue')
            self.assertEqual(inst1.fine_amount, 200.0)
            self.assertEqual(inst1.total_due, 4200.0)
            print(f"\n[Test 5] EMI Overdue Auto-Fine verified: Base=Rs. {inst1.amount}, Fine=Rs. {inst1.fine_amount}, Due=Rs. {inst1.total_due}")

    def test_06_attendance_and_salary_calculation(self):
        from models import Attendance, SalaryAdvance, PayrollRecord
        from services.payroll_service import calculate_employee_salary, finalize_payroll
        with self.app.app_context():
            # Get an employee
            tech = User.query.filter_by(role='technician').first()
            self.assertIsNotNone(tech)
            tech.monthly_salary = 26000.0
            tech.daily_rate = 1000.0  # 26000 / 26
            db.session.commit()

            # Record attendance for September 2026:
            # 20 full days present, 2 half days (counts as 1 day), 1 paid leave (counts as 1 day) = 22 effective days
            # Expected earned gross = 22 * 1000 = 22,000
            test_year = 2026
            test_month = 9
            # Clear any previous test attendance
            Attendance.query.filter_by(user_id=tech.id).delete()
            SalaryAdvance.query.filter_by(user_id=tech.id).delete()
            PayrollRecord.query.filter_by(user_id=tech.id).delete()

            for d in range(1, 21):
                db.session.add(Attendance(user_id=tech.id, date=date(test_year, test_month, d), status='present'))
            for d in [21, 22]:
                db.session.add(Attendance(user_id=tech.id, date=date(test_year, test_month, d), status='half_day'))
            db.session.add(Attendance(user_id=tech.id, date=date(test_year, test_month, 23), status='leave'))
            db.session.add(Attendance(user_id=tech.id, date=date(test_year, test_month, 24), status='absent'))

            # Record a salary advance of ₹2,000
            db.session.add(SalaryAdvance(user_id=tech.id, amount=2000.0, date=date(test_year, test_month, 10), reason='Medical advance'))
            db.session.commit()

            # Calculate salary
            calc = calculate_employee_salary(user_id=tech.id, year=test_year, month=test_month, total_working_days=26, bonus=500.0)
            self.assertEqual(calc['present_days'], 20.0)
            self.assertEqual(calc['half_days'], 2)
            self.assertEqual(calc['paid_leaves'], 1.0)
            self.assertEqual(calc['effective_work_days'], 22.0)
            self.assertEqual(calc['earned_salary'], 22000.0)
            self.assertEqual(calc['advances_deducted'], 2000.0)
            # Net = 22,000 + 500 (bonus) - 2000 (advance) = 20,500
            self.assertEqual(calc['net_salary'], 20500.0)

            # Finalize payroll
            record = finalize_payroll(user_id=tech.id, year=test_year, month=test_month, total_working_days=26, bonus=500.0)
            self.assertEqual(record.net_salary, 20500.0)
            self.assertEqual(record.effective_work_days, 22.0)

            # Check that the advance is marked as settled
            adv = SalaryAdvance.query.filter_by(user_id=tech.id).first()
            self.assertTrue(adv.is_settled)
            self.assertEqual(adv.payroll_record_id, record.id)
            print(f"\n[Test 6] Attendance Salary Verified: Earned=Rs.{record.earned_salary}, Net=Rs.{record.net_salary}, Advances Deducted=Rs.{record.advances_deducted}")

            # Test web routes with authenticated admin
            self.client.get('/logout')
            self.client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)
            res_att = self.client.get('/payroll/attendance')
            self.assertEqual(res_att.status_code, 200)
            self.assertIn(b'Staff Daily Attendance', res_att.data)

            res_sal = self.client.get('/payroll/salary?month=9&year=2026')
            self.assertEqual(res_sal.status_code, 200)
            self.assertIn(b'Employee Salary Calculation', res_sal.data)

            res_slip = self.client.get(f'/payroll/payslip/{record.id}')
            self.assertEqual(res_slip.status_code, 200)
            self.assertIn(b'PAYSLIP FOR', res_slip.data)
            print("[Test 6] Payroll web routes verified: /payroll/attendance (200), /payroll/salary (200), /payroll/payslip (200)")

    def test_07_preorders_queue_and_stock_allocation(self):
        # 1. Login as Admin
        self.client.get('/logout')
        self.client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)

        with self.app.app_context():
            # Clean test bookings and test mobiles for isolated test run
            PreBooking.query.filter_by(model='iPhone 16 Pro Max Testing Model').delete()
            Mobile.query.filter_by(model='iPhone 16 Pro Max Testing Model').delete()
            db.session.commit()

        # 2. Staff creates Pre-Booking 1 for iPhone 16 Pro Max Testing Model
        res1 = self.client.post('/preorders/create', data={
            'customer_name': 'Aakash Verma',
            'customer_phone': '9112233445',
            'brand': 'Apple',
            'model': 'iPhone 16 Pro Max Testing Model',
            'storage': '256GB',
            'color': 'Desert Titanium',
            'expected_price': '144900',
            'token_advance': '5000',
            'payment_mode': 'UPI'
        }, follow_redirects=True)
        self.assertEqual(res1.status_code, 200)

        with self.app.app_context():
            b1 = PreBooking.query.filter_by(model='iPhone 16 Pro Max Testing Model').first()
            self.assertIsNotNone(b1)
            self.assertEqual(b1.queue_priority, 1)
            self.assertEqual(b1.status, 'Booked')
            self.assertEqual(b1.token_advance, 5000.0)
            b1_id = b1.id
            b1_no = b1.booking_no

        # 3. Staff creates Pre-Booking 2 for the same model -> checks Queue Rank #2
        res2 = self.client.post('/preorders/create', data={
            'customer_name': 'Sneha Rao',
            'customer_phone': '9223344556',
            'brand': 'Apple',
            'model': 'iPhone 16 Pro Max Testing Model',
            'storage': '256GB',
            'color': 'Desert Titanium',
            'expected_price': '144900',
            'token_advance': '5000',
            'payment_mode': 'Cash'
        }, follow_redirects=True)
        self.assertEqual(res2.status_code, 200)

        with self.app.app_context():
            b2 = PreBooking.query.filter_by(model='iPhone 16 Pro Max Testing Model', queue_priority=2).first()
            self.assertIsNotNone(b2)
            self.assertEqual(b2.queue_priority, 2)
            self.assertEqual(b2.status, 'Booked')

            # 4. Simulate arrival of 1 physical handset in stock
            new_phone = Mobile(
                brand='Apple',
                model='iPhone 16 Pro Max Testing Model',
                imei_1='358899001122334',
                ram='8GB',
                storage='256GB',
                color='Desert Titanium',
                purchase_price=120000.0,
                selling_price=144900.0,
                stock_quantity=1,
                status='in_stock'
            )
            db.session.add(new_phone)
            db.session.commit()
            phone_id = new_phone.id

        # 5. Run FIFO Auto-Allocation Engine
        res_alloc = self.client.post('/preorders/auto-allocate', follow_redirects=True)
        self.assertEqual(res_alloc.status_code, 200)

        with self.app.app_context():
            # Booking 1 (Priority 1) MUST be allocated!
            b1_refreshed = db.session.get(PreBooking, b1_id)
            self.assertEqual(b1_refreshed.status, 'Allocated')
            self.assertEqual(b1_refreshed.allocated_mobile_id, phone_id)

            # Handset MUST be marked 'reserved' to protect from walk-ins!
            phone_refreshed = db.session.get(Mobile, phone_id)
            self.assertEqual(phone_refreshed.status, 'reserved')

            # Booking 2 (Priority 2) MUST still be waiting (Booked)
            b2_refreshed = PreBooking.query.filter_by(model='iPhone 16 Pro Max Testing Model', queue_priority=2).first()
            self.assertEqual(b2_refreshed.status, 'Booked')
            self.assertIsNone(b2_refreshed.allocated_mobile_id)
            print(f"\n[Test 7] FIFO Auto-Allocation Verified: Booking #1 allocated IMEI {phone_refreshed.imei_1}, Booking #2 stays in queue.")

        # 6. Test Public Customer Portal & Digital Pass
        res_pass = self.client.get(f'/prebook/pass/{b1_no}')
        self.assertEqual(res_pass.status_code, 200)
        self.assertIn(b'QUEUE RANK #01', res_pass.data)

        # 7. Convert Booking 1 to POS Invoice and verify Token Advance (Rs 5,000) deduction!
        pos_payload = {
            'customer_id': 'new',
            'customer_name': 'Aakash Verma',
            'customer_phone': '9112233445',
            'payment_mode': 'Cash',
            'tax_rate': 18.0,
            'discount_amount': 0.0,
            'exchange_discount': 0.0,
            'preorder_id': b1_id,
            'items': [
                {'id': phone_id, 'type': 'mobile', 'name': 'iPhone 16 Pro Max Testing Model', 'price': 144900.0, 'qty': 1}
            ]
        }
        res_checkout = self.client.post('/pos/checkout', json=pos_payload)
        self.assertEqual(res_checkout.status_code, 200)
        checkout_data = res_checkout.get_json()
        self.assertTrue(checkout_data['success'])

        with self.app.app_context():
            invoice = db.session.get(Invoice, checkout_data['invoice_id'])
            # Subtotal = 144,900. Tax 18% = 26,082. Gross = 170,982. Token Advance Deducted = 5,000 -> Final = 165,982
            expected_final = (144900.0 + round(144900.0 * 0.18, 2)) - 5000.0
            self.assertAlmostEqual(invoice.final_total, expected_final, places=1)

            # Booking must be marked Fulfilled
            b1_final = db.session.get(PreBooking, b1_id)
            self.assertEqual(b1_final.status, 'Fulfilled')
            self.assertEqual(b1_final.invoice_id, invoice.id)
            self.assertIsNotNone(b1_final.fulfilled_at)

            # Handset status must transition to 'sold'
            sold_phone = db.session.get(Mobile, phone_id)
            self.assertEqual(sold_phone.status, 'sold')
            print(f"[Test 7] POS Pre-Order Fulfillment Verified: Invoice #{invoice.invoice_number}, Final Total Rs. {invoice.final_total:,.2f} (Rs. 5,000 advance deducted).")

        # 8. Test Lost Sales Demand Logger
        res_ls = self.client.post('/preorders/lost-sales/create', data={
            'customer_name': 'Kavita Joshi',
            'customer_phone': '9334455667',
            'brand': 'Google',
            'model': 'Pixel 9 Pro Fold Special',
            'variant': '512GB Obsidian',
            'max_budget': '175000',
            'notes': 'Requested urgent launch delivery'
        }, follow_redirects=True)
        self.assertEqual(res_ls.status_code, 200)

        with self.app.app_context():
            ls = LostSaleRequest.query.filter_by(model='Pixel 9 Pro Fold Special').first()
            self.assertIsNotNone(ls)
            self.assertEqual(ls.status, 'Pending')
    def test_08_credit_scoring_and_overdue_handling(self):
        # 1. Login as Admin
        self.client.get('/logout')
        self.client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=True)

        with self.app.app_context():
            # Setup a clean test customer
            cust = Customer.query.filter_by(phone='9876500099').first()
            if not cust:
                cust = Customer(name='Vikramaditya Rao', phone='9876500099', email='vikram@test.com', address='Bengaluru')
                db.session.add(cust)
                db.session.commit()
            cust_id = cust.id

            # Verify initial/baseline credit profile
            profile = cust.get_credit_profile()
            self.assertIn('score', profile)
            self.assertIn('tier', profile)
            self.assertGreaterEqual(profile['score'], 300)
            self.assertLessEqual(profile['score'], 900)
            print(f"\n[Test 8] Credit Profile Verified: Score={profile['score']}, Tier={profile['tier']}, Min DP={profile['down_payment_min_pct']}%")

            # Remove any old conflicting test invoice
            old_inv = Invoice.query.filter_by(invoice_number='INV-TEST-LOCK-001').first()
            if old_inv:
                for old_acc in EMIAccount.query.filter_by(invoice_id=old_inv.id).all():
                    db.session.delete(old_acc)
                db.session.delete(old_inv)
                db.session.commit()

            # Create test invoice and EMI account
            inv = Invoice(
                invoice_number='INV-TEST-LOCK-001',
                customer_id=cust.id,
                user_id=1,
                subtotal=120000.0,
                tax_amount=21600.0,
                discount_amount=0.0,
                final_total=141600.0,
                payment_mode='EMI',
                payment_status='Paid'
            )
            db.session.add(inv)
            db.session.commit()

            # Create EMI Account
            account = EMIAccount(
                invoice_id=inv.id,
                customer_id=cust.id,
                total_amount=141600.0,
                down_payment=21600.0,
                principal_remaining=120000.0,
                emi_amount=20000.0,
                tenure_months=6,
                start_date=date.today() - timedelta(days=60),
                status='Active',
                fine_per_cycle=200.0
            )
            db.session.add(account)
            db.session.commit()

            # Create an installment overdue by 25 days (> 15 days threshold)
            inst1 = EMIInstallment(
                emi_account_id=account.id,
                installment_no=1,
                due_date=date.today() - timedelta(days=25),
                amount=20000.0,
                fine_amount=200.0,
                status='overdue'
            )
            inst2 = EMIInstallment(
                emi_account_id=account.id,
                installment_no=2,
                due_date=date.today() + timedelta(days=5),
                amount=20000.0,
                fine_amount=0.0,
                status='pending'
            )
            db.session.add_all([inst1, inst2])
            db.session.commit()

            account_id = account.id
            inst1_id = inst1.id

            # Verify overdue tracking
            self.assertGreaterEqual(account.max_days_overdue, 25)
            self.assertEqual(account.status, 'Active')

            # Pay installment 1 (the overdue installment)
            pay_success, pay_msg = pay_installment(inst1_id, 20200.0, payment_mode='UPI')
            self.assertTrue(pay_success)

            acc_cleared = db.session.get(EMIAccount, account_id)
            self.assertEqual(inst1.status, 'paid')
            print(f"[Test 8] Overdue Installment Settlement Verified: {pay_msg}")

        # Test Web Routes: EMI Schedule Detail (200 OK)
        res_detail = self.client.get(f'/emi/{account_id}')
        self.assertEqual(res_detail.status_code, 200)
        self.assertIn(b'Repayment Schedule', res_detail.data)
        print(f"[Test 8] EMI Contract Detail Route Verified: /emi/{account_id} (200 OK)")

        # Test Customer Credit API endpoint
        res_credit_api = self.client.get(f'/emi/api/customer-credit/{cust_id}')
        self.assertEqual(res_credit_api.status_code, 200)
        credit_json = res_credit_api.get_json()
        self.assertTrue(credit_json['success'])
        self.assertIn('profile', credit_json)
        self.assertIn('tier', credit_json['profile'])
        print(f"[Test 8] Customer Credit Check API Verified: Score={credit_json['profile']['score']}, Tier={credit_json['profile']['tier']}")

        # Test Refresh Fines route
        res_fines = self.client.post('/emi/refresh-fines', follow_redirects=True)
        self.assertEqual(res_fines.status_code, 200)
        print(f"[Test 8] EMI Refresh Fines Route Verified: /emi/refresh-fines (200 OK)")

        # Clean up test invoice and EMI data
        with self.app.app_context():
            old_inv = Invoice.query.filter_by(invoice_number='INV-TEST-LOCK-001').first()
            if old_inv:
                for old_acc in EMIAccount.query.filter_by(invoice_id=old_inv.id).all():
                    db.session.delete(old_acc)
                db.session.delete(old_inv)
                db.session.commit()

if __name__ == '__main__':
    unittest.main()

