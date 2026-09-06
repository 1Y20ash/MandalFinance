import datetime
from decimal import Decimal
from app.extensions import db
from app.models.income import Donation
from app.models.ledger import Account, TransactionCategory
from app.models.mandal import Event
from app.services.ledger_service import LedgerService
from app.services.audit_service import AuditService

class DonationService:
    @staticmethod
    def _generate_donation_number():
        year = datetime.datetime.utcnow().year
        count = Donation.query.count() + 1
        return f"DON-{year}-{count:04d}"

    @staticmethod
    def _generate_receipt_number():
        year = datetime.datetime.utcnow().year
        count = Donation.query.filter(Donation.receipt_number != None).count() + 1
        return f"REC-{year}-{count:04d}"

    @staticmethod
    def record_offline_donation(event_id, donor_name, amount, payment_mode, account_id, created_by_id,
                                donor_phone=None, donor_email=None, donor_address=None, pan_number=None,
                                purpose='General Donation', transaction_ref=None, notes=None):
        """
        Records an offline donation, updates central ledger, generates official receipt number.
        """
        decimal_amount = Decimal(str(amount))
        if decimal_amount <= Decimal('0.00'):
            raise ValueError("Donation amount must be greater than zero.")

        donation_num = DonationService._generate_donation_number()
        receipt_num = DonationService._generate_receipt_number()

        donation = Donation(
            donation_number=donation_num,
            event_id=event_id,
            donor_name=donor_name,
            donor_phone=donor_phone,
            donor_email=donor_email,
            donor_address=donor_address,
            pan_number=pan_number,
            amount=decimal_amount,
            purpose=purpose,
            donation_type='OFFLINE',
            payment_mode=payment_mode,
            status='SUCCESS',
            transaction_ref=transaction_ref,
            receipt_number=receipt_num,
            receipt_generated_at=datetime.datetime.utcnow(),
            notes=notes,
            created_by_id=created_by_id
        )

        db.session.add(donation)
        db.session.commit()

        # Link to Central Ledger
        cat = TransactionCategory.query.filter_by(name='Donations', category_type='income').first()
        cat_id = cat.id if cat else None

        LedgerService.record_income(
            account_id=account_id,
            amount=decimal_amount,
            description=f"Donation {donation_num} ({receipt_num}) from {donor_name}",
            source_module='DONATION',
            source_id=donation.id,
            created_by_id=created_by_id,
            payment_mode=payment_mode,
            external_ref=transaction_ref,
            category_id=cat_id,
            event_id=event_id
        )

        AuditService.log_action(
            action='CREATE',
            entity_type='DONATION',
            entity_id=donation.id,
            description=f"Recorded offline donation {donation_num} of ₹{decimal_amount} for {donor_name}"
        )

        return donation

    @staticmethod
    def confirm_online_donation(donation_id, gateway_payment_id, gateway_signature, account_id):
        """
        Confirms online donation upon payment gateway verification, generates receipt, and posts to Ledger.
        """
        donation = Donation.query.get(donation_id)
        if not donation:
            raise ValueError("Donation not found.")

        if donation.status == 'SUCCESS':
            return donation  # Prevent duplicate confirmation

        receipt_num = DonationService._generate_receipt_number()

        donation.status = 'SUCCESS'
        donation.gateway_payment_id = gateway_payment_id
        donation.gateway_signature = gateway_signature
        donation.receipt_number = receipt_num
        donation.receipt_generated_at = datetime.datetime.utcnow()

        db.session.commit()

        # Post to central ledger
        cat = TransactionCategory.query.filter_by(name='Donations', category_type='income').first()
        cat_id = cat.id if cat else None

        LedgerService.record_income(
            account_id=account_id,
            amount=donation.amount,
            description=f"Online Donation {donation.donation_number} ({receipt_num}) from {donation.donor_name}",
            source_module='DONATION',
            source_id=donation.id,
            created_by_id=donation.created_by_id or 1,
            payment_mode='ONLINE_GATEWAY',
            external_ref=gateway_payment_id,
            category_id=cat_id,
            event_id=donation.event_id
        )

        AuditService.log_action(
            action='VERIFY',
            entity_type='DONATION',
            entity_id=donation.id,
            description=f"Confirmed online donation {donation.donation_number} of ₹{donation.amount}"
        )

        return donation
