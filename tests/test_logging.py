import json
import logging

from app.logging_config import JsonFormatter, SensitiveDataFilter


def test_sensitive_log_filter_redacts_credentials():
    record = logging.LogRecord(
        name='test',
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg='login password=super-secret token=abc123',
        args=(),
        exc_info=None,
    )
    SensitiveDataFilter().filter(record)
    assert 'super-secret' not in record.getMessage()
    assert 'abc123' not in record.getMessage()
    assert '[REDACTED]' in record.getMessage()


def test_json_formatter_contains_only_safe_request_metadata():
    record = logging.LogRecord(
        name='app',
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg='request.completed',
        args=(),
        exc_info=None,
    )
    record.request_id = 'abc123'
    record.extra_data = {
        'method': 'POST',
        'path': '/auth/login',
        'status': 200,
        'password': 'must-not-appear',
    }
    output = JsonFormatter().format(record)
    payload = json.loads(output)
    assert payload['message'] == 'request.completed'
    assert payload['request_id'] == 'abc123'
    assert payload['data']['path'] == '/auth/login'
    assert payload['data']['password'] == '[REDACTED]'
    assert 'must-not-appear' not in output
    assert 'query_string' not in output


def test_request_logging_adds_correlation_id(client):
    response = client.get('/health/live')
    request_id = response.headers.get('X-Request-ID')
    assert request_id
    assert len(request_id) == 32


def test_request_logging_preserves_supplied_correlation_id(client):
    response = client.get('/health/live', headers={'X-Request-ID': 'external-request-42'})
    assert response.headers['X-Request-ID'] == 'external-request-42'
