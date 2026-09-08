from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from sqlalchemy import func

from app.extensions import db
from app.models.contribution import SponsorshipPayment, MemberContributionPayment
from app.models.income import Sponsorship, MemberContribution
from app.models.ledger import Account
from app.models.mandal import Event
from app.services.audit_service import AuditService
from app.services.ledger_service import LedgerService


ZERO = Decimal('0.00')


class ContributionService:
    PAYMENT_MODES = {'CASH', 'UPI', 'BANK_TRANSFER', 'CHEQUE', 'GATEWAY'}

    @staticmethod
    def money(value, positive=False):
        try:
            amount = Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        except (InvalidOperation, ValueError, TypeError):
            raise ValueError('Amount must be a valid monetary value.')
        if positive and amount <= ZERO:
            raise ValueError('Amount must be greater than zero.')
        if not positive and amount < ZERO:
            raise ValueError('Amount cannot be negative.')
        return amount

    @staticmethod
    def _event(event_id):
        event = db.session.get(Event, event_id)
        if not event:
            raise ValueError('Event not found.')
        event.assert_editable()
        return event

    @staticmethod
    def _account(account_id):
        account = db.session.get(Account, account_id)
        if not account or not account.is_active:
            raise ValueError('A valid active account is required.')
        return account

    @staticmethod
    def _mode(mode):
        mode = (mode or '').strip().upper()
        if mode not in ContributionService.PAYMENT_MODES:
            raise ValueError('Invalid payment mode.')
        return mode

    @staticmethod
    def _payment_amount(amount, outstanding):
        value = ContributionService.money(amount, positive=True)
        if value > outstanding:
            raise ValueError('Payment cannot exceed the outstanding commitment/target.')
        return value

    @staticmethod
    def create_sponsorship(event_id, sponsor_name, sponsorship_type, committed_amount,
                           created_by_id, contact_person=None, contact_phone=None,
                           contact_email=None, notes=None):
        event = ContributionService._event(event_id)
        sponsor_name = (sponsor_name or '').strip()
        sponsorship_type = (sponsorship_type or '').strip()
        if not sponsor_name or not sponsorship_type:
            raise ValueError('Sponsor name and sponsorship type are required.')
        amount = ContributionService.money(committed_amount, positive=True)
        sponsorship = Sponsorship(
            sponsorship_ref=f'SP-{event.id}-{event.created_at.strftime("%Y%m%d")}-{db.session.query(Sponsorship).count()+1:04d}',
            event_id=event.id, sponsor_name=sponsor_name, sponsorship_type=sponsorship_type,
            committed_amount=amount, pending_amount=amount, created_by_id=created_by_id,
            contact_person=(contact_person or '').strip() or None,
            contact_phone=(contact_phone or '').strip() or None,
            contact_email=(contact_email or '').strip() or None,
            notes=(notes or '').strip() or None,
        )
        db.session.add(sponsorship)
        db.session.flush()
        AuditService.log_action('CREATE', 'SPONSORSHIP', sponsorship.id,
                                f'Created sponsorship {sponsorship.sponsorship_ref} for {sponsor_name}.', commit=False)
        db.session.commit()
        return sponsorship

    @staticmethod
    def create_member_contribution(event_id, member_name, target_amount, created_by_id,
                                   member_phone=None, designation=None, notes=None):
        event = ContributionService._event(event_id)
        member_name = (member_name or '').strip()
        if not member_name:
            raise ValueError('Member name is required.')
        target = ContributionService.money(target_amount, positive=True)
        contribution = MemberContribution(
            event_id=event.id, member_name=member_name, target_amount=target,
            pending_amount=target, created_by_id=created_by_id,
            member_phone=(member_phone or '').strip() or None,
            designation=(designation or '').strip() or None,
            notes=(notes or '').strip() or None,
        )
        db.session.add(contribution)
        db.session.flush()
        AuditService.log_action('CREATE', 'MEMBER_CONTRIBUTION', contribution.id,
                                f'Created member contribution target for {member_name}.', commit=False)
        db.session.commit()
        return contribution

    @staticmethod
    def record_sponsorship_payment(sponsorship_id, account_id, amount, payment_mode,
                                   transaction_ref, created_by_id, notes=None):
        sponsorship = db.session.get(Sponsorship, sponsorship_id)
        if not sponsorship:
            raise ValueError('Sponsorship not found.')
        event = ContributionService._event(sponsorship.event_id)
        account = ContributionService._account(account_id)
        mode = ContributionService._mode(payment_mode)
        ref = (transaction_ref or '').strip() or None
        outstanding = ContributionService.money(sponsorship.committed_amount) - ContributionService.money(sponsorship.received_amount)
        value = ContributionService._payment_amount(amount, outstanding)
        if ref and SponsorshipPayment.query.filter_by(transaction_ref=ref).first():
            raise ValueError('This transaction reference has already been used for a sponsorship payment.')
        try:
            payment = SponsorshipPayment(
                sponsorship_id=sponsorship.id, amount=value, payment_mode=mode,
                transaction_ref=ref, account_id=account.id, created_by_id=created_by_id,
                notes=(notes or '').strip() or None,
            )
            db.session.add(payment)
            db.session.flush()
            ledger = LedgerService.record_income(
                account_id=account.id, amount=value,
                description=f'Sponsorship payment {sponsorship.sponsorship_ref}',
                source_module='SPONSORSHIP_PAYMENT', source_id=payment.id,
                created_by_id=created_by_id, payment_mode=mode, external_ref=ref,
                event_id=event.id, commit=False,
            )
            payment.ledger_transaction_id = ledger.id
            sponsorship.received_amount = ContributionService.money(sponsorship.received_amount) + value
            sponsorship.pending_amount = ContributionService.money(sponsorship.committed_amount) - sponsorship.received_amount
            sponsorship.status = 'RECEIVED' if sponsorship.pending_amount == ZERO else 'PARTIAL'
            AuditService.log_action('PAY', 'SPONSORSHIP', sponsorship.id,
                                    f'Recorded sponsorship payment of ₹{value} ({ledger.transaction_ref}).', commit=False)
            db.session.commit()
            return payment
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def record_member_payment(contribution_id, account_id, amount, payment_mode,
                              transaction_ref, created_by_id, notes=None):
        contribution = db.session.get(MemberContribution, contribution_id)
        if not contribution:
            raise ValueError('Member contribution not found.')
        event = ContributionService._event(contribution.event_id)
        account = ContributionService._account(account_id)
        mode = ContributionService._mode(payment_mode)
        ref = (transaction_ref or '').strip() or None
        outstanding = ContributionService.money(contribution.target_amount) - ContributionService.money(contribution.received_amount)
        value = ContributionService._payment_amount(amount, outstanding)
        if ref and MemberContributionPayment.query.filter_by(transaction_ref=ref).first():
            raise ValueError('This transaction reference has already been used for a member contribution payment.')
        try:
            payment = MemberContributionPayment(
                contribution_id=contribution.id, amount=value, payment_mode=mode,
                transaction_ref=ref, account_id=account.id, created_by_id=created_by_id,
                notes=(notes or '').strip() or None,
            )
            db.session.add(payment)
            db.session.flush()
            ledger = LedgerService.record_income(
                account_id=account.id, amount=value,
                description=f'Member contribution payment for {contribution.member_name}',
                source_module='MEMBER_CONTRIBUTION_PAYMENT', source_id=payment.id,
                created_by_id=created_by_id, payment_mode=mode, external_ref=ref,
                event_id=event.id, commit=False,
            )
            payment.ledger_transaction_id = ledger.id
            contribution.received_amount = ContributionService.money(contribution.received_amount) + value
            contribution.pending_amount = ContributionService.money(contribution.target_amount) - contribution.received_amount
            contribution.status = 'RECEIVED' if contribution.pending_amount == ZERO else 'PARTIAL'
            contribution.payment_mode = mode
            contribution.transaction_ref = ref
            AuditService.log_action('PAY', 'MEMBER_CONTRIBUTION', contribution.id,
                                    f'Recorded member contribution payment of ₹{value} ({ledger.transaction_ref}).', commit=False)
            db.session.commit()
            return payment
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def sponsorship_summary(event_id):
        query = Sponsorship.query.filter_by(event_id=event_id)
        return {
            'count': query.count(),
            'committed': sum((ContributionService.money(x.committed_amount) for x in query.all()), ZERO),
            'received': sum((ContributionService.money(x.received_amount) for x in query.all()), ZERO),
            'pending': sum((ContributionService.money(x.pending_amount) for x in query.all()), ZERO),
        }

    @staticmethod
    def member_summary(event_id):
        query = MemberContribution.query.filter_by(event_id=event_id)
        return {
            'count': query.count(),
            'target': sum((ContributionService.money(x.target_amount) for x in query.all()), ZERO),
            'received': sum((ContributionService.money(x.received_amount) for x in query.all()), ZERO),
            'pending': sum((ContributionService.money(x.pending_amount) for x in query.all()), ZERO),
        }
