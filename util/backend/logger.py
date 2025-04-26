import os
import logging
from datetime import datetime, timezone
from flask import request
# from logging.handlers import RotatingFileHandler

LOG_DIR = "logs"
# LOG_DIR = "." # trying to have the log dir be the root directory

os.makedirs(LOG_DIR, exist_ok=True)

REQUEST_LOG_PATH = os.path.join(LOG_DIR, "requests.log")
RAW_LOG_PATH = os.path.join(LOG_DIR, "http_raw.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[
        logging.FileHandler(REQUEST_LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

def log_request(response):
    ip = request.remote_addr
    method = request.method
    path = request.path
    status = response.status_code
    timestamp = datetime.now(timezone.utc).isoformat()

    log_entry = f"[{timestamp}] {ip} {method} {path} -> {status}"
    logging.info(log_entry)

    return response

def log_auth_attempt(action, username, success, reason=None):
    ip = request.remote_addr
    timestamp = datetime.now(timezone.utc).isoformat()

    if success:
        log_entry = f"[{timestamp}] {ip} {action.upper()} SUCCESS for user '{username}'"
    else:
        log_entry = f"[{timestamp}] {ip} {action.upper()} FAILED for user '{username}' - Reason: {reason}"
    
    logging.info(log_entry)

# Before we were printing the auth_token in the logs, but that is a security risk.
def redact_sensitive_headers(headers):
    redacted = {}
    for key, value in headers.items():
        lower_key = key.lower()
        if "authorization" in lower_key:
            redacted[key] = "[REDACTED]"
        elif "cookie" in lower_key:
            redacted[key] = "[REDACTED]"
        elif "set-cookie" in lower_key:
            redacted[key] = "[REDACTED]"
        else:
            redacted[key] = value
    return redacted

def log_raw_http(response):
    timestamp = datetime.now(timezone.utc).isoformat()
    ip = request.remote_addr

    req_headers = redact_sensitive_headers(dict(request.headers))
    req_log = f"[{timestamp}] {ip} REQUEST {request.method} {request.path}\nHeaders: {req_headers}"

    resp_headers = redact_sensitive_headers(dict(response.headers))
    resp_log = f"[{timestamp}] {ip} RESPONSE {response.status_code} {request.path}\nHeaders: {resp_headers}"

    raw_entry = f"{req_log}\n{resp_log}\n{'-'*60}\n"

    trimmed_entry = raw_entry[:2048]

    with open(RAW_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(trimmed_entry)
    
    return response