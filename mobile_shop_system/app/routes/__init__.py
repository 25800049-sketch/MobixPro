from flask import Blueprint
from app.routes import auth, dashboard, customers, products, billing, emi, repairs, exchange, suppliers, inventory, notifications, settings

bp = Blueprint('main', __name__)

bp.register_blueprint(auth.bp)
bp.register_blueprint(dashboard.bp)
bp.register_blueprint(customers.bp)
bp.register_blueprint(products.bp)
bp.register_blueprint(billing.bp)
bp.register_blueprint(emi.bp)
bp.register_blueprint(repairs.bp)
bp.register_blueprint(exchange.bp)
bp.register_blueprint(suppliers.bp)
bp.register_blueprint(inventory.bp)
bp.register_blueprint(notifications.bp)
bp.register_blueprint(settings.bp)