from flask import jsonify

from app.extensions import db


def test_not_found_is_generic_html(app):
    client = app.test_client()
    response = client.get('/definitely-not-a-real-route')

    assert response.status_code == 404
    assert response.content_type.startswith('text/html')
    assert b'could not be found' in response.data
    assert b'Traceback' not in response.data
    assert b'Werkzeug' not in response.data


def test_not_found_supports_safe_json_contract(app):
    client = app.test_client()
    response = client.get('/definitely-not-a-real-route', headers={'Accept': 'application/json'})

    assert response.status_code == 404
    assert response.is_json
    payload = response.get_json()
    assert payload == {
        'error': {
            'code': 404,
            'message': 'The requested page could not be found.',
        }
    }


def test_unexpected_exception_is_generic_and_logged(app, caplog):
    @app.get('/phase28-test-error')
    def phase28_test_error():
        raise RuntimeError('secret database password must never be exposed')

    client = app.test_client()
    response = client.get('/phase28-test-error')

    assert response.status_code == 500
    assert response.content_type.startswith('text/html')
    assert b'Something went wrong' in response.data
    assert b'secret database password' not in response.data
    assert 'Unhandled application exception' in caplog.text


def test_unexpected_exception_supports_safe_json_contract(app):
    @app.get('/phase28-test-json-error')
    def phase28_test_json_error():
        raise RuntimeError('internal secret')

    client = app.test_client()
    response = client.get('/phase28-test-json-error', headers={'Accept': 'application/json'})

    assert response.status_code == 500
    assert response.is_json
    payload = response.get_json()
    assert payload == {
        'error': {
            'code': 500,
            'message': 'An unexpected error occurred. Please try again later.',
        }
    }
    assert 'internal secret' not in response.get_data(as_text=True)


def test_health_does_not_expose_database_exception_details(app, monkeypatch):
    secret = 'postgresql://user:super-secret-password@example.invalid/db'

    def fail_execute(*args, **kwargs):
        raise RuntimeError(secret)

    monkeypatch.setattr(db.session, 'execute', fail_execute)
    client = app.test_client()
    response = client.get('/health')

    assert response.status_code == 200
    assert response.is_json
    payload = response.get_json()
    assert payload['status'] == 'DEGRADED'
    assert payload['database'] == 'UNHEALTHY'
    assert secret not in response.get_data(as_text=True)
