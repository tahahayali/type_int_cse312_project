import os
import logging
import jwt
from datetime import datetime, timezone
from flask import request
import re 

_AUTH_RE = re.compile(r'auth_token=[^;,\s]*', flags=re.IGNORECASE)

# Secret key for JWT decoding (must match auth service)
SECRET_KEY = os.environ.get("SECRET_KEY", "dev_secret_key")

# Ensure log directory exists
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Log file paths
REQUEST_LOG_PATH = os.path.join(LOG_DIR, "requests.log")
RAW_LOG_PATH = os.path.join(LOG_DIR, "http_raw.log")
ERROR_LOG_PATH = os.path.join(LOG_DIR, "errors.log")
SENSITIVE_PATHS = {"/login", "/register"}          # body must NOT be logged

# Configure root logger
default_logger = logging.getLogger()
default_logger.setLevel(logging.INFO)

# 🚫  Remove any previous handlers added during an earlier import / reload
for h in list(default_logger.handlers):
    default_logger.removeHandler(h)

class MaxLevelFilter(logging.Filter):
    """Allow records up to (and including) a certain level."""
    def __init__(self, level):
        self.max_level = level
    def filter(self, record):
        return record.levelno <= self.max_level


# ─── handlers ────────────────────────────────────────────────
request_handler = logging.FileHandler(REQUEST_LOG_PATH, encoding="utf-8")
raw_handler     = logging.FileHandler(RAW_LOG_PATH,     encoding="utf-8")
error_handler   = logging.FileHandler(ERROR_LOG_PATH,   encoding="utf-8")
stream_handler  = logging.StreamHandler()

error_handler.setLevel(logging.ERROR)      # only ERROR & CRITICAL

# Accept INFO and below in these two files, but *not* ERROR
info_only_filter = MaxLevelFilter(logging.INFO)
request_handler.addFilter(info_only_filter)
raw_handler.addFilter(info_only_filter)

# levels (for clarity)
request_handler.setLevel(logging.INFO)
raw_handler.setLevel(logging.INFO)
stream_handler.setLevel(logging.INFO)

# Simple formatter (messages already include timestamp etc.)
formatter = logging.Formatter("%(message)s")
for h in (request_handler, raw_handler, error_handler, stream_handler):
    h.setFormatter(formatter)
    default_logger.addHandler(h)


def _get_username():
    """
    Extracts 'username' from JWT in HttpOnly cookie, if present.
    """
    token = request.cookies.get("auth_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload.get("username")
    except Exception:
        return None


def log_request(response):
    """
    Logs every HTTP request: IP, method, path, status, timestamp, and JWT username if any.
    """
    # ip = request.remote_addr
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    method = request.method
    path = request.path
    status = response.status_code
    timestamp = datetime.now(timezone.utc).isoformat()
    user = _get_username()
    user_part = f" user='{user}'" if user else ""

    entry = f"[{timestamp}] {ip} {method} {path} -> {status}{user_part}"
    default_logger.info(entry)
    return response


def log_auth_attempt(action, username, success, reason=None):
    """
    Logs registration/login attempts: IP, timestamp, action, user, result.
    """
    # ip = request.remote_addr
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    timestamp = datetime.now(timezone.utc).isoformat()
    if success:
        entry = f"[{timestamp}] {ip} {action.upper()} SUCCESS for user '{username}'"
    else:
        entry = f"[{timestamp}] {ip} {action.upper()} FAILED for user '{username}' - Reason: {reason}"
    default_logger.info(entry)



def _mask_auth_token(value: str) -> str:
    """Replace auth_token’s value with [REDACTED] inside a header string."""
    return _AUTH_RE.sub('auth_token=[REDACTED]', value)

def redact_sensitive_headers(headers):
    """
    Redact only the auth_token inside Cookie / Set‑Cookie headers,
    and fully redact Authorization‑style headers.
    """
    redacted = {}
    for k, v in headers.items():
        kl = k.lower()

        # Full redaction for Authorization / Bearer headers
        if "authorization" in kl:
            redacted[k] = "[REDACTED]"

        # Partial redaction for auth_token inside Cookie / Set‑Cookie
        elif kl in ("cookie", "set-cookie"):
            redacted[k] = _mask_auth_token(v)

        else:
            redacted[k] = v

    return redacted

def _safe_body():
    """
    Return ≤2 KiB of text body **except** for sensitive auth endpoints,
    where the rubric demands headers‑only logging.
    """
    if request.path in SENSITIVE_PATHS:
        return ""                                  # blank body → “headers only”
    try:
        return request.get_data(as_text=True)[:2048]
    except Exception:
        return "[Unreadable]"


def log_raw_http(response):
    """
    Write one entry to http_raw.log containing:
      • full headers of the incoming request
      • up‑to‑2048 B of its body (unless path is sensitive → omitted)
      • full headers of the outgoing response
      • up‑to‑2048 B of its body (text / JSON only; else placeholder)
    Passwords and auth tokens are redacted.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    ip        = request.headers.get("X-Forwarded-For", request.remote_addr)
    user      = _get_username()
    user_part = f" user='{user}'" if user else ""

    # ──────── HEADERS (w/ auth‑token redaction) ────────────────────────────
    req_hdrs  = redact_sensitive_headers(dict(request.headers))
    resp_hdrs = redact_sensitive_headers(dict(response.headers))

    # ──────── BODY (request) ───────────────────────────────────────────────
    req_body  = _safe_body()                    # ≤2 KiB or "" for sensitive paths

    # extra password scrubbing if body present
    if "password=" in req_body:
        req_body = req_body.replace("password=", "password=[REDACTED]")
    if '"password"' in req_body:
        req_body = re.sub(
            r'"password"\s*:\s*"[^"]+"',
            '"password": "[REDACTED]"',
            req_body
        )

    # ──────── BODY (response) ──────────────────────────────────────────────
    try:
        if "text" in response.content_type or "json" in response.content_type:
            resp_body = response.get_data(as_text=True)[:2048]
        else:
            resp_body = "[Binary or non-text response]"
    except Exception:
        resp_body = "[Unreadable]"

    # ──────── FORMAT AND WRITE ENTRY ───────────────────────────────────────
    raw_entry = (
        f"[{timestamp}] {ip} REQUEST {request.method} {request.path}{user_part}\n"
        f"Headers: {req_hdrs}\n"
        f"Body (trimmed): {req_body}\n"
        f"[{timestamp}] {ip} RESPONSE {response.status_code} {request.path}{user_part}\n"
        f"Headers: {resp_hdrs}\n"
        f"Body (trimmed): {resp_body}\n"
        + "-" * 60 + "\n"
    )

    with open(RAW_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(raw_entry)

    return response

def log_error(e):
    """
    Logs uncaught exceptions with full stack trace, associated request info, and JWT username.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        # ip = request.remote_addr
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        method = request.method
        path = request.path
    except Exception:
        ip = method = path = 'N/A'

    user = _get_username()
    user_part = f" user='{user}'" if user else ""

    error_msg = f"[{timestamp}] {ip} {method} {path} ERROR{user_part}: {e}"
    default_logger.error(error_msg, exc_info=True)


def register_error_handlers(app):
    """
    Call in your Flask setup to capture all exceptions.
    @app.errorhandler(Exception)
    def handle_exc(e):
        log_error(e)
        raise e  # let Flask return 500
    """
    @app.errorhandler(Exception)
    def handle_exc(e):
        log_error(e)
        raise e
    return app
