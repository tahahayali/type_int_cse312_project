# import os
# import logging
# from datetime import datetime, timezone
# from flask import request
# # from logging.handlers import RotatingFileHandler
#
# LOG_DIR = "logs"
# # LOG_DIR = "." # trying to have the log dir be the root directory
#
# os.makedirs(LOG_DIR, exist_ok=True)
#
# REQUEST_LOG_PATH = os.path.join(LOG_DIR, "requests.log")
# RAW_LOG_PATH = os.path.join(LOG_DIR, "http_raw.log")
#
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(message)s",
#     handlers=[
#         logging.FileHandler(REQUEST_LOG_PATH, encoding="utf-8"),
#         logging.StreamHandler()
#     ]
# )
#
# def log_request(response):
#     ip = request.remote_addr
#     method = request.method
#     path = request.path
#     status = response.status_code
#     timestamp = datetime.now(timezone.utc).isoformat()
#
#     log_entry = f"[{timestamp}] {ip} {method} {path} -> {status}"
#     logging.info(log_entry)
#
#     return response
#
# def log_auth_attempt(action, username, success, reason=None):
#     ip = request.remote_addr
#     timestamp = datetime.now(timezone.utc).isoformat()
#
#     if success:
#         log_entry = f"[{timestamp}] {ip} {action.upper()} SUCCESS for user '{username}'"
#     else:
#         log_entry = f"[{timestamp}] {ip} {action.upper()} FAILED for user '{username}' - Reason: {reason}"
#
#     logging.info(log_entry)
#
# # Before we were printing the auth_token in the logs, but that is a security risk.
# def redact_sensitive_headers(headers):
#     redacted = {}
#     for key, value in headers.items():
#         lower_key = key.lower()
#         if "authorization" in lower_key:
#             redacted[key] = "[REDACTED]"
#         elif "cookie" in lower_key:
#             redacted[key] = "[REDACTED]"
#         elif "set-cookie" in lower_key:
#             redacted[key] = "[REDACTED]"
#         else:
#             redacted[key] = value
#     return redacted
#
# def log_raw_http(response):
#     timestamp = datetime.now(timezone.utc).isoformat()
#     ip = request.remote_addr
#
#     req_headers = redact_sensitive_headers(dict(request.headers))
#     req_log = f"[{timestamp}] {ip} REQUEST {request.method} {request.path}\nHeaders: {req_headers}"
#
#     resp_headers = redact_sensitive_headers(dict(response.headers))
#     resp_log = f"[{timestamp}] {ip} RESPONSE {response.status_code} {request.path}\nHeaders: {resp_headers}"
#
#     raw_entry = f"{req_log}\n{resp_log}\n{'-'*60}\n"
#
#     trimmed_entry = raw_entry[:2048]
#
#     with open(RAW_LOG_PATH, "a", encoding="utf-8") as f:
#         f.write(trimmed_entry)
#
#     return response





import os
import logging
import jwt
from datetime import datetime, timezone
from flask import request

# Secret key for JWT decoding (must match auth service)
SECRET_KEY = os.environ.get("SECRET_KEY", "dev_secret_key")

# Ensure log directory exists
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Log file paths
REQUEST_LOG_PATH = os.path.join(LOG_DIR, "requests.log")
RAW_LOG_PATH = os.path.join(LOG_DIR, "http_raw.log")
ERROR_LOG_PATH = os.path.join(LOG_DIR, "errors.log")

# Configure root logger
default_logger = logging.getLogger()
default_logger.setLevel(logging.INFO)

# Handlers for different log streams
request_handler = logging.FileHandler(REQUEST_LOG_PATH, encoding="utf-8")
raw_handler = logging.FileHandler(RAW_LOG_PATH, encoding="utf-8")
error_handler = logging.FileHandler(ERROR_LOG_PATH, encoding="utf-8")
stream_handler = logging.StreamHandler()

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
    ip = request.remote_addr
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
    ip = request.remote_addr
    timestamp = datetime.now(timezone.utc).isoformat()
    if success:
        entry = f"[{timestamp}] {ip} {action.upper()} SUCCESS for user '{username}'"
    else:
        entry = f"[{timestamp}] {ip} {action.upper()} FAILED for user '{username}' - Reason: {reason}"
    default_logger.info(entry)


def redact_sensitive_headers(headers):
    """
    Removes any auth tokens, cookies, or authorization headers from a header dict.
    """
    redacted = {}
    for k, v in headers.items():
        kl = k.lower()
        if any(s in kl for s in ("authorization", "cookie", "set-cookie", "auth_token")):
            redacted[k] = "[REDACTED]"
        else:
            redacted[k] = v
    return redacted


def log_raw_http(response):
    """
    Logs raw HTTP request and response headers (up to 2048 bytes), redacting sensitive values.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    ip = request.remote_addr
    user = _get_username()
    user_part = f" user='{user}'" if user else ""

    req_hdrs = redact_sensitive_headers(dict(request.headers))
    req_log = f"[{timestamp}] {ip} REQUEST {request.method} {request.path}{user_part}\nHeaders: {req_hdrs}"

    resp_hdrs = redact_sensitive_headers(dict(response.headers))
    resp_log = f"[{timestamp}] {ip} RESPONSE {response.status_code} {request.path}{user_part}\nHeaders: {resp_hdrs}"

    raw_entry = f"{req_log}\n{resp_log}\n{'-'*60}\n"
    trimmed = raw_entry[:2048]

    # Append to raw log file
    with open(RAW_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(trimmed)
    return response


def log_error(e):
    """
    Logs uncaught exceptions with full stack trace, associated request info, and JWT username.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    try:
        ip = request.remote_addr
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
