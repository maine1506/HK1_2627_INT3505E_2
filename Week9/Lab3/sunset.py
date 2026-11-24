"""Reusable Sunset decorator for Practice 3."""

from datetime import datetime, timezone
from email.utils import format_datetime
from functools import wraps
import logging

from flask import jsonify, make_response, request

log = logging.getLogger('sunset')


def http_date(dt):
    return format_datetime(dt.astimezone(timezone.utc), usegmt=True)


def deprecate_at(sunset_date, replacement=None):
    if sunset_date.tzinfo is None or sunset_date.utcoffset() is None:
        raise ValueError('sunset_date must include a timezone')

    def wrap(fn):
        @wraps(fn)
        def inner(*args, **kwargs):
            log.warning('deprecated_call %s %s', request.path, request.remote_addr)
            if datetime.now(timezone.utc) >= sunset_date:
                response = jsonify(
                    error='gone', sunset=http_date(sunset_date),
                    use_instead=replacement,
                )
                response.status_code = 410
            else:
                response = make_response(fn(*args, **kwargs))
            response.headers['Sunset'] = http_date(sunset_date)
            # Keep the value requested by the exercise on page 22.
            response.headers['Deprecation'] = 'true'
            if replacement:
                response.headers['Link'] = f'<{replacement}>; rel="successor-version"'
            return response
        return inner
    return wrap
