"""Deterministic donation-page Jinja fallbacks for Vercel Python bundles.

The normal FileSystemLoader remains the primary source. These two templates are
used only when Vercel's Python bundler omits dynamically selected public donation
pages from the serverless function bundle.
"""

DONATION_TEMPLATE_FALLBACKS = {
    "public/donate.html": r'''{% extends "base.html" %}
{% block title %}Online Donation - Shree Ashtavinayak Ganesh Utsav Mandal{% endblock %}
{% block content %}
<div class="online-donation-page">
    <div class="online-donation-shell">
        <div class="online-donation-header">
            <span class="online-donation-kicker">Support the Mandal</span>
            <div class="d-flex align-items-center justify-content-between gap-3">
                <div><h1 class="h3 mb-1">Online Donation Portal</h1><p class="mb-0 text-white-50">Ganesh Utsav {{ active_event.year if active_event else '2026' }}</p></div>
                <span class="online-donation-icon" aria-hidden="true"><i class="fa-solid fa-om"></i></span>
            </div>
        </div>
        <div class="p-4 p-lg-5">
            <form method="POST">
                <input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
                <div class="mb-4">
                    <label class="form-label fw-bold" for="amount">Donation Amount (₹)</label>
                    <div class="online-donation-presets" role="group" aria-label="Preset donation amounts">
                        <button type="button" class="btn btn-outline-success" onclick="setAmt(501)">₹501</button>
                        <button type="button" class="btn btn-outline-success" onclick="setAmt(1001)">₹1,001</button>
                        <button type="button" class="btn btn-outline-success" onclick="setAmt(2501)">₹2,501</button>
                        <button type="button" class="btn btn-outline-success" onclick="setAmt(5001)">₹5,001</button>
                    </div>
                    <div class="input-group mt-2"><span class="input-group-text fw-bold">₹</span><input type="number" step="0.01" min="0.01" id="amount" name="amount" class="form-control form-control-lg fw-bold" placeholder="Enter amount in INR" required></div>
                </div>
                <div class="mb-3"><label class="form-label fw-bold" for="donor_name">Donor Full Name</label><input id="donor_name" type="text" name="donor_name" class="form-control" minlength="2" maxlength="120" placeholder="Your Name" required></div>
                <div class="row g-3 mb-3">
                    <div class="col-md-6"><label class="form-label" for="donor_phone">Phone Number</label><input id="donor_phone" type="tel" name="donor_phone" class="form-control" maxlength="20" placeholder="For receipt/contact"></div>
                    <div class="col-md-6"><label class="form-label" for="donor_email">Email Address</label><input id="donor_email" type="email" name="donor_email" class="form-control" maxlength="120" placeholder="name@example.com"></div>
                </div>
                <div class="mb-4"><label class="form-label" for="purpose">Donation Purpose</label><select id="purpose" name="purpose" class="form-select"><option value="General Utsav Donation">General Utsav Donation</option><option value="Prasad & Mahaprasad">Prasad & Mahaprasad</option><option value="Cultural Program">Cultural Program</option><option value="Mandal Decoration">Mandal Decoration</option></select></div>
                <div class="online-donation-security mb-4"><i class="fa-solid fa-shield-halved" aria-hidden="true"></i><div><strong>Verified payment flow</strong><p class="mb-0">The gateway response is verified on the server before a receipt and ledger entry are created.</p></div></div>
                <button type="submit" class="btn btn-success btn-lg w-100 py-3 fw-bold"><i class="fa-solid fa-lock me-2"></i>Proceed to Secure Payment</button>
            </form>
        </div>
    </div>
</div>
{% endblock %}
{% block extra_js %}<script>function setAmt(val) { document.getElementById('amount').value = val; }</script>{% endblock %}
''',
    "public/checkout.html": r'''{% extends "base.html" %}
{% block title %}Secure Payment - Ashtavinayak Mandal{% endblock %}
{% block content %}
<div class="payment-page"><div class="payment-shell">
    <div class="payment-header"><div><span class="payment-kicker">Secure donation checkout</span><h1 class="h3 mb-1">Complete your donation</h1><p class="mb-0 text-white-50">Your payment is verified on the server before the donation enters the ledger.</p></div><span class="payment-header-icon" aria-hidden="true"><i class="fa-solid fa-shield-halved"></i></span></div>
    <div class="payment-summary"><div><span>Donation</span><strong>{{ donation.donation_number }}</strong></div><div><span>Donor</span><strong>{{ donation.donor_name }}</strong></div><div><span>Purpose</span><strong>{{ donation.purpose }}</strong></div><div class="payment-total"><span>Amount</span><strong>₹{{ donation.amount }}</strong></div></div>
    {% if order_info.key_id != 'mock_key_id' %}<div class="payment-action"><button id="rzp-pay-button" type="button" class="btn btn-success btn-lg w-100 py-3 fw-bold"><i class="fa-solid fa-lock me-2"></i>Pay ₹{{ donation.amount }} securely</button><p id="payment-status" class="small text-muted text-center mt-3 mb-0">You will be redirected to the secure Razorpay checkout.</p></div>
    {% else %}<div class="payment-action"><div class="alert alert-warning small mb-3"><i class="fa-solid fa-flask me-1"></i>Development/test gateway is active. No real money will be charged.</div><form method="POST" action="{{ url_for('public.confirm_online_payment') }}"><input type="hidden" name="csrf_token" value="{{ csrf_token() }}"><input type="hidden" name="donation_id" value="{{ donation.id }}"><input type="hidden" name="gateway_order_id" value="{{ order_info.order_id }}"><input type="hidden" name="gateway_payment_id" value="{{ order_info.mock_payment_id }}"><input type="hidden" name="gateway_signature" value="{{ order_info.mock_signature }}"><button type="submit" class="btn btn-success btn-lg w-100 py-3 fw-bold"><i class="fa-solid fa-vial me-2"></i>Simulate successful payment</button></form></div>{% endif %}
    <div class="payment-trust-row"><span><i class="fa-solid fa-lock"></i> Server-side verification</span><span><i class="fa-solid fa-receipt"></i> Receipt after verification</span><span><i class="fa-solid fa-book"></i> Ledger posting after success</span></div>
</div></div>
{% endblock %}
{% block extra_js %}{% if order_info.key_id != 'mock_key_id' %}<script src="https://checkout.razorpay.com/v1/checkout.js"></script><script>
(() => { const button=document.getElementById('rzp-pay-button'); const status=document.getElementById('payment-status'); const csrfToken={{ csrf_token()|tojson }}; const options={key:{{ order_info.key_id|tojson }},amount:{{ order_info.amount_in_paise|tojson }},currency:{{ order_info.currency|tojson }},name:'Shree Ashtavinayak Ganesh Utsav Mandal',description:{{ donation.purpose|tojson }},order_id:{{ order_info.order_id|tojson }},prefill:{name:{{ donation.donor_name|tojson }},email:{{ donation.donor_email|tojson }},contact:{{ donation.donor_phone|tojson }}},theme:{color:'#d97706'},handler:async function(response){status.textContent='Verifying payment securely…';button.disabled=true;const form=document.createElement('form');form.method='POST';form.action={{ url_for('public.confirm_online_payment')|tojson }};const fields={csrf_token:csrfToken,donation_id:{{ donation.id|tojson }},gateway_order_id:response.razorpay_order_id,gateway_payment_id:response.razorpay_payment_id,gateway_signature:response.razorpay_signature};Object.entries(fields).forEach(([name,value])=>{const input=document.createElement('input');input.type='hidden';input.name=name;input.value=value||'';form.appendChild(input)});document.body.appendChild(form);form.submit()},modal:{ondismiss:function(){status.textContent='Payment window closed. Your donation remains pending.';button.disabled=false}}};button.addEventListener('click',()=>new Razorpay(options).open())})();
</script>{% endif %}{% endblock %}
'''
}
