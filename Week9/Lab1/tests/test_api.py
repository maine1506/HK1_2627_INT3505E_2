import pytest
from app import create_app
from blueprints.users_data import USERS


@pytest.fixture
def client():
    original = {uid: dict(user) for uid, user in USERS.items()}
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client
    USERS.clear()
    USERS.update(original)


def test_version_contracts(client):
    v1 = client.get('/api/v1/users/1')
    v2 = client.get('/api/v2/users/1')
    assert v1.status_code == v2.status_code == 200
    assert v1.json == {'id': 1, 'full_name': 'Văn Nguyễn', 'email': 'a@vnu.vn'}
    assert v2.json == {'id': 1, 'first_name': 'Văn', 'last_name': 'Nguyễn', 'email': 'a@vnu.vn'}
    assert v1.headers['Sunset'] == 'Thu, 31 Dec 2026 23:59:59 GMT'
    assert 'Sunset' not in v2.headers


@pytest.mark.parametrize('version', ['v1', 'v2'])
def test_not_found(client, version):
    response = client.get(f'/api/{version}/users/999')
    assert response.status_code == 404
    assert response.json == {'error': 'nf'}


def test_create_shared_between_versions(client):
    body = {'first_name': 'An', 'last_name': 'Lê', 'email': 'an@example.com'}
    response = client.post('/api/v2/users', json=body)
    assert response.status_code == 201
    uid = response.json['id']
    assert response.json == {'id': uid, **body}
    assert client.get(response.headers['Location']).json == response.json
    assert client.get(f'/api/v1/users/{uid}').json['full_name'] == 'An Lê'
    assert client.post('/api/v1/users', json=body).status_code == 404


@pytest.mark.parametrize('body', [None, [], {}, {'first_name': 'An'},
    {'first_name': '', 'last_name': 'Lê', 'email': 'a@b.com'},
    {'first_name': 1, 'last_name': 'Lê', 'email': 'a@b.com'},
    {'first_name': 'An', 'last_name': 'Lê', 'email': 'a@b.com', 'id': 10}])
def test_invalid_json_body(client, body):
    import json
    response = client.post('/api/v2/users', data=json.dumps(body), content_type='application/json')
    assert response.status_code == 400


def test_invalid_content(client):
    assert client.post('/api/v2/users', data='text').status_code == 415
    assert client.post('/api/v2/users', data='{', content_type='application/json').status_code == 400


def test_openapi(client):
    response = client.get('/openapi.json')
    assert response.status_code == 200
    assert response.json['openapi'] == '3.0.3'
    assert '/api/v1/users/{uid}' in response.json['paths']
    assert '/api/v2/users' in response.json['paths']
