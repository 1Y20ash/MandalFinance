
def test_supabase_storage_uses_server_side_service_role_only():
    source = Path('app/utils/storage_driver.py').read_text(encoding='utf-8')
    assert 'SUPABASE_SERVICE_ROLE_KEY' in source
    assert "Authorization': f'Bearer {supabase_key}'" in source
    assert 'SUPABASE_SERVICE_ROLE_KEY' not in Path('app/templates/base.html').read_text(encoding='utf-8')


def test_vercel_deployment_is_documented_as_hosting_processor():
    vercel_config = Path('vercel.json').read_text(encoding='utf-8')
    register = Path('docs/THIRD_PARTY_PROCESSOR_REGISTER.md').read_text(encoding='utf-8')
    # Vercel's canonical application entrypoint is app.server:app in pyproject.toml.
    # server.py remains the documented application boundary, so this test verifies
    # the actual deployment configuration rather than requiring an obsolete string
    # in vercel.json. The recursive include bundles the complete Jinja template tree
    # and is attached to the actual Flask serverless entrypoint.
    pyproject = Path('pyproject.toml').read_text(encoding='utf-8')
    assert 'entrypoint = "app.server:app"' in pyproject
    assert '"app/server.py"' in vercel_config
    assert 'includeFiles' in vercel_config
    assert 'app/templates/**/*.html' in vercel_config
    assert '**Vercel**' in register
