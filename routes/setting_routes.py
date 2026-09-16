"""
Store Settings Controller
Configuration for store profile, tax rates, invoice branding, and system preferences.
"""
from flask import Blueprint, render_template, request, flash, redirect, url_for
from config import Config
from routes.auth_routes import login_required, roles_accepted

setting_bp = Blueprint('settings', __name__, url_prefix='/settings')

# In-memory settings state for store customization (or backed by Config)
STORE_SETTINGS = {
    'store_name': 'MOBIXPRO Electronics & Mobile World',
    'tagline': 'Your Shop • Your Success',
    'contact_phone': '+91 98765 43210',
    'contact_email': 'support@mobixpro.com',
    'store_address': 'Shop 104, Cyber Plaza, Tech Hub, Mumbai, MH - 400001',
    'gstin': '27ABCDE1234F1Z5',
    'tax_rate': 18.0,
    'emi_late_fine': 200.0,
    'currency': 'INR (₹)',
    'auto_backup': True,
    'floating_theme_default': 'enabled',
    'floating_theme_style': 'cyber-glass'
}

@setting_bp.route('/', methods=['GET', 'POST'])
@login_required
@roles_accepted('admin')
def settings_page():
    if request.method == 'POST':
        STORE_SETTINGS['store_name'] = request.form.get('store_name', STORE_SETTINGS['store_name'])
        STORE_SETTINGS['tagline'] = request.form.get('tagline', STORE_SETTINGS['tagline'])
        STORE_SETTINGS['contact_phone'] = request.form.get('contact_phone', STORE_SETTINGS['contact_phone'])
        STORE_SETTINGS['contact_email'] = request.form.get('contact_email', STORE_SETTINGS['contact_email'])
        STORE_SETTINGS['store_address'] = request.form.get('store_address', STORE_SETTINGS['store_address'])
        STORE_SETTINGS['gstin'] = request.form.get('gstin', STORE_SETTINGS['gstin'])
        STORE_SETTINGS['tax_rate'] = float(request.form.get('tax_rate', STORE_SETTINGS['tax_rate']))
        STORE_SETTINGS['emi_late_fine'] = float(request.form.get('emi_late_fine', STORE_SETTINGS['emi_late_fine']))
        STORE_SETTINGS['floating_theme_default'] = request.form.get('floating_theme_default', STORE_SETTINGS.get('floating_theme_default', 'enabled'))
        STORE_SETTINGS['floating_theme_style'] = request.form.get('floating_theme_style', STORE_SETTINGS.get('floating_theme_style', 'cyber-glass'))
        
        flash('Store settings updated successfully!', 'success')
        return redirect(url_for('settings.settings_page'))

    return render_template('settings/index.html', settings=STORE_SETTINGS)
