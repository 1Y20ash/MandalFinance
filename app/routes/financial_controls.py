import json
from datetime import date, datetime
from decimal import Decimal

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from sqlalchemy import or_

from app.extensions import db
from app.models.mandal import Event, FinancialYear
from app.models.income import Sponsorship, MemberContribution, Donation
from app.models.expense import Expense
from app.models.ledger import Account, Transaction
from app.models.document import Document
from app.models.audit import AuditLog, Notification
from app.models.controls import ContributionReceipt, CorrectionRequest, ReconciliationRecord, EvidenceRule
from app.services.financial_controls_service import FinancialControlsService, active_event, money
from app.services.audit_service import AuditService

controls_bp = Blueprint('financial_controls', __name__, url_prefix='/finance-controls')


def _finance_access():
    return current_user.is_admin or current_user.has_permission('expense.create') or current_user.has_permission('donation.create')


def _require_finance():
    if not _finance_access():
        return jsonify({'error': 'Financial permission required.'}), 403
    return None


def _json_money(value):
    return str(money(value))


def _serialize_reconciliation(r):
    return {
        'id': r.id, 'reference': r.reconciliation_ref, 'account_id': r.account_id, 'event_id': r.event_id,
        'statement_date': r.statement_date.isoformat(), 'period_start': r.period_start.isoformat() if r.period_start else None,
        'period_end': r.period_end.isoformat() if r.period_end else None, 'book_balance': _json_money(r.book_balance),
        'statement_balance': _json_money(r.statement_balance), 'difference': _json_money(r.difference),
        'status': r.status, 'external_reference': r.external_reference, 'notes': r.notes,
    }


@controls_bp.post('/events/<int:event_id>/close')
@login_required
def close_event(event_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Administrator access required.'}), 403
    try:
        event = FinancialControlsService.close_event(event_id, current_user, request.form.get('reason', '') or (request.json or {}).get('reason', ''))
        return jsonify({'ok': True, 'event_id': event.id, 'status': event.status})
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400


@controls_bp.post('/events/<int:event_id>/lock')
@login_required
def lock_event(event_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Administrator access required.'}), 403
    payload = request.get_json(silent=True) or request.form
    try:
        event = FinancialControlsService.lock_event(event_id, current_user, payload.get('reason', ''))
        return jsonify({'ok': True, 'event_id': event.id, 'status': event.status})
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400


@controls_bp.post('/financial-years/<int:financial_year_id>/lock')
@login_required
def lock_financial_year(financial_year_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Administrator access required.'}), 403
    payload = request.get_json(silent=True) or request.form
    try:
        fy = FinancialControlsService.lock_financial_year(financial_year_id, current_user, payload.get('reason', ''))
        return jsonify({'ok': True, 'financial_year_id': fy.id, 'is_locked': fy.is_locked})
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400


@controls_bp.get('/events')
@login_required
def events_status():
    return jsonify([{'id': e.id, 'title': e.title, 'year': e.year, 'status': e.status, 'is_editable': e.is_editable} for e in Event.query.order_by(Event.year.desc(), Event.id.desc()).all()])


@controls_bp.post('/sponsorships')
@login_required
def create_sponsorship():
    denied = _require_finance()
    if denied: return denied
    payload = request.get_json(silent=True) or request.form
    try:
        event = db.session.get(Event, int(payload.get('event_id')))
        event.assert_editable()
        committed = money(payload.get('committed_amount'))
        if committed <= 0: raise ValueError('Committed amount must be greater than zero.')
        sponsor = Sponsorship(sponsorship_ref=f'SP-{datetime.utcnow().strftime("%Y%m%d%H%M%S%f")}', event_id=event.id,
            sponsor_name=str(payload.get('sponsor_name', '')).strip(), contact_person=payload.get('contact_person'),
            contact_phone=payload.get('contact_phone'), contact_email=payload.get('contact_email'),
            sponsorship_type=str(payload.get('sponsorship_type', 'GENERAL')).strip(), committed_amount=committed,
            received_amount=Decimal('0.00'), pending_amount=committed, status='COMMITTED', notes=payload.get('notes'), created_by_id=current_user.id)
        if not sponsor.sponsor_name: raise ValueError('Sponsor name is required.')
        db.session.add(sponsor); db.session.flush()
        AuditService.log_action('CREATE', 'SPONSORSHIP', sponsor.id, f'Created sponsorship {sponsor.sponsorship_ref}.', commit=False)
        db.session.commit()
        return jsonify({'ok': True, 'id': sponsor.id, 'reference': sponsor.sponsorship_ref}), 201
    except (ValueError, TypeError) as exc:
        db.session.rollback(); return jsonify({'error': str(exc)}), 400


@controls_bp.get('/sponsorships')
@login_required
def list_sponsorships():
    event_id = request.args.get('event_id', type=int) or (active_event().id if active_event() else None)
    q = Sponsorship.query.filter_by(event_id=event_id) if event_id else Sponsorship.query
    return jsonify([{'id': s.id, 'reference': s.sponsorship_ref, 'sponsor_name': s.sponsor_name, 'type': s.sponsorship_type,
        'committed_amount': _json_money(s.committed_amount), 'received_amount': _json_money(s.received_amount),
        'pending_amount': _json_money(s.pending_amount), 'status': s.status} for s in q.order_by(Sponsorship.created_at.desc()).all()])


@controls_bp.post('/sponsorships/<int:sponsorship_id>/receipts')
@login_required
def sponsorship_receipt(sponsorship_id):
    denied = _require_finance()
    if denied: return denied
    payload = request.get_json(silent=True) or request.form
    try:
        receipt = FinancialControlsService.create_contribution_receipt('SPONSORSHIP', sponsorship_id,
            int(payload.get('account_id')), payload.get('amount'), payload.get('payment_mode', 'CASH').upper(),
            current_user, payload.get('external_ref'), payload.get('notes'))
        return jsonify({'ok': True, 'receipt_ref': receipt.receipt_ref, 'transaction_id': receipt.transaction_id}), 201
    except (ValueError, TypeError) as exc:
        db.session.rollback(); return jsonify({'error': str(exc)}), 400


@controls_bp.post('/members')
@login_required
def create_member_contribution():
    denied = _require_finance()
    if denied: return denied
    payload = request.get_json(silent=True) or request.form
    try:
        event = db.session.get(Event, int(payload.get('event_id'))); event.assert_editable()
        target = money(payload.get('target_amount', '0'))
        member = MemberContribution(event_id=event.id, member_name=str(payload.get('member_name', '')).strip(),
            member_phone=payload.get('member_phone'), designation=payload.get('designation'), target_amount=target,
            received_amount=Decimal('0.00'), pending_amount=target, status='PENDING', notes=payload.get('notes'), created_by_id=current_user.id)
        if not member.member_name: raise ValueError('Member name is required.')
        db.session.add(member); db.session.flush()
        AuditService.log_action('CREATE', 'MEMBER_CONTRIBUTION', member.id, f'Created member contribution for {member.member_name}.', commit=False)
        db.session.commit()
        return jsonify({'ok': True, 'id': member.id}), 201
    except (ValueError, TypeError) as exc:
        db.session.rollback(); return jsonify({'error': str(exc)}), 400


@controls_bp.get('/members')
@login_required
def list_member_contributions():
    event_id = request.args.get('event_id', type=int) or (active_event().id if active_event() else None)
    q = MemberContribution.query.filter_by(event_id=event_id) if event_id else MemberContribution.query
    return jsonify([{'id': m.id, 'member_name': m.member_name, 'designation': m.designation,
        'target_amount': _json_money(m.target_amount), 'received_amount': _json_money(m.received_amount),
        'pending_amount': _json_money(m.pending_amount), 'status': m.status} for m in q.order_by(MemberContribution.created_at.desc()).all()])


@controls_bp.post('/members/<int:member_id>/receipts')
@login_required
def member_receipt(member_id):
    denied = _require_finance()
    if denied: return denied
    payload = request.get_json(silent=True) or request.form
    try:
        receipt = FinancialControlsService.create_contribution_receipt('MEMBER', member_id,
            int(payload.get('account_id')), payload.get('amount'), payload.get('payment_mode', 'CASH').upper(),
            current_user, payload.get('external_ref'), payload.get('notes'))
        return jsonify({'ok': True, 'receipt_ref': receipt.receipt_ref, 'transaction_id': receipt.transaction_id}), 201
    except (ValueError, TypeError) as exc:
        db.session.rollback(); return jsonify({'error': str(exc)}), 400


@controls_bp.post('/reconciliations')
@login_required
def create_reconciliation():
    denied = _require_finance()
    if denied: return denied
    payload = request.get_json(silent=True) or request.form
    try:
        record = FinancialControlsService.reconcile_account(int(payload.get('account_id')), date.fromisoformat(payload.get('statement_date')),
            payload.get('statement_balance'), current_user, payload.get('event_id', type=int) if hasattr(payload, 'get') else None,
            date.fromisoformat(payload['period_start']) if payload.get('period_start') else None,
            date.fromisoformat(payload['period_end']) if payload.get('period_end') else None,
            payload.get('external_reference'), payload.get('notes'))
        return jsonify({'ok': True, **_serialize_reconciliation(record)}), 201
    except (ValueError, TypeError) as exc:
        db.session.rollback(); return jsonify({'error': str(exc)}), 400


@controls_bp.get('/reconciliations')
@login_required
def list_reconciliations():
    q = ReconciliationRecord.query
    if request.args.get('account_id', type=int): q = q.filter_by(account_id=request.args.get('account_id', type=int))
    return jsonify([_serialize_reconciliation(r) for r in q.order_by(ReconciliationRecord.created_at.desc()).all()])


@controls_bp.post('/reconciliations/<int:record_id>/resolve')
@login_required
def resolve_reconciliation(record_id):
    if not current_user.is_admin: return jsonify({'error': 'Administrator access required.'}), 403
    payload = request.get_json(silent=True) or request.form
    try:
        r = FinancialControlsService.resolve_reconciliation(record_id, current_user, payload.get('note', ''))
        return jsonify({'ok': True, 'status': r.status})
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400


@controls_bp.post('/corrections')
@login_required
def request_correction():
    denied = _require_finance()
    if denied: return denied
    payload = request.get_json(silent=True) or request.form
    try:
        req = FinancialControlsService.request_correction(payload.get('entity_type', 'TRANSACTION'), int(payload.get('entity_id')),
            int(payload['transaction_id']) if payload.get('transaction_id') else None, payload.get('reason', ''), current_user)
        admins = db.session.query(type(current_user)).filter_by(is_admin=True, is_active=True).all()
        for admin in admins:
            db.session.add(Notification(user_id=admin.id, title='Correction request pending', message=f'{req.request_ref} requires review.', notification_type='APPROVAL', link='/finance-controls/corrections'))
        db.session.commit()
        return jsonify({'ok': True, 'request_ref': req.request_ref, 'status': req.status}), 201
    except (ValueError, TypeError) as exc:
        db.session.rollback(); return jsonify({'error': str(exc)}), 400


@controls_bp.post('/corrections/<int:request_id>/review')
@login_required
def review_correction(request_id):
    if not current_user.is_admin: return jsonify({'error': 'Administrator access required.'}), 403
    payload = request.get_json(silent=True) or request.form
    approve = str(payload.get('approve', '')).lower() in ('1', 'true', 'yes', 'approve', 'approved')
    try:
        req = FinancialControlsService.review_correction(request_id, current_user, approve, payload.get('note', ''))
        return jsonify({'ok': True, 'request_ref': req.request_ref, 'status': req.status, 'reversal_id': req.applied_reversal_id})
    except ValueError as exc:
        db.session.rollback(); return jsonify({'error': str(exc)}), 400


@controls_bp.post('/evidence-rules')
@login_required
def create_evidence_rule():
    if not current_user.is_admin: return jsonify({'error': 'Administrator access required.'}), 403
    payload = request.get_json(silent=True) or request.form
    try:
        required = payload.get('required_categories', [])
        if isinstance(required, str): required = json.loads(required)
        rule = EvidenceRule(name=str(payload.get('name', '')).strip(), entity_type=str(payload.get('entity_type', '')).upper(),
            min_amount=money(payload['min_amount']) if payload.get('min_amount') not in (None, '') else None,
            required_categories=json.dumps([str(x).upper() for x in required]), description=payload.get('description'), created_by_id=current_user.id)
        if not rule.name or not rule.entity_type: raise ValueError('Rule name and entity type are required.')
        db.session.add(rule); db.session.commit()
        AuditService.log_action('CREATE', 'EVIDENCE_RULE', rule.id, f'Created evidence rule {rule.name}.')
        return jsonify({'ok': True, 'id': rule.id}), 201
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        db.session.rollback(); return jsonify({'error': str(exc)}), 400


@controls_bp.get('/evidence/<entity_type>/<int:entity_id>')
@login_required
def evidence_status(entity_type, entity_id):
    result = FinancialControlsService.check_evidence(entity_type, entity_id, request.args.get('amount'))
    return jsonify(result)


@controls_bp.get('/timeline/<entity_type>/<int:entity_id>')
@login_required
def evidence_timeline(entity_type, entity_id):
    docs = Document.query.filter_by(entity_type=entity_type.upper(), entity_id=entity_id).order_by(Document.created_at.asc()).all()
    audits = AuditLog.query.filter_by(entity_type=entity_type.upper(), entity_id=str(entity_id)).order_by(AuditLog.created_at.asc()).all()
    transactions = Transaction.query.filter_by(source_module=f'{entity_type.upper()}_CONTRIBUTION', source_id=entity_id).order_by(Transaction.created_at.asc()).all()
    events = []
    for d in docs: events.append({'at': d.created_at.isoformat(), 'type': 'DOCUMENT', 'id': d.id, 'label': d.title, 'hash': d.current_sha256_hash})
    for a in audits: events.append({'at': a.created_at.isoformat(), 'type': 'AUDIT', 'id': a.id, 'label': a.action, 'description': a.description})
    for t in transactions: events.append({'at': t.created_at.isoformat(), 'type': 'TRANSACTION', 'id': t.id, 'label': t.transaction_ref, 'amount': _json_money(t.amount)})
    return jsonify(sorted(events, key=lambda x: x['at']))


@controls_bp.get('/reports/comprehensive')
@login_required
def comprehensive_report():
    event_id = request.args.get('event_id', type=int) or (active_event().id if active_event() else None)
    event = db.session.get(Event, event_id) if event_id else None
    donations = Donation.query.filter_by(event_id=event_id, status='SUCCESS').all() if event_id else []
    sponsorships = Sponsorship.query.filter_by(event_id=event_id).all() if event_id else []
    members = MemberContribution.query.filter_by(event_id=event_id).all() if event_id else []
    expenses = Expense.query.filter_by(event_id=event_id).all() if event_id else []
    transactions = Transaction.query.filter_by(event_id=event_id).order_by(Transaction.transaction_date.desc()).all() if event_id else []
    total_income = sum((money(d.amount) for d in donations), Decimal('0.00')) + sum((money(s.received_amount) for s in sponsorships), Decimal('0.00')) + sum((money(m.received_amount) for m in members), Decimal('0.00'))
    total_expense = sum((money(e.amount) for e in expenses), Decimal('0.00'))
    return jsonify({
        'event': {'id': event.id, 'title': event.title, 'year': event.year, 'status': event.status} if event else None,
        'totals': {'donations': _json_money(sum((money(d.amount) for d in donations), Decimal('0.00'))),
                   'sponsorship_received': _json_money(sum((money(s.received_amount) for s in sponsorships), Decimal('0.00'))),
                   'member_received': _json_money(sum((money(m.received_amount) for m in members), Decimal('0.00'))),
                   'income': _json_money(total_income), 'expense': _json_money(total_expense), 'balance': _json_money(total_income - total_expense)},
        'sponsorships': [{'reference': s.sponsorship_ref, 'name': s.sponsor_name, 'committed': _json_money(s.committed_amount), 'received': _json_money(s.received_amount), 'pending': _json_money(s.pending_amount), 'status': s.status} for s in sponsorships],
        'members': [{'id': m.id, 'name': m.member_name, 'target': _json_money(m.target_amount), 'received': _json_money(m.received_amount), 'pending': _json_money(m.pending_amount), 'status': m.status} for m in members],
        'expenses': [{'id': e.id, 'amount': _json_money(e.amount), 'status': getattr(e, 'status', None)} for e in expenses],
        'transactions': [{'ref': t.transaction_ref, 'type': t.transaction_type, 'amount': _json_money(t.amount), 'mode': t.payment_mode, 'source': t.source_module} for t in transactions],
        'reconciliations': [_serialize_reconciliation(r) for r in ReconciliationRecord.query.filter_by(event_id=event_id).order_by(ReconciliationRecord.created_at.desc()).all()] if event_id else [],
    })


@controls_bp.get('/notifications')
@login_required
def notifications():
    rows = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(100).all()
    return jsonify([{'id': n.id, 'title': n.title, 'message': n.message, 'type': n.notification_type, 'read': n.is_read, 'link': n.link, 'created_at': n.created_at.isoformat()} for n in rows])


@controls_bp.post('/notifications/<int:notification_id>/read')
@login_required
def mark_notification_read(notification_id):
    n = Notification.query.filter_by(id=notification_id, user_id=current_user.id).first()
    if not n: return jsonify({'error': 'Notification not found.'}), 404
    n.is_read = True; db.session.commit()
    return jsonify({'ok': True})


@controls_bp.get('/search')
@login_required
def unified_search():
    term = request.args.get('q', '').strip()
    if len(term) < 2: return jsonify({'error': 'Search term must contain at least 2 characters.'}), 400
    like = f'%{term}%'
    event_id = request.args.get('event_id', type=int)
    results = {'donations': [], 'expenses': [], 'transactions': [], 'documents': [], 'sponsorships': [], 'members': [], 'vendors': []}
    dq = Donation.query.filter(or_(Donation.donation_number.ilike(like), Donation.donor_name.ilike(like)))
    sq = Sponsorship.query.filter(or_(Sponsorship.sponsorship_ref.ilike(like), Sponsorship.sponsor_name.ilike(like)))
    mq = MemberContribution.query.filter(MemberContribution.member_name.ilike(like))
    tq = Transaction.query.filter(or_(Transaction.transaction_ref.ilike(like), Transaction.description.ilike(like), Transaction.external_ref.ilike(like)))
    eq = Expense.query.filter(Expense.description.ilike(like))
    docq = Document.query.filter(or_(Document.doc_ref.ilike(like), Document.title.ilike(like), Document.original_filename.ilike(like)))
    if event_id:
        dq = dq.filter_by(event_id=event_id); sq = sq.filter_by(event_id=event_id); mq = mq.filter_by(event_id=event_id); tq = tq.filter_by(event_id=event_id); eq = eq.filter_by(event_id=event_id)
    results['donations'] = [{'id': d.id, 'ref': d.donation_number, 'name': d.donor_name, 'amount': _json_money(d.amount)} for d in dq.limit(25).all()]
    results['sponsorships'] = [{'id': s.id, 'ref': s.sponsorship_ref, 'name': s.sponsor_name, 'amount': _json_money(s.committed_amount)} for s in sq.limit(25).all()]
    results['members'] = [{'id': m.id, 'name': m.member_name, 'amount': _json_money(m.target_amount)} for m in mq.limit(25).all()]
    results['transactions'] = [{'id': t.id, 'ref': t.transaction_ref, 'type': t.transaction_type, 'amount': _json_money(t.amount)} for t in tq.limit(25).all()]
    results['expenses'] = [{'id': e.id, 'amount': _json_money(e.amount), 'description': e.description} for e in eq.limit(25).all()]
    results['documents'] = [{'id': d.id, 'ref': d.doc_ref, 'title': d.title, 'category': d.category} for d in docq.limit(25).all()]
    return jsonify(results)
