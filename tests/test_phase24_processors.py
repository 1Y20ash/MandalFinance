from pathlib import Path


def test_processor_register_exists_and_covers_active_infrastructure():
    register = Path('docs/THIRD_PARTY_PROCESSOR_REGISTER.md').read_text(encoding='utf-8')
    for provider in ('Supabase', 'Razorpay', 'Vercel', 'Managed Redis provider'):
        assert provider in register
    assert 'Minimum-data-sharing rules' in register
    assert 'Operational processor controls' in register


def test_processor_register_records_disabled_processor_categories():
    register = Path('docs/THIRD_PARTY_PROCESSOR_REGISTER.md').read_text(encoding='utf-8')
    assert 'Email delivery provider' in register
    assert 'Analytics platform' in register
    assert 'Advertising/tracking platform' in register
    assert 'must not be introduced without updating this register first' in register


def test_environment_example_records_non_secret_redis_processor_identity():
    env_example = Path('.env.example').read_text(encoding='utf-8')
    assert 'REDIS_PROVIDER_NAME=' in env_example
    assert 'RATELIMIT_STORAGE_URI=' in env_example
    assert 'REDIS_PROVIDER_NAME' in Path('app/config.py').read_text(encoding='utf-8')


def test_razorpay_order_payload_minimizes_server_to_gateway_data():
    source = Path('app/services/payment_gateway.py').read_text(encoding='utf-8')
    assert "'notes': {'donor_name': donor_name[:120]}" in source
    assert 'donor_email' not in source
    assert 'donor_phone' not in source
    assert 'password' not in source.lower()
    assert 'csrf_token' not in source.lower()


def test_supabase_storage_uses_server_side_service_role_only():
    source = Path('app/utils/storage_driver.py').read_text(encoding='utf-8')
    assert 'SUPABASE_SERVICE_ROLE_KEY' in source
    assert "Authorization': f'Bearer {supabase_key}'" in source
    assert 'SUPABASE_SERVICE_ROLE_KEY' not in Path('app/templates/base.html').read_text(encoding='utf-8')


def test_vercel_deployment_is_documented_as_hosting_processor():
    vercel_config = Path('vercel.json').read_text(encoding='utf-8')
    register = Path('docs/THIRD_PARTY_PROCESSOR_REGISTER.md').read_text(encoding='utf-8')
    assert 'server.py' in vercel_config
    assert '**Vercel**' in register
