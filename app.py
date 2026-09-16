"""
MOBIX — Mobile Shop Management System
Main Application Entrypoint and Blueprints Registration
"""
import os
from flask import Flask, render_template, session, g
from config import Config
from models import db, User
from seed_data import seed_database

# Import Blueprints
from routes.auth_routes import auth_bp
from routes.dashboard_routes import dashboard_bp
from routes.inventory_routes import inventory_bp
from routes.pos_routes import pos_bp
from routes.emi_routes import emi_bp
from routes.repair_routes import repair_bp
from routes.customer_routes import customer_bp
from routes.supplier_routes import supplier_bp
from routes.exchange_routes import exchange_bp
from routes.payment_routes import payment_bp
from routes.report_routes import report_bp
from routes.user_routes import user_bp
from routes.setting_routes import setting_bp
from routes.payroll_routes import payroll_bp
from routes.preorder_routes import preorder_bp, public_prebook_bp

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure uploads and reports directories exist
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(Config.REPORTS_FOLDER, exist_ok=True)

    # Initialize extensions
    db.init_app(app)

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(pos_bp)
    app.register_blueprint(emi_bp)
    app.register_blueprint(repair_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(supplier_bp)
    app.register_blueprint(exchange_bp)
    app.register_blueprint(payment_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(setting_bp)
    app.register_blueprint(payroll_bp)
    app.register_blueprint(preorder_bp)
    app.register_blueprint(public_prebook_bp)

    # Global Context Processor
    @app.context_processor
    def inject_global_vars():
        current_user = None
        if 'user_id' in session:
            current_user = db.session.get(User, session['user_id'])
        return {
            'config': Config,
            'current_user': current_user,
            'user_role': session.get('role', None)
        }

    # Custom Error Handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('base.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        import traceback
        err_msg = traceback.format_exc()
        print("[ERROR 500]", err_msg)
        db.session.rollback()
        return f"<div style='background:#1e1e2f; color:#ff6b6b; padding:30px; font-family:monospace; border-radius:10px; margin:20px;'><h2 style='color:#fff;'>MOBIX Server Error</h2><pre style='white-space:pre-wrap; font-size:13px; color:#f8f9fa;'>{err_msg}</pre></div>", 500


    # Auto-initialize database tables & seed data on startup
    with app.app_context():
        db.create_all()

        # Ensure SQLite has new columns on users and emi_accounts tables if they already exist
        try:
            with db.engine.connect() as conn:
                cursor = conn.connection.cursor()
                cursor.execute("PRAGMA table_info(users);")
                user_cols = [row[1] for row in cursor.fetchall()]
                if 'monthly_salary' not in user_cols:
                    cursor.execute("ALTER TABLE users ADD COLUMN monthly_salary FLOAT DEFAULT 18000.0;")
                if 'daily_rate' not in user_cols:
                    cursor.execute("ALTER TABLE users ADD COLUMN daily_rate FLOAT DEFAULT 692.31;")
                if 'salary_type' not in user_cols:
                    cursor.execute("ALTER TABLE users ADD COLUMN salary_type VARCHAR(20) DEFAULT 'monthly';")

                cursor.execute("PRAGMA table_info(repair_tickets);")
                repair_cols = [row[1] for row in cursor.fetchall()]
                if 'payment_status' not in repair_cols:
                    cursor.execute("ALTER TABLE repair_tickets ADD COLUMN payment_status VARCHAR(20) DEFAULT 'Unpaid';")
                if 'payment_mode' not in repair_cols:
                    cursor.execute("ALTER TABLE repair_tickets ADD COLUMN payment_mode VARCHAR(30) DEFAULT 'Cash';")

                conn.connection.commit()
        except Exception:
            pass

        # If no users exist, auto-seed with rich demo data
        if not User.query.first():
            seed_database(app)

    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print(f"[MOBIX] Starting Mobile Shop Management System on http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)
