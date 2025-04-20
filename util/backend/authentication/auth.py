# # util/backend/authentication/auth.py
#
# from flask import Blueprint, request, jsonify, make_response, current_app
# from pymongo.errors import DuplicateKeyError
# import bcrypt
# import jwt
# from datetime import datetime, timedelta
#
# # adjust import path as needed
# from db.database import get_db
#
# auth_bp = Blueprint('auth', __name__)
#
# # Helper to fetch collections
# def users_col():
#     return get_db().users
#
# def sessions_col():
#     return get_db().sessions
#
# # Utility: generate and sign a JWT
# def _generate_jwt(user_id):
#     payload = {
#         'sub': str(user_id),
#         'iat': datetime.utcnow(),
#         'exp': datetime.utcnow() + timedelta(hours=12)
#     }
#     token = jwt.encode(payload, current_app.config['JWT_SECRET'], algorithm='HS256')
#     return token
#
# # Utility: decode and verify a JWT
# def _decode_jwt(token):
#     try:
#         return jwt.decode(token, current_app.config['JWT_SECRET'], algorithms=['HS256'])
#     except jwt.ExpiredSignatureError:
#         return None
#     except jwt.InvalidTokenError:
#         return None
#
# # REGISTER
# @auth_bp.route('/register', methods=['POST'])
# def register():
#     data = request.get_json() or {}
#     username = data.get('username')
#     password = data.get('password')
#     if not username or not password:
#         return jsonify({'error': 'Username and password required'}), 400
#
#     # hash password with bcrypt
#     pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
#     try:
#         users_col().insert_one({
#             '_id': username,
#             'password_hash': pw_hash
#         })
#     except DuplicateKeyError:
#         return jsonify({'error': 'Username already exists'}), 409
#
#     return jsonify({'message': 'User registered'}), 201
#
# # LOGIN
# @auth_bp.route('/login', methods=['POST'])
# def login():
#     data = request.get_json() or {}
#     username = data.get('username')
#     password = data.get('password')
#     if not username or not password:
#         return jsonify({'error': 'Username and password required'}), 400
#
#     user = users_col().find_one({'_id': username})
#     if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password_hash']):
#         return jsonify({'error': 'Invalid credentials'}), 401
#
#     # generate JWT and hash it for storage
#     token = _generate_jwt(username)
#     token_hash = bcrypt.hashpw(token.encode('utf-8'), bcrypt.gensalt())
#
#     # upsert session document
#     sessions_col().update_one(
#         {'user_id': username},
#         {'$set': {
#             'token_hash': token_hash,
#             'created_at': datetime.utcnow()
#         }},
#         upsert=True
#     )
#
#     # set HttpOnly cookie
#     resp = make_response(jsonify({'message': 'Logged in'}))
#     resp.set_cookie(
#         'access_token',
#         token,
#         httponly=True,
#         secure=current_app.config.get('COOKIE_SECURE', False),
#         samesite='Strict',
#         max_age=12 * 3600  # match JWT expiry
#     )
#     return resp, 200
#
# # LOGOUT
# @auth_bp.route('/logout', methods=['POST'])
# def logout():
#     token = request.cookies.get('access_token')
#     if token:
#         # remove session record
#         sessions_col().delete_one({'user_id': _decode_jwt(token).get('sub')})
#     resp = make_response(jsonify({'message': 'Logged out'}))
#     # Clear the cookie
#     resp.set_cookie('access_token', '', expires=0)
#     return resp, 200
#
# # DECORATOR to protect your routes
# from functools import wraps
# def login_required(f):
#     @wraps(f)
#     def wrap(*args, **kwargs):
#         token = request.cookies.get('access_token')
#         if not token:
#             return jsonify({'error': 'Authentication required'}), 401
#
#         payload = _decode_jwt(token)
#         if not payload:
#             return jsonify({'error': 'Invalid or expired token'}), 401
#
#         # verify the token is the same one stored (token theft protection)
#         session = sessions_col().find_one({'user_id': payload['sub']})
#         if not session or not bcrypt.checkpw(token.encode('utf-8'), session['token_hash']):
#             return jsonify({'error': 'Session not found'}), 401
#
#         # you can attach user info to flask.g here if needed
#         return f(*args, **kwargs)
#     return wrap



import os
import bcrypt
import PyJWT as pyjwt
from datetime import datetime, timedelta, timezone
from flask import request, jsonify, make_response
from db.database import users, sessions
from util.backend.logger import log_auth_attempt

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
    Handles user login. Expects JSON with 'username' and 'password'.
    Issues a JWT and sets it as HttpOnly cookie if credentials valid.
    """
    data = request.get_json() or {}
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify(error="Username and password are required"), 400

    user = users.find_one({"username": username})
    if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password']):
        log_auth_attempt("login", username, False, "Invalid credentials")
        return jsonify(error="Invalid username or password"), 401

    # Generate JWT token
    exp = datetime.utcnow() + timedelta(hours=TOKEN_EXP_HOURS)
    payload = {"username": username, "exp": exp}
    token = pyjwt.encode(payload, SECRET_KEY, algorithm="HS256")
    # Store only a bcrypt-hash of the token in the sessions collection
    token_hash = bcrypt.hashpw(token.encode('utf-8'), bcrypt.gensalt())
    sessions.insert_one({
        "username": username,
        "token_hash": token_hash,
        "created_at": datetime.now(timezone.utc),
        "expires_at": exp
    })

    log_auth_attempt("login", username, True)

    # Set HttpOnly cookie
    resp = make_response(jsonify(message="Login successful"))
    resp.set_cookie(
        "auth_token", token,
        httponly=True,
        samesite='Strict'
    )
    return resp, 200


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
    resp.delete_cookie("auth_token")
    return resp, 200


def token_required(fn):
    """
    Decorator to protect routes: checks for valid JWT cookie and session.
    """
    from functools import wraps

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
        return fn(*args, **kwargs)

    return wrapper