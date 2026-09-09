from unittest.mock import patch


def test_liveness_probe_is_process_only(client):
    response = client.get('/health/live')
    assert response.status_code == 200
    assert response.get_json() == {'status': 'OK'}


def test_readiness_probe_reports_database_health(client):
    response = client.get('/health/ready')
    assert response.status_code == 200
    assert response.get_json() == {'status': 'READY', 'database': 'HEALTHY'}


def test_readiness_probe_fails_closed_on_database_error(client):
    with patch('app.routes.main.db.session.execute', side_effect=RuntimeError('secret connection detail')):
        response = client.get('/health/ready')
    assert response.status_code == 503
    payload = response.get_json()
    assert payload == {'status': 'UNHEALTHY', 'database': 'UNHEALTHY'}
    assert 'secret connection detail' not in response.get_data(as_text=True)


def test_legacy_health_endpoint_hides_database_exception(client):
    with patch('app.routes.main.db.session.execute', side_effect=RuntimeError('secret connection detail')):
        response = client.get('/health')
    assert response.status_code == 200
    assert response.get_json()['status'] == 'DEGRADED'
    assert response.get_json()['database'] == 'UNHEALTHY'
    assert 'secret connection detail' not in response.get_data(as_text=True)


def test_health_probes_are_rate_limit_exempt(client):
    for path in ('/health/live', '/health/ready', '/health'):
        for _ in range(5):
            response = client.get(path)
            assert response.status_code in (200, 503)


def test_health_policy_exists():
    from pathlib import Path
    policy = Path('docs/HEALTH_CHECK_POLICY.md').read_text(encoding='utf-8')
    for required in ('/health/live', '/health/ready', 'HTTP 503', 'connection strings', 'rate limits'):
        assert required in policy
