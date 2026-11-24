"""Three-tier blue-green routing from Practice 4, page 23."""

import hashlib
import logging

from flask import current_app, request

from handlers import v1_create_order, v2_create_order

V2_PERCENT = 5
V2_COHORTS = {'beta', 'internal'}
V2_FORCE_ACCOUNTS = {'acct_42', 'acct_99'}
log = logging.getLogger('gateway')


def account_bucket(account_id):
    # MD5 is used only for deterministic assignment, not for security.
    return int(hashlib.md5(account_id.encode()).hexdigest(), 16) % 100


def route_to_v2(body):
    cohort = request.headers.get('X-Cohort', '').lower()
    if cohort in V2_COHORTS:
        return True
    account = body['account_id']
    if account in V2_FORCE_ACCOUNTS:
        return True
    percent = current_app.config['V2_PERCENT']
    return account_bucket(account) < percent


def dispatch(body):
    which = 'v2' if route_to_v2(body) else 'v1'
    log.info('order_route account=%s handler=%s', body['account_id'], which)
    result = v2_create_order(body) if which == 'v2' else v1_create_order(body)
    return which, result
