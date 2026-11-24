from datetime import datetime, timezone
import logging
from unittest.mock import patch

import pytest
from flask import Flask

from app import V1_SUNSET, create_app
from sunset import deprecate_at


@pytest.mark.parametrize('now, status', [
    (datetime(2026, 12, 30, tzinfo=timezone.utc), 200),
    (V1_SUNSET, 410),
    (datetime(2027, 1, 1, tzinfo=timezone.utc), 410),
])
def test_sunset_lifecycle(now, status, caplog):
    app = create_app()
    app.config['TESTING'] = True
    with patch('sunset.datetime') as clock, caplog.at_level(logging.WARNING, logger='sunset'):
        clock.now.return_value = now
        response = app.test_client().get('/api/v1/users/1')
    assert response.status_code == status
    assert response.headers['Sunset'] == 'Thu, 31 Dec 2026 23:59:59 GMT'
    assert response.headers['Deprecation'] == 'true'
    assert response.headers['Link'] == '</api/v2/users>; rel="successor-version"'
    assert 'deprecated_call /api/v1/users/1 127.0.0.1' in caplog.text
    if status == 200:
        assert response.json == {'id': 1, 'full_name': 'Nguyễn Văn A'}
    else:
        assert response.json == {
            'error': 'gone', 'sunset': 'Thu, 31 Dec 2026 23:59:59 GMT',
            'use_instead': '/api/v2/users',
        }


def test_expired_handler_is_not_called():
    app = Flask(__name__)

    @app.get('/expired')
    @deprecate_at(datetime(2020, 1, 1, tzinfo=timezone.utc))
    def expired():
        pytest.fail('Expired handler must not run')

    response = app.test_client().get('/expired')
    assert response.status_code == 410
    assert 'Link' not in response.headers


def test_preserves_handler_status_and_headers():
    app = Flask(__name__)

    @app.get('/missing')
    @deprecate_at(datetime(2099, 1, 1, tzinfo=timezone.utc))
    def missing():
        return {'error': 'not found'}, 404, {'X-Test': 'preserved'}

    response = app.test_client().get('/missing')
    assert response.status_code == 404
    assert response.json == {'error': 'not found'}
    assert response.headers['X-Test'] == 'preserved'
    assert response.headers['Deprecation'] == 'true'


def test_v2_has_no_deprecation_headers():
    response = create_app().test_client().get('/api/v2/users/1')
    assert response.status_code == 200
    assert response.json['first_name'] == 'Văn A'
    for header in ('Sunset', 'Deprecation', 'Link'):
        assert header not in response.headers


def test_rejects_naive_date():
    with pytest.raises(ValueError, match='timezone'):
        deprecate_at(datetime(2026, 12, 31))
