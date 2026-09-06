from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from uuid import uuid4

from app.extensions import db
from app.models.income import Donation
from app.models.ledger import TransactionCategory
from app.services.audit_service import AuditService
from app.services.ledger_service import LedgerService


class DonationService:
    """Business logic for donations and their central-ledger postings."""

    OFFLINE_MODES = {'CASH', 'UPI', 'BANK_TRANSFER', 'CHEQUE'}

    @staticmethod
    def _generate_donation_number():
        return f"DON-{datetime.utcnow().year}-{uuid4().hex[:10].upper()}"

    @staticmethod
    def _generate_receipt_number():
        return f"REC-{datetime.utcnow().year}-{uuid4().hex[:10].upper()}"

    @staticmethod
    def _normalize_amount(amount):
        try:
            value = Decimal(str(amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        except (InvalidOperation, ValueError, TypeError):
            raise ValueError('Donation amount must be a valid number.')
        if value <= Decimal('0.00'):
            raise ValueError('Donation amount must be greater than zero.')
        return value

    @staticmethod
    def _validate_common(event_id, donor_name, payment_mode):
        if not event_id:
            raise ValueError('A target event is required.')
        if not donor_name or len(donor_name.strip()) < 2:
            raise ValueError('Donor name must contain at least 2 characters.')
        if payment_mode not in DonationService.OFFLINE_MODES:
            raise ValueError('Invalid offline donation payment mode.')

    @staticmethod
    def _donation_category_id():
        category = TransactionCategory.query.filter_by(name='Donations', category_type='income').first()
        if not category:
            category = TransactionCategory(name='Donations', category_type='income', description='Donation income')
            db.session.add(category)
            db.session.flush()
        return category.id

    @staticmethod
    def record_offline_donation(event_id, donor_name, amount, payment_mode, account_id, created_by_id,
                                donor_phone=None, donor_email=None, donor_address=None, pan_number=None,
                                purpose='General Donation', transaction_ref=None, notes=None):
        DonationService._validate_common(event_id, donor_name, payment_mode)
        decimal_amount = DonationService._normalize_amount(amount)
        if payment_mode in {'UPI', 'BANK_TRANSFER', 'CHEQUE'} and not transaction_ref:
            raise ValueError('Transaction reference is required for this payment mode.')

        donation = Donation(
            donation_number=DonationService._generate_donation_number(), event_id=event_id,
            donor_name=donor_name.strip(), donor_phone=donor_phone or None, donor_email=donor_email or None,
            donor_address=donor_address or None, pan_number=pan_number or None, amount=decimal_amount,
            purpose=(purpose or 'General Donation').strip(), donation_type='OFFLINE', payment_mode=payment_mode,
            status='SUCCESS', transaction_ref=transaction_ref or None,
            receipt_number=DonationService._generate_receipt_number(), receipt_generated_at=datetime.utcnow(),
            notes=notes or None, created_by_id=created_by_id,
        )
        try:
            db.session.add(donation)
            db.session.flush()
            LedgerService.record_income(
                account_id=account_id, amount=decimal_amount,
                description=f"Donation {donation.donation_number} ({donation.receipt_number}) from {donation.donor_name}",
                source_module='DONATION', source_id=donation.id, created_by_id=created_by_id,
                payment_mode=payment_mode, external_ref=transaction_ref, category_id=DonationService._donation_category_id(),
                event_id=event_id, commit=False,
            )
            AuditService.log_action(action='CREATE', entity_type='DONATION', entity_id=donation.id,
                                    description=f"Recorded offline donation {donation.donation_number} of ₹{decimal_amount} for {donation.donor_name}",
                                    commit=False)
            db.session.commit()
            return donation
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def confirm_online_donation(donation_id, gateway_payment_id, gateway_signature, account_id):
        donation = db.session.get(Donation, donation_id)
        if not donation:
            raise ValueError('Donation not found.')
        if donation.status == 'SUCCESS':
            return donation
        if donation.status in {'FAILED', 'CANCELLED'}:
            raise ValueError('A failed or cancelled donation cannot be confirmed.')
        if not gateway_payment_id or not gateway_signature:
            raise ValueError('Gateway payment ID and signature are required.')
        try:
            donation.status = 'SUCCESS'
            donation.gateway_payment_id = gateway_payment_id
            donation.gateway_signature = gateway_signature
            donation.receipt_number = DonationService._generate_receipt_number()
            donation.receipt_generated_at = datetime.utcnow()
            db.session.flush()
            LedgerService.record_income(
                account_id=account_id, amount=donation.amount,
                description=f"Online Donation {donation.donation_number} ({donation.receipt_number}) from {donation.donor_name}",
                source_module='DONATION', source_id=donation.id, created_by_id=donation.created_by_id,
                payment_mode='GATEWAY', external_ref=gateway_payment_id,
                category_id=DonationService._donation_category_id(), event_id=donation.event_id, commit=False,
            )
            AuditService.log_action(action='VERIFY', entity_type='DONATION', entity_id=donation.id,
                                    description=f"Confirmed online donation {donation.donation_number} of ₹{donation.amount}",
                                    commit=False)
            db.session.commit()
            return donation
        except Exception:
            db.session.rollback()
            raise
