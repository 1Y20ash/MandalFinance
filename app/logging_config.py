"""Application logging configuration for production-safe operational logs."""

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from flask import g, has_request_context, request


SENSITIVE_FIELD_NAMES = {
    "password",
    "password_confirmation",
    "confirm_password",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "api_key",
    "key_secret",
    "service_role_key",
    "webhook_secret",
    "authorization",
    "cookie",
}


class SensitiveDataFilter(logging.Filter):
    """Remove common credential material from log messages and fields."""

    def filter(self, record):
        message = record.getMessage()
        record.msg = self._redact(message)
        record.args = ()
        if isinstance(getattr(record, "extra_data", None), dict):
            record.extra_data = self._redact_mapping(record.extra_data)
        return True

    @classmethod
    def _redact(cls, value):
        if not isinstance(value, str):
            return value
        # Keep this deliberately conservative: application code should never
        # log secrets, but this catches accidental key=value style logging.
        import re
        pattern = re.compile(
            r"(?i)(password|secret|token|api[_-]?key|authorization|cookie)"
            r"\s*[:=]\s*([^\s,;]+)"
        )
        return pattern.sub(lambda m: f"{m.group(1)}=[REDACTED]", value)

    @classmethod
    def _redact_mapping(cls, value):
        result = {}
        for key, item in value.items():
            if str(key).lower() in SENSITIVE_FIELD_NAMES:
                result[key] = "[REDACTED]"
            elif isinstance(item, dict):
                result[key] = cls._redact_mapping(item)
            else:
                result[key] = item
        return result


class JsonFormatter(logging.Formatter):
    """Emit machine-readable logs without request bodies or query strings."""

    def format(self, record):
        payload = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = getattr(record, "request_id", None)
        if request_id:
            payload["request_id"] = request_id
        extra_data = getattr(record, "extra_data", None)
        if isinstance(extra_data, dict):
            payload["data"] = SensitiveDataFilter._redact_mapping(extra_data)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _level_from_environment():
    configured = os.getenv("LOG_LEVEL", "INFO").upper()
    return configured if configured in logging._nameToLevel else "INFO"


def configure_logging(app):
    """Configure one stdout-oriented, privacy-filtered application logger."""
    level = _level_from_environment()
    app.logger.setLevel(level)
    app.logger.propagate = False

    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(SensitiveDataFilter())

    for existing in list(app.logger.handlers):
        app.logger.removeHandler(existing)
        existing.close()
    app.logger.addHandler(handler)

    # Werkzeug request logs inherit the same level but are kept separate from
    # application events. Their default formatter does not expose credentials.
    logging.getLogger("werkzeug").setLevel(level)
    return app


def install_request_logging(app):
    """Attach correlation IDs and minimal request telemetry."""

    @app.before_request
    def _start_request_logging():
        g.request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        g.request_started_at = time.perf_counter()

    @app.after_request
    def _finish_request_logging(response):
        request_id = getattr(g, "request_id", None)
        if request_id:
            response.headers["X-Request-ID"] = request_id
        started = getattr(g, "request_started_at", None)
        duration_ms = round((time.perf_counter() - started) * 1000, 2) if started else None
        extra = {
            "method": request.method,
            "path": request.path,
            "status": response.status_code,
        }
        if duration_ms is not None:
            extra["duration_ms"] = duration_ms
        app.logger.info(
            "request.completed",
            extra={"request_id": request_id, "extra_data": extra},
        )
        return response

    @app.errorhandler(500)
    def _log_internal_error(error):
        app.logger.exception(
            "request.failed",
            extra={
                "request_id": getattr(g, "request_id", None),
                "extra_data": {"method": request.method, "path": request.path},
            },
        )
        from flask import jsonify
        return jsonify({"error": "Internal server error"}), 500

    return app
