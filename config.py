import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'mobix_production_ready_secret_key_889922')
    db_url = os.getenv('DATABASE_URL', 'sqlite:///mobix.db')
    if os.getenv('RENDER') and 'localhost' in db_url:
        db_url = f"sqlite:///{BASE_DIR / 'mobix.db'}"
    SQLALCHEMY_DATABASE_URI = db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Uploads & Reports directory
    UPLOAD_FOLDER = BASE_DIR / 'static' / 'uploads'
    REPORTS_FOLDER = BASE_DIR / 'static' / 'reports'
    
    # Mail settings
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() in ('true', '1')
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'MOBIXPRO Electronics <sales@mobixpro.com>')
    
    # Shop details for Invoices
    SHOP_NAME = "MOBIXPRO Mobile Store & Services"
    SHOP_TAGLINE = "Premium Smart Devices • Express Repairs • Smart EMI"
    SHOP_ADDRESS = "104, raja Street, Commercial Hub"
    SHOP_PHONE = "+91 98765 43210"
    SHOP_EMAIL = "support@mobixpro.com"
    SHOP_GST = "29AAAAA0000A1Z5"
    CURRENCY_SYMBOL = "₹"
