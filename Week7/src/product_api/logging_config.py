import json
import logging
import sys
import time
import uuid

from flask import g


class JsonFormatter(logging.Formatter):
    converter = time.gmtime

    def format(self, record):
        payload = {"ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%SZ"),
                   "level": record.levelname, "event": record.getMessage()}
        for key in ("request_id", "status", "latency_ms"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure(app):
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    app.logger.handlers = [handler]
    app.logger.setLevel(app.config["LOG_LEVEL"])

    @app.before_request
    def start():
        g.started = time.perf_counter()
        g.request_id = str(uuid.uuid4())

    @app.after_request
    def done(response):
        response.headers["X-Request-Id"] = g.request_id
        app.logger.info("done", extra={"request_id": g.request_id, "status": response.status_code,
                                      "latency_ms": round((time.perf_counter() - g.started) * 1000, 2)})
        return response
