from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.services.reconciliation_service import ReconciliationService
from app.models.controls import ReconciliationRecord
from app.models.reconciliation import ReconciliationLine
from app.utils.decorators import permission_required

reconciliation_bp = Blueprint('reconciliation', __name__, url_prefix='/finance-controls/reconciliation')


def payload():
    return request.get_json(silent=True) or request.form


def _line_json(line):
    return {
        'id': line.id,
        'line_ref': line.line_ref,
        'transaction_date': line.transaction_date.isoformat(),
        'description': line.description,
        'external_ref': line.external_ref,
        'amount': str(line.amount),
        'matched_transaction_id': line.matched_transaction_id,
        'status': line.status,
        'match_note': line.match_note,
    }


@reconciliation_bp.get('/<int:record_id>/lines')
@login_required
@permission_required('finance.view')
def list_lines(record_id):
    record = ReconciliationRecord.query.get_or_404(record_id)
    return jsonify([_line_json(x) for x in ReconciliationLine.query.filter_by(reconciliation_id=record.id).order_by(ReconciliationLine.id).all()])


@reconciliation_bp.post('/<int:record_id>/import')
@login_required
@permission_required('finance.manage')
def import_lines(record_id):
    p = payload()
    rows = p.get('lines', [])
    if isinstance(rows, str):
        import json
        try:
            rows = json.loads(rows)
        except json.JSONDecodeError:
            return jsonify({'error': 'lines must contain valid JSON.'}), 400
    try:
        lines = ReconciliationService.import_lines(record_id, rows, current_user)
        return jsonify({'ok': True, 'count': len(lines), 'lines': [_line_json(x) for x in lines]}), 201
    except (ValueError, TypeError) as exc:
        return jsonify({'error': str(exc)}), 400


@reconciliation_bp.post('/lines/<int:line_id>/match')
@login_required
@permission_required('finance.manage')
def match_line(line_id):
    try:
        line = ReconciliationService.match_line(line_id, current_user)
        return jsonify({'ok': True, 'line': _line_json(line)})
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400


@reconciliation_bp.post('/<int:record_id>/finalize')
@login_required
@permission_required('finance.manage')
def finalize(record_id):
    try:
        record = ReconciliationService.finalize(record_id, current_user)
        return jsonify({'ok': True, 'status': record.status, 'reconciliation_ref': record.reconciliation_ref})
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
