"""Practice 3/5: Sunset middleware."""

import logging
from datetime import datetime, timezone

from flask import Flask

from sunset import deprecate_at

V1_SUNSET = datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc)


def create_app(sunset_date=V1_SUNSET):
    app = Flask(__name__)
    app.json.ensure_ascii = False

    @app.get('/api/v1/users/<int:uid>')
    @deprecate_at(sunset_date, replacement='/api/v2/users')
    def get_v1(uid):
        return {'id': uid, 'full_name': 'Nguyễn Văn A'}

    @app.get('/api/v2/users/<int:uid>')
    def get_v2(uid):
        return {'id': uid, 'first_name': 'Văn A', 'last_name': 'Nguyễn'}

    return app


app = create_app()

if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING)
    app.run(host='127.0.0.1', port=5000)
