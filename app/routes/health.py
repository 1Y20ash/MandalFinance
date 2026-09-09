from flask import Blueprint, jsonify
from app.extensions import db, limiter

health_bp = Blueprint('health', __name__, url_prefix='/health')


@health_bp.get('/live')
@limiter.exempt
def live():
    return jsonify({'status': 'ok'})


@health_bp.get('/ready')
@limiter.exempt
def ready():
    checks = {}
    try:
        db.session.execute(db.text('SELECT 1'))
        checks['database'] = 'ok'
    except Exception:
        checks['database'] = 'unavailable'
    ready_state = all(value == 'ok' for value in checks.values())
    return jsonify({'status': 'ready' if ready_state else 'not_ready', 'checks': checks}), 200 if ready_state else 503
