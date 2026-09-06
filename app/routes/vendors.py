from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.models.vendor import Vendor
from app.extensions import db
from app.utils.decorators import permission_required

vendors_bp = Blueprint('vendors', __name__, url_prefix='/vendors')

@vendors_bp.route('/')
@login_required
@permission_required('vendor.view')
def list_vendors():
    vendors = Vendor.query.order_by(Vendor.name.asc()).all()
    return render_template('vendors/list.html', vendors=vendors)

@vendors_bp.route('/create', methods=['GET', 'POST'])
@login_required
@permission_required('vendor.create')
def create_vendor():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category = request.form.get('category', '').strip()
        contact_person = request.form.get('contact_person', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        address = request.form.get('address', '').strip()
        bank_name = request.form.get('bank_name', '').strip()
        account_number = request.form.get('account_number', '').strip()
        ifsc_code = request.form.get('ifsc_code', '').strip()
        upi_id = request.form.get('upi_id', '').strip()
        gstin = request.form.get('gstin', '').strip()

        try:
            vendor = Vendor(
                name=name,
                category=category,
                contact_person=contact_person,
                phone=phone,
                email=email,
                address=address,
                bank_name=bank_name,
                account_number=account_number,
                ifsc_code=ifsc_code,
                upi_id=upi_id,
                gstin=gstin
            )
            db.session.add(vendor)
            db.session.commit()
            flash(f'Vendor "{name}" created successfully.', 'success')
            return redirect(url_for('vendors.list_vendors'))
        except Exception as e:
            flash(f'Error creating vendor: {str(e)}', 'danger')

    return render_template('vendors/create.html')
