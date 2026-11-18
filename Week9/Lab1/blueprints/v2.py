from flask import Blueprint, request, url_for
from .users_data import create_user, get_user

bp = Blueprint('v2', __name__)
FIELDS = {'first_name', 'last_name', 'email'}


@bp.get('/<int:uid>')
def get(uid):
    user = get_user(uid)
    if user is None:
        return {'error': 'nf'}, 404
    return {'id': uid, **user}


@bp.post('')
def post():
    if not request.is_json:
        return {'error': 'Content-Type must be application/json'}, 415
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or set(body) != FIELDS:
        return {'error': 'Provide exactly first_name, last_name and email'}, 400
    if any(not isinstance(value, str) or not value.strip() for value in body.values()):
        return {'error': 'All fields must be non-empty strings'}, 400
    user = create_user({key: value.strip() for key, value in body.items()})
    return user, 201, {'Location': url_for('v2.get', uid=user['id'])}
