from unittest.mock import patch

import pytest

from app import create_app
from gateway import account_bucket


def send(percent=5, account='ordinary', cohort=None):
    headers = {} if cohort is None else {'X-Cohort': cohort}
    return create_app(percent).test_client().post(
        '/orders', json={'account_id': account}, headers=headers,
    )


@pytest.mark.parametrize('cohort', ['beta', 'internal', 'BETA'])
def test_cohort_overrides_zero_percent(cohort):
    response = send(0, cohort=cohort)
    assert response.status_code == 201
    assert response.headers['X-Order-Handler'] == 'v2'


@pytest.mark.parametrize('account', ['acct_42', 'acct_99'])
def test_allow_list_overrides_zero_percent(account):
    response = send(0, account)
    assert response.status_code == 201
    assert response.json['account_id'] == account
    assert response.headers['X-Order-Handler'] == 'v2'


@pytest.mark.parametrize('bucket, handler, status', [(4, 'v2', 201), (5, 'v1', 200), (99, 'v1', 200)])
def test_five_percent_boundary(bucket, handler, status):
    with patch('gateway.account_bucket', return_value=bucket):
        response = send()
    assert response.status_code == status
    assert response.headers['X-Order-Handler'] == handler
    assert response.json['status'] == 'created'
    assert response.json['order_id']


@pytest.mark.parametrize('percent, handler', [(0, 'v1'), (100, 'v2')])
def test_rollout_limits(percent, handler):
    for account in ['ordinary', 'acct_1', 'acct_2']:
        assert send(percent, account).headers['X-Order-Handler'] == handler


def test_deterministic_assignment():
    assert account_bucket('abc') == 70
    responses = [send(account='abc') for _ in range(3)]
    assert {r.headers['X-Order-Handler'] for r in responses} == {'v1'}


@pytest.mark.parametrize('body', [None, [], {}, {'account_id': ''}, {'account_id': '   '}, {'account_id': 42}])
def test_invalid_body(body):
    import json
    response = create_app().test_client().post(
        '/orders', data=json.dumps(body), content_type='application/json',
    )
    assert response.status_code == 400
    assert 'X-Order-Handler' not in response.headers


def test_invalid_content():
    client = create_app().test_client()
    assert client.post('/orders', data='text').status_code == 415
    assert client.post('/orders', data='{', content_type='application/json').status_code == 400


@pytest.mark.parametrize('percent', [-1, 101, 1.5, True])
def test_invalid_rollout(percent):
    with pytest.raises(ValueError):
        create_app(percent)
