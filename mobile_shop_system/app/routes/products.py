from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from app.models import db, Product, Category, Supplier

bp = Blueprint('products', __name__)

@bp.route('/products')
@login_required
def product_list():
    products = Product.query.filter_by(is_active=True).order_by(Product.created_at.desc()).all()
    categories = Category.query.filter_by(is_active=True).all()
    return render_template('products.html', products=products, categories=categories)

@bp.route('/products/add', methods=['POST'])
@login_required
def add_product():
    from app.models import Product
    code = request.form.get('product_code')
    if Product.query.filter_by(product_code=code).first():
        flash('Product code exists', 'danger')
        return redirect(url_for('products.product_list'))
    p = Product(
        product_code=code, name=request.form.get('name'),
        category_id=request.form.get('category_id'),
        supplier_id=request.form.get('supplier_id'),
        brand=request.form.get('brand'), model=request.form.get('model'),
        color=request.form.get('color'), storage=request.form.get('storage'),
        ram=request.form.get('ram'),
        purchase_price=float(request.form.get('purchase_price')),
        selling_price=float(request.form.get('selling_price')),
        mrp=float(request.form.get('mrp', 0)),
        quantity_in_stock=int(request.form.get('quantity', 0)),
        warranty_period=int(request.form.get('warranty', 12))
    )
    db.session.add(p)
    db.session.commit()
    flash('Product added', 'success')
    return redirect(url_for('products.product_list'))

@bp.route('/products/edit/<int:id>', methods=['POST'])
@login_required
def edit_product(id):
    p = Product.query.get_or_404(id)
    p.name = request.form.get('name')
    p.selling_price = float(request.form.get('selling_price'))
    p.purchase_price = float(request.form.get('purchase_price'))
    p.quantity_in_stock = int(request.form.get('quantity', p.quantity_in_stock))
    p.warranty_period = int(request.form.get('warranty', p.warranty_period))
    db.session.commit()
    flash('Product updated', 'success')
    return redirect(url_for('products.product_list'))

@bp.route('/products/delete/<int:id>')
@login_required
def delete_product(id):
    p = Product.query.get_or_404(id)
    p.is_active = False
    db.session.commit()
    flash('Product deactivated', 'info')
    return redirect(url_for('products.product_list'))

@bp.route('/products/stock/<int:id>')
@login_required
def product_stock(id):
    p = Product.query.get_or_404(id)
    return jsonify({'product_code': p.product_code, 'name': p.name,
                    'stock': p.quantity_in_stock, 'min': p.min_stock_level,
                    'is_low': p.is_low_stock})