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
from app.models.vendor import Vendor
from app.models.audit import AuditLog, Notification
from app.models.controls import ContributionReceipt, CorrectionRequest, ReconciliationRecord, EvidenceRule
from app.services.financial_controls_service import FinancialControlsService, active_event, money
from app.services.audit_service import AuditService

controls_bp = Blueprint('financial_controls', __name__, url_prefix='/finance-controls')


def finance_access():
    """Return whether the current user may mutate financial-control records.

    Financial-control writes are deliberately narrower than ordinary income or
    expense creation. A user who can create an expense/donation must not gain
    reconciliation, correction, sponsorship, or member-contribution authority
    as a side effect.
    """
    return current_user.is_admin or current_user.has_permission('finance.manage')


def deny_unless_finance():
    return jsonify({'error': 'Financial permission required.'}), 403 if not finance_access() else None


def jm(v): return str(money(v))


def payload(): return request.get_json(silent=True) or request.form


def rec_json(r):
    return {'id': r.id, 'reference': r.reconciliation_ref, 'account_id': r.account_id, 'event_id': r.event_id,
            'statement_date': r.statement_date.isoformat(), 'period_start': r.period_start.isoformat() if r.period_start else None,
            'period_end': r.period_end.isoformat() if r.period_end else None, 'book_balance': jm(r.book_balance),
            'statement_balance': jm(r.statement_balance), 'difference': jm(r.difference), 'status': r.status,
            'external_reference': r.external_reference, 'notes': r.notes}

@controls_bp.get('/events')
@login_required
def events_status():
    return jsonify([{'id': e.id, 'title': e.title, 'year': e.year, 'status': e.status, 'is_editable': e.is_editable} for e in Event.query.order_by(Event.year.desc()).all()])

@controls_bp.post('/events/<int:event_id>/close')
@login_required
def close_event(event_id):
    if not current_user.is_admin: return jsonify({'error': 'Administrator access required.'}), 403
    try:
        e = FinancialControlsService.close_event(event_id, current_user, payload().get('reason', ''))
        return jsonify({'ok': True, 'event_id': e.id, 'status': e.status})
    except ValueError as x: return jsonify({'error': str(x)}), 400

@controls_bp.post('/events/<int:event_id>/lock')
@login_required
def lock_event(event_id):
    if not current_user.is_admin: return jsonify({'error': 'Administrator access required.'}), 403
    try:
        e = FinancialControlsService.lock_event(event_id, current_user, payload().get('reason', ''))
        return jsonify({'ok': True, 'event_id': e.id, 'status': e.status})
    except ValueError as x: return jsonify({'error': str(x)}), 400

@controls_bp.post('/financial-years/<int:financial_year_id>/lock')
@login_required
def lock_fy(financial_year_id):
    if not current_user.is_admin: return jsonify({'error': 'Administrator access required.'}), 403
    try:
        fy = FinancialControlsService.lock_financial_year(financial_year_id, current_user, payload().get('reason', ''))
        return jsonify({'ok': True, 'financial_year_id': fy.id, 'is_locked': fy.is_locked})
    except ValueError as x: return jsonify({'error': str(x)}), 400

@controls_bp.post('/sponsorships')
@login_required
def create_sponsorship():
    if not finance_access(): return jsonify({'error': 'Financial permission required.'}), 403
    p = payload()
    try:
        e = db.session.get(Event, int(p.get('event_id'))); e.assert_editable()
        amount = money(p.get('committed_amount'))
        name = str(p.get('sponsor_name', '')).strip()
        if amount <= 0 or not name: raise ValueError('Sponsor name and positive committed amount are required.')
        s = Sponsorship(sponsorship_ref=f'SP-{datetime.utcnow().strftime("%Y%m%d%H%M%S%f")}', event_id=e.id,
            sponsor_name=name, contact_person=p.get('contact_person'), contact_phone=p.get('contact_phone'), contact_email=p.get('contact_email'),
            sponsorship_type=str(p.get('sponsorship_type', 'GENERAL')).strip(), committed_amount=amount,
            received_amount=Decimal('0.00'), pending_amount=amount, status='COMMITTED', notes=p.get('notes'), created_by_id=current_user.id)
        db.session.add(s); db.session.flush(); AuditService.log_action('CREATE', 'SPONSORSHIP', s.id, f'Created {s.sponsorship_ref}.', commit=False); db.session.commit()
        return jsonify({'ok': True, 'id': s.id, 'reference': s.sponsorship_ref}), 201
    except (ValueError, TypeError) as x: db.session.rollback(); return jsonify({'error': str(x)}), 400

@controls_bp.get('/sponsorships')
@login_required
def sponsorships():
    eid = request.args.get('event_id', type=int) or (active_event().id if active_event() else None)
    q = Sponsorship.query.filter_by(event_id=eid) if eid else Sponsorship.query
    return jsonify([{'id': s.id, 'reference': s.sponsorship_ref, 'name': s.sponsor_name, 'committed': jm(s.committed_amount), 'received': jm(s.received_amount), 'pending': jm(s.pending_amount), 'status': s.status} for s in q.all()])

@controls_bp.post('/sponsorships/<int:sponsorship_id>/receipts')
@login_required
def sponsorship_receipt(sponsorship_id):
    if not finance_access(): return jsonify({'error': 'Financial permission required.'}), 403
    p = payload()
    try:
        r = FinancialControlsService.create_contribution_receipt('SPONSORSHIP', sponsorship_id, int(p.get('account_id')), p.get('amount'), str(p.get('payment_mode','CASH')).upper(), current_user, p.get('external_ref'), p.get('notes'))
        return jsonify({'ok': True, 'receipt_ref': r.receipt_ref, 'transaction_id': r.transaction_id}), 201
    except (ValueError, TypeError) as x: db.session.rollback(); return jsonify({'error': str(x)}), 400

@controls_bp.post('/members')
@login_required
def create_member():
    if not finance_access(): return jsonify({'error': 'Financial permission required.'}), 403
    p = payload()
    try:
        e = db.session.get(Event, int(p.get('event_id'))); e.assert_editable(); name = str(p.get('member_name','')).strip(); target = money(p.get('target_amount','0'))
        if not name: raise ValueError('Member name is required.')
        m = MemberContribution(event_id=e.id, member_name=name, member_phone=p.get('member_phone'), designation=p.get('designation'), target_amount=target, received_amount=Decimal('0.00'), pending_amount=target, status='PENDING', notes=p.get('notes'), created_by_id=current_user.id)
        db.session.add(m); db.session.flush(); AuditService.log_action('CREATE','MEMBER_CONTRIBUTION',m.id,f'Created member contribution for {name}.',commit=False); db.session.commit()
        return jsonify({'ok': True, 'id': m.id}), 201
    except (ValueError, TypeError) as x: db.session.rollback(); return jsonify({'error': str(x)}), 400

@controls_bp.get('/members')
@login_required
def members():
    eid = request.args.get('event_id', type=int) or (active_event().id if active_event() else None); q = MemberContribution.query.filter_by(event_id=eid) if eid else MemberContribution.query
    return jsonify([{'id':m.id,'name':m.member_name,'target':jm(m.target_amount),'received':jm(m.received_amount),'pending':jm(m.pending_amount),'status':m.status} for m in q.all()])

@controls_bp.post('/members/<int:member_id>/receipts')
@login_required
def member_receipt(member_id):
    if not finance_access(): return jsonify({'error': 'Financial permission required.'}), 403
    p=payload()
    try:
        r=FinancialControlsService.create_contribution_receipt('MEMBER',member_id,int(p.get('account_id')),p.get('amount'),str(p.get('payment_mode','CASH')).upper(),current_user,p.get('external_ref'),p.get('notes'))
        return jsonify({'ok':True,'receipt_ref':r.receipt_ref,'transaction_id':r.transaction_id}),201
    except (ValueError,TypeError) as x: db.session.rollback(); return jsonify({'error':str(x)}),400

@controls_bp.post('/reconciliations')
@login_required
def reconcile():
    if not finance_access(): return jsonify({'error':'Financial permission required.'}),403
    p=payload()
    try:
        eid=p.get('event_id'); eid=int(eid) if eid else None
        r=FinancialControlsService.reconcile_account(int(p.get('account_id')),date.fromisoformat(p.get('statement_date')),p.get('statement_balance'),current_user,eid,date.fromisoformat(p['period_start']) if p.get('period_start') else None,date.fromisoformat(p['period_end']) if p.get('period_end') else None,p.get('external_reference'),p.get('notes'))
        return jsonify({'ok':True,**rec_json(r)}),201
    except (ValueError,TypeError) as x: db.session.rollback(); return jsonify({'error':str(x)}),400

@controls_bp.get('/reconciliations')
@login_required
def reconciliations():
    q=ReconciliationRecord.query
    if request.args.get('account_id',type=int): q=q.filter_by(account_id=request.args.get('account_id',type=int))
    return jsonify([rec_json(r) for r in q.order_by(ReconciliationRecord.created_at.desc()).all()])

@controls_bp.post('/reconciliations/<int:record_id>/resolve')
@login_required
def resolve_reconciliation(record_id):
    if not current_user.is_admin:return jsonify({'error':'Administrator access required.'}),403
    try:r=FinancialControlsService.resolve_reconciliation(record_id,current_user,payload().get('note',''));return jsonify({'ok':True,'status':r.status})
    except ValueError as x:return jsonify({'error':str(x)}),400

@controls_bp.post('/corrections')
@login_required
def correction():
    if not finance_access():return jsonify({'error':'Financial permission required.'}),403
    p=payload()
    try:
        r=FinancialControlsService.request_correction(str(p.get('entity_type','TRANSACTION')),int(p.get('entity_id')),int(p['transaction_id']) if p.get('transaction_id') else None,p.get('reason',''),current_user)
        for admin in type(current_user).query.filter_by(is_admin=True,is_active=True).all():db.session.add(Notification(user_id=admin.id,title='Correction request pending',message=f'{r.request_ref} requires review.',notification_type='APPROVAL',link='/finance-controls/corrections'))
        db.session.commit();return jsonify({'ok':True,'request_ref':r.request_ref,'status':r.status}),201
    except (ValueError,TypeError) as x:db.session.rollback();return jsonify({'error':str(x)}),400

@controls_bp.post('/corrections/<int:request_id>/review')
@login_required
def review_correction(request_id):
    if not current_user.is_admin:return jsonify({'error':'Administrator access required.'}),403
    p=payload(); approve=str(p.get('approve','')).lower() in ('1','true','yes','approve','approved')
    try:r=FinancialControlsService.review_correction(request_id,current_user,approve,p.get('note',''));return jsonify({'ok':True,'request_ref':r.request_ref,'status':r.status,'reversal_id':r.applied_reversal_id})
    except ValueError as x:db.session.rollback();return jsonify({'error':str(x)}),400

@controls_bp.post('/evidence-rules')
@login_required
def evidence_rule():
    if not current_user.is_admin:return jsonify({'error':'Administrator access required.'}),403
    p=payload()
    try:
        req=p.get('required_categories',[]); req=json.loads(req) if isinstance(req,str) else req
        r=EvidenceRule(name=str(p.get('name','')).strip(),entity_type=str(p.get('entity_type','')).upper(),min_amount=money(p['min_amount']) if p.get('min_amount') not in (None,'') else None,required_categories=json.dumps([str(x).upper() for x in req]),description=p.get('description'),created_by_id=current_user.id)
        if not r.name or not r.entity_type:raise ValueError('Rule name and entity type are required.')
        db.session.add(r);db.session.commit();AuditService.log_action('CREATE','EVIDENCE_RULE',r.id,f'Created evidence rule {r.name}.');return jsonify({'ok':True,'id':r.id}),201
    except (ValueError,TypeError,json.JSONDecodeError) as x:db.session.rollback();return jsonify({'error':str(x)}),400

@controls_bp.get('/evidence/<entity_type>/<int:entity_id>')
@login_required
def evidence(entity_type,entity_id):return jsonify(FinancialControlsService.check_evidence(entity_type,entity_id,request.args.get('amount')))

@controls_bp.get('/timeline/<entity_type>/<int:entity_id>')
@login_required
def timeline(entity_type,entity_id):
    et=entity_type.upper();events=[]
    for d in Document.query.filter_by(entity_type=et,entity_id=entity_id).order_by(Document.created_at.asc()).all():events.append({'at':d.created_at.isoformat(),'type':'DOCUMENT','id':d.id,'label':d.title,'hash':d.current_sha256_hash})
    for a in AuditLog.query.filter_by(entity_type=et,entity_id=str(entity_id)).order_by(AuditLog.created_at.asc()).all():events.append({'at':a.created_at.isoformat(),'type':'AUDIT','id':a.id,'label':a.action,'description':a.description})
    for t in Transaction.query.filter_by(source_id=entity_id).filter(Transaction.source_module.in_([et,f'{et}_CONTRIBUTION'])).order_by(Transaction.created_at.asc()).all():events.append({'at':t.created_at.isoformat(),'type':'TRANSACTION','id':t.id,'label':t.transaction_ref,'amount':jm(t.amount)})
    return jsonify(sorted(events,key=lambda x:x['at']))

@controls_bp.get('/reports/comprehensive')
@login_required
def comprehensive():
    eid=request.args.get('event_id',type=int) or (active_event().id if active_event() else None);e=db.session.get(Event,eid) if eid else None
    ds=Donation.query.filter_by(event_id=eid,status='SUCCESS').all() if eid else [];ss=Sponsorship.query.filter_by(event_id=eid).all() if eid else [];ms=MemberContribution.query.filter_by(event_id=eid).all() if eid else [];es=Expense.query.filter_by(event_id=eid).all() if eid else [];ts=Transaction.query.filter_by(event_id=eid).order_by(Transaction.transaction_date.desc()).all() if eid else []
    di=sum((money(x.amount) for x in ds),Decimal('0.00'));sr=sum((money(x.received_amount) for x in ss),Decimal('0.00'));mr=sum((money(x.received_amount) for x in ms),Decimal('0.00'));ex=sum((money(x.amount) for x in es),Decimal('0.00'))
    return jsonify({'event':{'id':e.id,'title':e.title,'year':e.year,'status':e.status} if e else None,'totals':{'donations':jm(di),'sponsorship_received':jm(sr),'member_received':jm(mr),'income':jm(di+sr+mr),'expense':jm(ex),'balance':jm(di+sr+mr-ex)},'sponsorships':[{'reference':x.sponsorship_ref,'name':x.sponsor_name,'committed':jm(x.committed_amount),'received':jm(x.received_amount),'pending':jm(x.pending_amount),'status':x.status} for x in ss],'members':[{'id':x.id,'name':x.member_name,'target':jm(x.target_amount),'received':jm(x.received_amount),'pending':jm(x.pending_amount),'status':x.status} for x in ms],'transactions':[{'ref':x.transaction_ref,'type':x.transaction_type,'amount':jm(x.amount),'mode':x.payment_mode,'source':x.source_module} for x in ts],'reconciliations':[rec_json(x) for x in ReconciliationRecord.query.filter_by(event_id=eid).all()] if eid else []})

@controls_bp.get('/notifications')
@login_required
def notifications():
    ns=Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(100).all();return jsonify([{'id':n.id,'title':n.title,'message':n.message,'type':n.notification_type,'read':n.is_read,'link':n.link,'created_at':n.created_at.isoformat()} for n in ns])

@controls_bp.post('/notifications/<int:notification_id>/read')
@login_required
def notification_read(notification_id):
    n=Notification.query.filter_by(id=notification_id,user_id=current_user.id).first()
    if not n:return jsonify({'error':'Notification not found.'}),404
    n.is_read=True;db.session.commit();return jsonify({'ok':True})
