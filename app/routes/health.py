from flask import Blueprint, jsonify, current_app
from sqlalchemy import text
from app.extensions import db

health_bp = Blueprint('health', __name__, url_prefix='/health')

@health_bp.get('/live')
def live():
    return jsonify({'status':'ok','service':'MandalFinance'}), 200

@health_bp.get('/ready')
def ready():
    checks={}
    try:
        db.session.execute(text('SELECT 1'))
        checks['database']='ok'
    except Exception as exc:
        current_app.logger.exception('Readiness database check failed')
        checks['database']='failed'
    if current_app.config.get('APP_ENV')=='production':
        checks['private_storage']='ok' if current_app.config.get('SUPABASE_URL') and current_app.config.get('SUPABASE_SERVICE_ROLE_KEY') and current_app.config.get('SUPABASE_STORAGE_PRIVATE') else 'failed'
        checks['payment_gateway']='ok' if current_app.config.get('PAYMENT_GATEWAY_DRIVER')=='razorpay' else 'failed'
    else:
        checks['private_storage']='development-mode'
        checks['payment_gateway']=current_app.config.get('PAYMENT_GATEWAY_DRIVER','mock')
    ok=all(v in ('ok','development-mode','mock') for v in checks.values())
    return jsonify({'status':'ready' if ok else 'not_ready','checks':checks}),200 if ok else 503
