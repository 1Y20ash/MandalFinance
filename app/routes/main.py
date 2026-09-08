from flask import Blueprint, redirect, url_for, jsonify, send_from_directory, current_app
from flask_login import current_user
from app.extensions import db
import os

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    return redirect(url_for('public.transparency'))

@main_bp.route('/sw.js')
def service_worker():
    static_folder = os.path.join(current_app.root_path, 'static')
    return send_from_directory(static_folder, 'sw.js', mimetype='application/javascript')

@main_bp.route('/manifest.json')
def pwa_manifest():
    static_folder = os.path.join(current_app.root_path, 'static')
    return send_from_directory(static_folder, 'manifest.json', mimetype='application/json')

@main_bp.route('/health')
def health():
    try:
        # Check DB connectivity
        db.session.execute(db.text('SELECT 1'))
        db_status = "HEALTHY"
    except Exception as e:
        db_status = f"UNHEALTHY: {str(e)}"

    return jsonify({
        'status': 'OK' if db_status == 'HEALTHY' else 'DEGRADED',
        'database': db_status,
        'app_name': 'Shree Ashtavinayak Ganesh Utsav Mandal Financial System',
        'version': '1.0.0'
    })
