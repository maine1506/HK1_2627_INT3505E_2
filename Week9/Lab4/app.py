"""Practice 4/5: one POST /orders URL, two handlers."""

import logging
import os

from flask import Flask, jsonify, request

from gateway import V2_PERCENT, dispatch


def create_app(v2_percent=None):
    app = Flask(__name__)
    percent = int(os.environ.get('V2_PERCENT', V2_PERCENT)) if v2_percent is None else v2_percent
    if type(percent) is not int or not 0 <= percent <= 100:
        raise ValueError('V2_PERCENT must be an integer between 0 and 100')
    app.config['V2_PERCENT'] = percent

    @app.post('/orders')
    def create_order():
        if not request.is_json:
            return {'error': 'Content-Type must be application/json'}, 415
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return {'error': 'Body must be a JSON object'}, 400
        account = body.get('account_id')
        if not isinstance(account, str) or not account.strip():
            return {'error': 'account_id must be a non-empty string'}, 400
        which, result = dispatch(body)
        response = jsonify(result)
        response.headers['X-Order-Handler'] = which
        return response, (201 if which == 'v2' else 200)

    return app


app = create_app()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run(host='127.0.0.1', port=5000)
