"""Demo handlers; no database or payment operations are performed."""

from uuid import uuid4


def v1_create_order(body):
    return {
        'order_id': str(uuid4()),
        'account_id': body['account_id'],
        'status': 'created',
    }


def v2_create_order(body):
    return {
        'order_id': str(uuid4()),
        'account_id': body['account_id'],
        'status': 'created',
        'version': 'v2',
        'message': 'Order created by the new handler',
    }
