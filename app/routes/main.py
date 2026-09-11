from flask import Blueprint, redirect, url_for, jsonify, send_from_directory, current_app, render_template
from flask_login import current_user
from app.extensions import db
import os

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    return redirect(url_for('public.transparency'))

@main_bp.route('/privacy')
def privacy_notice():
    return render_template('public/privacy.html')

@main_bp.route('/sw.js')
def service_worker():
    static_folder = os.path.join(current_app.root_path, 'static')
    return send_from_directory(static_folder, 'sw.js', mimetype='application/javascript')

@main_bp.route('/manifest.json')
def pwa_manifest():
    static_folder = os.path.join(current_app.root_path, 'static')
    return send_from_directory(static_folder, 'manifest.json', mimetype='application/json')


def _database_health():
    try:
        db.session.execute(db.text('SELECT 1'))
        return True
    except Exception:
        current_app.logger.exception('Health database check failed')
        db.session.rollback()
        return False


@main_bp.route('/health/live')
def health_live():
    return jsonify({'status': 'OK'}), 200


@main_bp.route('/health/ready')
def health_ready():
    if not _database_health():
        return jsonify({'status': 'UNHEALTHY', 'database': 'UNHEALTHY'}), 503
    return jsonify({'status': 'READY', 'database': 'HEALTHY'}), 200


@main_bp.route('/health')
def health():
    db_healthy = _database_health()
    return jsonify({
        'status': 'OK' if db_healthy else 'DEGRADED',
        'database': 'HEALTHY' if db_healthy else 'UNHEALTHY',
        'app_name': 'Shree Ashtavinayak Ganesh Utsav Mandal Financial System',
        'version': '1.0.0'
    }), 200
