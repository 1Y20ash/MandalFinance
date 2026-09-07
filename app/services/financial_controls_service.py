import json
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from sqlalchemy import func
from app.extensions import db
from app.models.mandal import Event, FinancialYear
from app.models.ledger import Account, Transaction
from app.models.income import Sponsorship, MemberContribution
from app.models.controls import ContributionReceipt, CorrectionRequest, ReconciliationRecord, EvidenceRule
from app.models.document import Document
from app.services.audit_service import AuditService
from app.services.ledger_service import LedgerService

ZERO=Decimal('0.00')

def money(value):
    try:return Decimal(str(value or '0')).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)
    except (InvalidOperation,TypeError,ValueError):raise ValueError('Invalid monetary value.')

def active_event():return Event.query.filter_by(is_active=True).first()

def assert_event_open(event):
    if not event:raise ValueError('Event not found.')
    event.assert_editable()

class FinancialControlsService:
    @staticmethod
    def lock_event(event_id,user,reason):
        event=db.session.get(Event,event_id)
        if not event or event.status=='LOCKED':raise ValueError('Event not found or already locked.')
        if not reason or not reason.strip():raise ValueError('A closure reason is required.')
        event.status='LOCKED';event.locked_at=datetime.utcnow();event.locked_by_id=user.id;event.closure_reason=reason.strip()
        AuditService.log_action('LOCK','EVENT',event.id,f'Event {event.title} locked. Reason: {reason.strip()}',commit=False);db.session.commit();return event

    @staticmethod
    def close_event(event_id,user,reason):
        event=db.session.get(Event,event_id)
        if not event or event.status!='OPEN':raise ValueError('Only an open event can be closed.')
        if not reason or not reason.strip():raise ValueError('A closure reason is required.')
        event.status='CLOSED';event.locked_at=datetime.utcnow();event.locked_by_id=user.id;event.closure_reason=reason.strip()
        AuditService.log_action('CLOSE','EVENT',event.id,f'Event {event.title} closed. Reason: {reason.strip()}',commit=False);db.session.commit();return event

    @staticmethod
    def lock_financial_year(financial_year_id,user,reason):
        fy=db.session.get(FinancialYear,financial_year_id)
        if not fy or fy.is_locked:raise ValueError('Financial year not found or already locked.')
        if not reason or not reason.strip():raise ValueError('A locking reason is required.')
        fy.is_locked=True;fy.locked_at=datetime.utcnow();fy.locked_by_id=user.id
        AuditService.log_action('LOCK','FINANCIAL_YEAR',fy.id,f'Financial year {fy.name} locked. Reason: {reason.strip()}',commit=False);db.session.commit();return fy

    @staticmethod
    def create_contribution_receipt(source_type,source_id,account_id,amount,payment_mode,user,external_ref=None,notes=None):
        source_type=source_type.upper();amount=money(amount);payment_mode=payment_mode.upper()
        if amount<=ZERO:raise ValueError('Contribution amount must be greater than zero.')
        if source_type not in ('SPONSORSHIP','MEMBER'):raise ValueError('Unsupported contribution source.')
        if payment_mode not in {'CASH','UPI','BANK_TRANSFER','CHEQUE','GATEWAY'}:raise ValueError('Invalid contribution payment mode.')
        source=db.session.get(Sponsorship if source_type=='SPONSORSHIP' else MemberContribution,source_id)
        if not source:raise ValueError('Contribution record not found.')
        event=db.session.get(Event,source.event_id);assert_event_open(event)
        account=db.session.get(Account,account_id)
        if not account or not account.is_active:raise ValueError('Selected receiving account is not active.')
        if external_ref and Transaction.query.filter_by(external_ref=external_ref).first():raise ValueError('This external payment reference is already recorded.')
        evidence=FinancialControlsService.check_evidence(source_type,source_id,amount)
        if not evidence['complete']:
            missing=sorted({category for failure in evidence['failures'] for category in failure['missing']})
            raise ValueError('Required evidence is missing before contribution posting: '+', '.join(missing))
        if source_type=='SPONSORSHIP':
            current=money(source.received_amount)
            if current+amount>money(source.committed_amount):raise ValueError('Receipt exceeds the sponsorship commitment.')
            source.received_amount=current+amount;source.pending_amount=money(source.committed_amount)-source.received_amount;source.status='RECEIVED' if source.pending_amount==ZERO else 'PARTIAL'
        else:
            current=money(source.received_amount)
            if money(source.target_amount)>ZERO and current+amount>money(source.target_amount):raise ValueError('Receipt exceeds the member contribution target.')
            source.received_amount=current+amount;source.pending_amount=max(ZERO,money(source.target_amount)-source.received_amount);source.status='RECEIVED' if source.pending_amount==ZERO else 'PARTIAL';source.payment_mode=payment_mode;source.transaction_ref=external_ref
        receipt=ContributionReceipt(receipt_ref=f'RCPT-{datetime.utcnow().strftime("%Y%m%d%H%M%S%f")}',source_type=source_type,source_id=source_id,event_id=source.event_id,account_id=account.id,amount=amount,payment_mode=payment_mode,external_ref=external_ref,notes=notes,created_by_id=user.id)
        db.session.add(receipt);db.session.flush()
        txn=LedgerService.record_income(account.id,amount,f'{source_type.title()} contribution {receipt.receipt_ref}','CONTRIBUTION_RECEIPT',receipt.id,user.id,payment_mode=payment_mode,external_ref=external_ref or receipt.receipt_ref,event_id=source.event_id,commit=False)
        receipt.transaction_id=txn.id
        AuditService.log_action('CREATE','CONTRIBUTION_RECEIPT',receipt.id,f'Recorded {source_type} contribution receipt {receipt.receipt_ref} for ₹{amount}',commit=False);db.session.commit();return receipt

    @staticmethod
    def request_correction(entity_type,entity_id,transaction_id,reason,user):
        if not reason or not reason.strip():raise ValueError('Correction reason is required.')
        if transaction_id and not db.session.get(Transaction,transaction_id):raise ValueError('Referenced transaction does not exist.')
        r=CorrectionRequest(request_ref=f'COR-{datetime.utcnow().strftime("%Y%m%d%H%M%S%f")}',entity_type=entity_type.upper(),entity_id=entity_id,transaction_id=transaction_id,reason=reason.strip(),requested_by_id=user.id)
        db.session.add(r);db.session.flush();AuditService.log_action('REQUEST_CORRECTION',entity_type.upper(),entity_id,f'Correction request {r.request_ref} created: {reason.strip()}',commit=False);db.session.commit();return r

    @staticmethod
    def review_correction(request_id,reviewer,approve,note=''):
        r=db.session.get(CorrectionRequest,request_id)
        if not r or r.status!='PENDING':raise ValueError('Pending correction request not found.')
        if r.requested_by_id==reviewer.id:raise ValueError('Self-approval is forbidden.')
        r.reviewed_by_id=reviewer.id;r.reviewed_at=datetime.utcnow();r.review_note=note.strip() or None
        if not approve:
            r.status='REJECTED';AuditService.log_action('REJECT','CORRECTION',r.id,f'Correction {r.request_ref} rejected.',commit=False);db.session.commit();return r
        if r.transaction_id:
            reversal=LedgerService.reverse_transaction(r.transaction_id,reviewer.id,f'Approved correction {r.request_ref}: {r.reason}');r.applied_reversal_id=reversal.id;r.status='APPLIED'
        else:r.status='APPROVED'
        AuditService.log_action('APPROVE','CORRECTION',r.id,f'Correction {r.request_ref} approved and applied.',commit=False);db.session.commit();return r

    @staticmethod
    def reconcile_account(account_id,statement_date,statement_balance,user,event_id=None,period_start=None,period_end=None,external_reference=None,notes=None):
        account=db.session.get(Account,account_id)
        if not account or not account.is_active:raise ValueError('Account not found or inactive.')
        statement_balance=money(statement_balance)
        if period_start and period_end and period_start>period_end:raise ValueError('Reconciliation period start cannot be after period end.')
        if period_end and statement_date<period_end:raise ValueError('Statement date cannot precede the reconciliation period end.')
        duplicate=ReconciliationRecord.query.filter_by(account_id=account.id,statement_date=statement_date).first()
        if duplicate:raise ValueError('A reconciliation already exists for this account and statement date.')
        opening=money(account.opening_balance)
        q=Transaction.query.filter(Transaction.account_id==account.id,Transaction.is_reversed.is_(False))
        if period_start:q=q.filter(func.date(Transaction.transaction_date)>=period_start)
        if period_end:q=q.filter(func.date(Transaction.transaction_date)<=period_end)
        income=q.filter(Transaction.transaction_type=='INCOME').with_entities(func.coalesce(func.sum(Transaction.amount),0)).scalar()
        expense=q.filter(Transaction.transaction_type.in_(['EXPENSE','REVERSAL'])).with_entities(func.coalesce(func.sum(Transaction.amount),0)).scalar()
        transfers_in=q.filter(Transaction.transaction_type=='TRANSFER').filter(Transaction.description.ilike('%transfer in%')).with_entities(func.coalesce(func.sum(Transaction.amount),0)).scalar()
        transfers_out=q.filter(Transaction.transaction_type=='TRANSFER').filter(Transaction.description.ilike('%transfer out%')).with_entities(func.coalesce(func.sum(Transaction.amount),0)).scalar()
        book=opening+money(income)+money(transfers_in)-money(expense)-money(transfers_out)
        difference=statement_balance-book
        r=ReconciliationRecord(reconciliation_ref=f'REC-{datetime.utcnow().strftime("%Y%m%d%H%M%S%f")}',event_id=event_id,account_id=account.id,statement_date=statement_date,period_start=period_start,period_end=period_end,book_balance=book,statement_balance=statement_balance,difference=difference,status='MATCHED' if difference==ZERO else 'ADJUSTMENT_REQUIRED',external_reference=external_reference,notes=notes,created_by_id=user.id)
        db.session.add(r);db.session.flush();AuditService.log_action('RECONCILE','ACCOUNT',account.id,f'Reconciliation {r.reconciliation_ref}: book ₹{book}, statement ₹{statement_balance}, difference ₹{difference}',commit=False);db.session.commit();return r

    @staticmethod
    def resolve_reconciliation(record_id,user,note=''):
        r=db.session.get(ReconciliationRecord,record_id)
        if not r or r.status=='RESOLVED':raise ValueError('Reconciliation record not found or already resolved.')
        if r.difference!=ZERO:raise ValueError('A non-zero reconciliation difference must be corrected before resolution.')
        r.status='RESOLVED';r.resolved_by_id=user.id;r.resolved_at=datetime.utcnow();r.notes=(r.notes+'\n' if r.notes else '')+(note.strip() or 'Resolved after review.')
        AuditService.log_action('RESOLVE','RECONCILIATION',r.id,f'Reconciliation {r.reconciliation_ref} resolved.',commit=False);db.session.commit();return r

    @staticmethod
    def check_evidence(entity_type,entity_id,amount=None):
        amount=money(amount) if amount is not None else None;rules=EvidenceRule.query.filter_by(entity_type=entity_type.upper(),is_active=True).all();docs=Document.query.filter_by(entity_type=entity_type.upper(),entity_id=entity_id,is_archived=False).all();categories={d.category.upper() for d in docs};failures=[]
        for rule in rules:
            if rule.min_amount is not None and (amount is None or amount<money(rule.min_amount)):continue
            missing=[c for c in json.loads(rule.required_categories or '[]') if c.upper() not in categories]
            if missing:failures.append({'rule':rule.name,'missing':missing})
        return {'complete':not failures,'failures':failures,'document_count':len(docs)}
