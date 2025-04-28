import os
import bcrypt
from datetime import datetime, timedelta, timezone
from flask import request, jsonify, make_response
from db.database import users, sessions
from util.backend.logger import log_auth_attempt
import jwt as pyjwt

# Secret key for JWTs (set via environment in production)
SECRET_KEY = os.environ.get("SECRET_KEY", "dev_secret_key")
# Token expiration time (e.g., 24 hours)
TOKEN_EXP_HOURS = int(os.environ.get("TOKEN_EXP_HOURS", 24))


def register():
    """
    Handles user registration. Expects JSON with 'username' and 'password'.
    """
    data = request.get_json() or {}
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify(error="Username and password are required"), 400

    # Check if username already exists
    if users.find_one({"username": username}):
        log_auth_attempt("register", username, False, "Username already exists")
        return jsonify(error="Username already exists"), 400

    # Hash the password with bcrypt
    pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    users.insert_one({
        "username": username,
        "password": pw_hash,
        "created_at": datetime.now(timezone.utc)
    })

    log_auth_attempt("register", username, True)
    return jsonify(message="Registration successful"), 201


def login():
    """
    Handles user login. Enforces a single session per user:
      1) On login, drop any old session docs.
      2) Insert the new session record.
      3) HTTP-set the cookie as before.
    """
    data     = request.get_json() or {}
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify(error="Username and password are required"), 400

    user = users.find_one({"username": username})
    if not user or not bcrypt.checkpw(password.encode(), user["password"]):
        log_auth_attempt("login", username, False, "Invalid credentials")
        return jsonify(error="Invalid username or password"), 401

    # kill any old sessions for this user
    sessions.delete_many({"username": username})

    # generate JWT
    exp     = datetime.utcnow() + timedelta(hours=TOKEN_EXP_HOURS)
    payload = {"username": username, "exp": exp}
    token   = pyjwt.encode(payload, SECRET_KEY, algorithm="HS256")

    # store only hash of token
    token_hash = bcrypt.hashpw(token.encode(), bcrypt.gensalt())
    sessions.insert_one({
        "username":     username,
        "token_hash":   token_hash,
        "created_at":   datetime.now(timezone.utc),
        "expires_at":   exp,
        # socket_id will be set once the WebSocket connects
    })

    log_auth_attempt("login", username, True)

    resp = make_response(jsonify(message="Login successful"))
    is_prod = os.environ.get("ENVIRONMENT") == "production"
    resp.set_cookie(
        "auth_token", token,
        httponly=True,
        secure=is_prod,
        samesite="Strict",
        max_age=TOKEN_EXP_HOURS * 3600
    )
    return resp, 200

# def login():
#     """
#     Handles user login. Expects JSON with 'username' and 'password'.
#     Issues a JWT and sets it as HttpOnly cookie if credentials valid.
#     """
#     data = request.get_json() or {}
#     username = data.get("username")
#     password = data.get("password")
#
#     if not username or not password:
#         return jsonify(error="Username and password are required"), 400
#
#     user = users.find_one({"username": username})
#     if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password']):
#         log_auth_attempt("login", username, False, "Invalid credentials")
#         return jsonify(error="Invalid username or password"), 401
#
#     # Generate JWT token
#     exp = datetime.utcnow() + timedelta(hours=TOKEN_EXP_HOURS)
#     payload = {"username": username, "exp": exp}
#     token = pyjwt.encode(payload, SECRET_KEY, algorithm="HS256")
#     # Store only a bcrypt-hash of the token in the sessions collection
#     token_hash = bcrypt.hashpw(token.encode('utf-8'), bcrypt.gensalt())
#     sessions.insert_one({
#         "username": username,
#         "token_hash": token_hash,
#         "created_at": datetime.now(timezone.utc),
#         "expires_at": exp
#     })
#
#
#
#     log_auth_attempt("login", username, True)
#
#     # Set HttpOnly cookie
#     resp = make_response(jsonify(message="Login successful"))
#
#     # In production, set secure=True
#     is_prod = os.environ.get("ENVIRONMENT") == "production"
#
#     resp.set_cookie(
#         "auth_token", token,
#         httponly=True,
#         secure=is_prod,  # Only use secure in production
#         samesite='Strict',
#         max_age=TOKEN_EXP_HOURS * 3600  # Convert hours to seconds
#     )
#     return resp, 200


def logout():
    """
    Handles user logout. Deletes the session record and clears the cookie.
    """
    token = request.cookies.get("auth_token")
    if not token:
        return jsonify(error="No active session"), 400

    # Decode token to get username
    try:
        payload = pyjwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        username = payload.get("username")
    except pyjwt.ExpiredSignatureError:
        return jsonify(error="Session expired"), 401
    except pyjwt.InvalidTokenError:
        return jsonify(error="Invalid token"), 401

    # Find matching session and remove it
    for sess in sessions.find({"username": username}):
        if bcrypt.checkpw(token.encode('utf-8'), sess.get('token_hash', b'')):
            sessions.delete_one({"_id": sess['_id']})
            break

    resp = make_response(jsonify(message="Logout successful"))
    resp.set_cookie("auth_token", "", expires=0, max_age=0)
    resp.delete_cookie("auth_token")
    return resp, 200


def token_required(fn):
    """
    Decorator to protect routes: checks for valid JWT cookie and session.
    """
    from functools import wraps
    from flask import request, g

    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = request.cookies.get("auth_token")
        if not token:
            return jsonify(error="Authentication required"), 401

        # Verify JWT signature and expiration
        try:
            payload = pyjwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        except pyjwt.ExpiredSignatureError:
            return jsonify(error="Session expired"), 401
        except pyjwt.InvalidTokenError:
            return jsonify(error="Invalid token"), 401

        # Verify token hash exists in DB
        username = payload.get("username")
        valid = False
        for sess in sessions.find({"username": username}):
            if bcrypt.checkpw(token.encode('utf-8'), sess.get('token_hash', b'')):
                valid = True
                break
        if not valid:
            return jsonify(error="Invalid session"), 401

        # Attach username to request context if needed
        g.username = username  # Store username in Flask's g object
        return fn(*args, **kwargs)

    return wrapper