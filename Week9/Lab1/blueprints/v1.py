from flask import Blueprint, current_app
from .users_data import get_user

bp = Blueprint('v1', __name__)


@bp.after_request
def sunset_header(response):
    if current_app.config.get('V1_SUNSET'):
        response.headers['Sunset'] = current_app.config['V1_SUNSET']
    return response


@bp.get('/<int:uid>')
def get(uid):
    user = get_user(uid)
    if user is None:
        return {'error': 'nf'}, 404
    return {
        'id': uid,
        'full_name': f"{user['first_name']} {user['last_name']}",
        'email': user['email'],
    }
