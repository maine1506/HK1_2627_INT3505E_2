import pytest

from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.mark.parametrize('version', [None, '1', '2', '2024-06-20'])
def test_version_selection(client, version):
    headers = {} if version is None else {'X-API-Version': version}
    response = client.get('/users/1', headers=headers)
    assert response.status_code == 200
    assert response.headers['X-API-Version-Served'] == (version or '2')
    assert 'X-API-Version' in response.vary
    if version == '1':
        assert response.json == {'id': 1, 'full_name': 'Văn Nguyễn'}
    else:
        assert response.json == {
            'id': 1, 'first_name': 'Văn', 'last_name': 'Nguyễn', 'email': 'a@vnu.vn'
        }


@pytest.mark.parametrize('version', ['99', '', 'v1', '2024-06-21'])
def test_unsupported_version(client, version):
    response = client.get('/users/1', headers={'X-API-Version': version})
    assert response.status_code == 400
    assert response.json == {'error': 'unsupported version'}
    assert 'X-API-Version-Served' not in response.headers
    assert 'X-API-Version' in response.vary


@pytest.mark.parametrize('version', ['1', '2', '2024-06-20'])
def test_missing_user(client, version):
    response = client.get('/users/999', headers={'X-API-Version': version})
    assert response.status_code == 404
    assert response.json == {'error': 'not found'}
    assert response.headers['X-API-Version-Served'] == version


def test_unsupported_version_checked_before_lookup(client):
    response = client.get('/users/999', headers={'X-API-Version': '99'})
    assert response.status_code == 400
