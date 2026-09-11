from app.extensions import db
from app.models.income import Donation


class FakeGateway:
    def create_order(self, amount_decimal, donation_id, donor_name):
        return {
            'order_id': f'order_test_{donation_id}',
            'amount_in_paise': int(amount_decimal * 100),
            'currency': 'INR',
            'status': 'created',
            'key_id': 'rzp_test_key',
        }


def test_public_online_donation_creates_gateway_order(app, client, monkeypatch):
    monkeypatch.setattr(
        'app.routes.public.get_payment_gateway',
        lambda: FakeGateway(),
    )

    response = client.post(
        '/donate',
        data={
            'donor_name': 'Online Test Donor',
            'donor_phone': '9876543210',
            'donor_email': 'donor@example.com',
            'amount': '501.00',
            'purpose': 'General Utsav Donation',
        },
    )

    assert response.status_code == 200
    assert b'Complete your donation' in response.data

    donation = Donation.query.filter_by(donor_name='Online Test Donor').one()
    assert donation.status == 'PENDING'
    assert donation.donation_type == 'ONLINE'
    assert donation.payment_mode == 'ONLINE_GATEWAY'
    assert donation.gateway_order_id == f'order_test_{donation.id}'
    assert donation.amount == '501.00' or str(donation.amount) == '501.00'

    db.session.rollback()
