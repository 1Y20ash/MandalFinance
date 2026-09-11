from app.donation_template_fallbacks import DONATION_TEMPLATE_FALLBACKS


def test_donation_template_fallbacks_cover_public_donation_flow():
    assert 'public/donate.html' in DONATION_TEMPLATE_FALLBACKS
    assert 'public/checkout.html' in DONATION_TEMPLATE_FALLBACKS
    assert 'csrf_token()' in DONATION_TEMPLATE_FALLBACKS['public/donate.html']
    assert 'public.confirm_online_payment' in DONATION_TEMPLATE_FALLBACKS['public/checkout.html']
