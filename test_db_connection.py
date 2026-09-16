"""
MOBIX Database Connectivity & Health Check
Verifies Flask SQLAlchemy connectivity to MySQL mobix_db
"""
import sys
from app import create_app
from models import (
    db, User, Customer, Supplier, Mobile, Accessory,
    Invoice, RepairTicket, EMIAccount, SupplierPurchase
)

def run_health_check():
    print("=" * 60)
    print("  MOBIX DATABASE CONNECTIVITY & INTEGRITY CHECK")
    print("=" * 60)

    try:
        app = create_app()
    except Exception as e:
        print(f"[FAIL] App initialization error: {e}")
        return False

    with app.app_context():
        # 1. Test Low-Level Engine Connection
        try:
            with db.engine.connect() as conn:
                res = conn.exec_driver_sql("SELECT VERSION(), DATABASE();").fetchone()
                print(f"[PASS] Connected to MySQL Engine: {res[0]}")
                print(f"[PASS] Active Database: `{res[1]}`")
        except Exception as e:
            print(f"[FAIL] Engine connection failed: {e}")
            return False

        # 2. Test Table Row Counts
        print("-" * 60)
        print("  TABLE ROW COUNTS & HEALTH")
        print("-" * 60)
        models_to_check = [
            ("Users", User),
            ("Customers", Customer),
            ("Suppliers", Supplier),
            ("Mobiles", Mobile),
            ("Accessories", Accessory),
            ("Invoices", Invoice),
            ("Repair Tickets", RepairTicket),
            ("EMI Accounts", EMIAccount),
            ("Supplier Purchases", SupplierPurchase),
        ]

        all_ok = True
        for name, model in models_to_check:
            try:
                count = model.query.count()
                print(f"  [OK] {name:20}: {count} records found")
            except Exception as e:
                print(f"  [FAIL] {name:20}: Query error -> {e}")
                all_ok = False

        # 3. Test User Authentication Check
        print("-" * 60)
        print("  USER AUTHENTICATION VERIFICATION")
        print("-" * 60)
        for username, plain_pw in [('admin', 'admin123'), ('cashier', 'cashier123'), ('tech', 'tech123')]:
            user = User.query.filter_by(username=username).first()
            if user:
                pw_valid = user.check_password(plain_pw)
                status = "VERIFIED" if pw_valid else "PASSWORD MISMATCH"
                print(f"  [OK] User '{username}' ({user.role}): {status}")
            else:
                print(f"  [FAIL] User '{username}' NOT FOUND")
                all_ok = False

        # 4. Test Transaction (Write, Query, Rollback)
        print("-" * 60)
        print("  READ/WRITE TRANSACTION TEST")
        print("-" * 60)
        try:
            test_customer = Customer(
                name="Temp DB Test",
                phone="9999999999",
                email="dbtest@example.com"
            )
            db.session.add(test_customer)
            db.session.flush()
            test_id = test_customer.id
            fetched = db.session.get(Customer, test_id)
            assert fetched is not None and fetched.name == "Temp DB Test"
            db.session.rollback()  # rollback cleanly so no junk is stored
            print(f"  [OK] Read/Write/Rollback transaction: 100% OPERATIONAL")
        except Exception as e:
            db.session.rollback()
            print(f"  [FAIL] Transaction test failed: {e}")
            all_ok = False

        print("=" * 60)
        if all_ok:
            print("  >>> STATUS: DATABASE CONNECTIVITY IS 100% PERFECT! <<<")
        else:
            print("  >>> STATUS: SOME ISSUES DETECTED <<<")
        print("=" * 60)
        return all_ok

if __name__ == '__main__':
    success = run_health_check()
    sys.exit(0 if success else 1)
