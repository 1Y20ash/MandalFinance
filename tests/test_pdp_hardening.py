from datetime import date
from decimal import Decimal
import json
import pytest

from app.extensions import db
from app.models.auth import User, Permission, Role
from app.models.mandal import Event
from app.models.ledger import Account, Transaction
from app.models.income import Donation, Sponsorship, MemberContribution
from app.models.controls import EvidenceRule, ReconciliationRecord
from app.models.reconciliation import ReconciliationLine
from app.models.budget import Budget
from app.services.financial_controls_service import FinancialControlsService
from app.services.reconciliation_service import ReconciliationService


def _admin():
    return User.query.filter_by(username='admin').first()


def test_finance_control_routes_require_dedicated_view_permission(client, app):
    with app.app_context():
        user = User.query.filter_by(username='volunteer').first()
        user.roles = []
        db.session.commit()
    client.post('/auth/login', data={'username': 'volunteer', 'password': 'password'})
    response = client.get('/finance-controls/reconciliations')
    assert response.status_code == 403


def test_finance_manage_permission_is_distinct_from_create_permission(app):
    with app.app_context():
        permission = Permission.query.filter_by(name='finance.manage').first()
        assert permission is not None
        user = User.query.filter_by(username='volunteer').first()
        assert not user.is_admin
        assert not user.has_permission('finance.manage')


def test_duplicate_external_reference_is_rejected(app):
    with app.app_context():
        admin = _admin(); event = Event.query.first(); account = Account.query.first()
        tx = Transaction(transaction_ref='DUP-REF-TX', event_id=event.id, account_id=account.id,
                         transaction_type='INCOME', amount=Decimal('100.00'), payment_mode='UPI',
                         external_ref='DUP-EXT-1', description='duplicate test', source_module='TEST',
                         source_id=9001, created_by_id=admin.id)
        db.session.add(tx); db.session.commit()
        with pytest.raises(ValueError, match='already recorded'):
            FinancialControlsService.create_contribution_receipt('MEMBER',
                _member(app).id, account.id, '10.00', 'UPI', admin, 'DUP-EXT-1')


def _member(app):
    event = Event.query.first(); admin = _admin()
    member = MemberContribution(event_id=event.id, member_name='Integrity Member',
                                 target_amount=Decimal('500.00'), received_amount=Decimal('0.00'),
                                 pending_amount=Decimal('500.00'), status='PENDING', created_by_id=admin.id)
    db.session.add(member); db.session.commit()
    return member


def test_contribution_cannot_over_collect(app):
    with app.app_context():
        admin = _admin(); account = Account.query.first(); member = _member(app)
        with pytest.raises(ValueError, match='exceeds the member contribution target'):
            FinancialControlsService.create_contribution_receipt('MEMBER', member.id, account.id, '600.00', 'CASH', admin)


def test_reconciliation_rejects_duplicate_statement_date(app):
    with app.app_context():
        admin = _admin(); account = Account.query.first()
        FinancialControlsService.reconcile_account(account.id, date(2026, 9, 7), '1000.00', admin)
        with pytest.raises(ValueError, match='already exists'):
            FinancialControlsService.reconcile_account(account.id, date(2026, 9, 7), '1000.00', admin)


def test_reconciliation_lines_require_unique_match(app):
    with app.app_context():
        admin = _admin(); account = Account.query.first(); event = Event.query.first()
        tx = Transaction(transaction_ref='MATCH-TX-1', event_id=event.id, account_id=account.id,
                         transaction_type='INCOME', amount=Decimal('250.00'), payment_mode='BANK_TRANSFER',
                         external_ref='BANK-250-1', description='bank match', source_module='TEST',
                         source_id=9010, created_by_id=admin.id)
        db.session.add(tx); db.session.commit()
        rec = FinancialControlsService.reconcile_account(account.id, date(2026, 9, 8), '250.00', admin,
                                                         event.id, date(2026, 9, 8), date(2026, 9, 8))
        ReconciliationService.import_lines(rec.id, [{'line_ref':'L1','transaction_date':'2026-09-08','amount':'250.00','external_ref':'BANK-250-1'}], admin)
        line = ReconciliationLine.query.one()
        ReconciliationService.match_line(line.id, admin)
        assert line.status == 'MATCHED' and line.matched_transaction_id == tx.id


def test_reconciliation_cannot_finalize_with_unmatched_lines(app):
    with app.app_context():
        admin = _admin(); account = Account.query.first()
        rec = FinancialControlsService.reconcile_account(account.id, date(2026, 9, 9), '100.00', admin)
        ReconciliationService.import_lines(rec.id, [{'line_ref':'UNMATCHED','transaction_date':'2026-09-09','amount':'100.00','external_ref':'NO-SUCH-TX'}], admin)
        with pytest.raises(ValueError, match='Unmatched statement lines remain'):
            ReconciliationService.finalize(rec.id, admin)


def test_donation_payment_is_blocked_when_evidence_rule_is_active(app):
    with app.app_context():
        admin = _admin(); event = Event.query.first(); account = Account.query.first()
        rule = EvidenceRule(name='Donation proof hardening', entity_type='DONATION', min_amount=Decimal('1.00'),
                             required_categories=json.dumps(['RECEIPT']), created_by_id=admin.id)
        db.session.add(rule); db.session.commit()
        from app.services.donation_service import DonationService
        with pytest.raises(ValueError, match='Required evidence'):
            DonationService.record_offline_donation(event.id, 'Evidence Donor', '100.00', 'CASH', account.id, admin.id)
        assert Donation.query.filter_by(donor_name='Evidence Donor').count() == 0


def test_budget_cannot_be_self_approved(app):
    with app.app_context():
        admin = _admin(); event = Event.query.first()
        budget = Budget(event_id=event.id, total_income_target=Decimal('1000.00'), total_expense_limit=Decimal('500.00'), created_by_id=admin.id)
        db.session.add(budget); db.session.commit()
        assert budget.created_by_id == admin.id and budget.approved_by_id is None


def test_login_rejects_external_next_url(client):
    response = client.get('/auth/login?next=https://evil.example', follow_redirects=False)
    assert response.status_code == 200


def test_login_rejects_protocol_relative_next_url(client):
    response = client.get('/auth/login?next=//evil.example', follow_redirects=False)
    assert response.status_code == 200


def test_donation_gateway_order_id_is_unique(app):
    with app.app_context():
        event = Event.query.first()
        first = Donation(donation_number='UNIQ-ORDER-1', event_id=event.id, donor_name='First Donor', amount=Decimal('10.00'),
                         purpose='Test', donation_type='ONLINE', payment_mode='ONLINE_GATEWAY', status='PENDING', gateway_order_id='order_unique')
        second = Donation(donation_number='UNIQ-ORDER-2', event_id=event.id, donor_name='Second Donor', amount=Decimal('20.00'),
                          purpose='Test', donation_type='ONLINE', payment_mode='ONLINE_GATEWAY', status='PENDING', gateway_order_id='order_unique')
        db.session.add(first); db.session.commit()
        db.session.add(second)
        with pytest.raises(Exception):
            db.session.commit()
        db.session.rollback()


def test_production_error_handler_is_generic(app):
    with app.test_request_context('/missing'):
        response = app.handle_http_exception(__import__('werkzeug').exceptions.NotFound())
        assert response.status_code == 404
        assert b'No such' not in response.get_data()
