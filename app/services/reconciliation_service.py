from datetime import datetime
from decimal import Decimal
from sqlalchemy import func
from app.extensions import db
from app.models.controls import ReconciliationRecord
from app.models.reconciliation import ReconciliationLine
from app.models.ledger import Transaction
from app.services.financial_controls_service import money
from app.services.audit_service import AuditService


class ReconciliationService:
    @staticmethod
    def import_lines(reconciliation_id, rows, user):
        record = db.session.get(ReconciliationRecord, reconciliation_id)
        if not record: raise ValueError('Reconciliation record not found.')
        if record.status == 'RESOLVED': raise ValueError('Resolved reconciliations cannot be changed.')
        if not rows: raise ValueError('At least one statement line is required.')
        existing_refs={x.line_ref for x in ReconciliationLine.query.filter_by(reconciliation_id=record.id).all()}
        created=[];seen=set()
        for row in rows:
            line_ref=str(row.get('line_ref') or '').strip()
            if not line_ref or line_ref in seen or line_ref in existing_refs: raise ValueError('Every statement line requires a unique line reference.')
            seen.add(line_ref)
            tx_date=row.get('transaction_date')
            if isinstance(tx_date,str):
                from datetime import date
                tx_date=date.fromisoformat(tx_date)
            amount=money(row.get('amount'))
            if amount<=0: raise ValueError('Statement line amount must be greater than zero.')
            line=ReconciliationLine(reconciliation_id=record.id,line_ref=line_ref,transaction_date=tx_date,description=str(row.get('description') or '').strip() or None,external_ref=str(row.get('external_ref') or '').strip() or None,amount=amount)
            db.session.add(line);created.append(line)
        db.session.flush();AuditService.log_action('IMPORT','RECONCILIATION',record.id,f'Imported {len(created)} statement lines into {record.reconciliation_ref}.',commit=False);db.session.commit();return created

    @staticmethod
    def match_line(line_id,user):
        line=db.session.get(ReconciliationLine,line_id)
        if not line: raise ValueError('Reconciliation line not found.')
        record=line.reconciliation
        if record.status=='RESOLVED': raise ValueError('Resolved reconciliations cannot be changed.')
        query=Transaction.query.filter(Transaction.account_id==record.account_id,Transaction.is_reversed.is_(False),Transaction.amount==money(line.amount))
        if line.external_ref: query=query.filter(Transaction.external_ref==line.external_ref)
        else: query=query.filter(func.date(Transaction.transaction_date)==line.transaction_date)
        candidates=query.all()
        if len(candidates)!=1:
            if not candidates: raise ValueError('No unique ledger transaction matches this statement line.')
            raise ValueError('Multiple ledger transactions match this statement line; provide an external reference.')
        txn=candidates[0]
        if ReconciliationLine.query.filter_by(matched_transaction_id=txn.id).filter(ReconciliationLine.id!=line.id).first(): raise ValueError('This ledger transaction is already matched to another statement line.')
        line.matched_transaction_id=txn.id;line.status='MATCHED';line.match_note='Matched by external reference.' if line.external_ref else 'Matched by account, date and amount.'
        AuditService.log_action('MATCH','RECONCILIATION_LINE',line.id,f'Matched statement line {line.line_ref} to transaction {txn.transaction_ref}.',commit=False);db.session.commit();return line

    @staticmethod
    def finalize(reconciliation_id,user):
        record=db.session.get(ReconciliationRecord,reconciliation_id)
        if not record: raise ValueError('Reconciliation record not found.')
        lines=ReconciliationLine.query.filter_by(reconciliation_id=record.id).all()
        if not lines: raise ValueError('Import statement lines before finalizing reconciliation.')
        unmatched=[line.line_ref for line in lines if line.status=='UNMATCHED']
        if unmatched: raise ValueError('Unmatched statement lines remain: '+', '.join(unmatched[:10]))
        if record.difference!=Decimal('0.00'): raise ValueError('Cannot finalize reconciliation while the balance difference is non-zero.')
        record.status='RESOLVED';record.resolved_by_id=user.id;record.resolved_at=datetime.utcnow();AuditService.log_action('FINALIZE','RECONCILIATION',record.id,f'Reconciliation {record.reconciliation_ref} finalized after matching all statement lines.',commit=False);db.session.commit();return record
