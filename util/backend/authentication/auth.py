# util/backend/authentication/auth.py

from flask import Blueprint, request, jsonify, make_response, current_app
from pymongo.errors import DuplicateKeyError
import bcrypt
import jwt
from datetime import datetime, timedelta

# adjust import path as needed
from db.database import get_db

auth_bp = Blueprint('auth', __name__)

# Helper to fetch collections
def users_col():
    return get_db().users

def sessions_col():
    return get_db().sessions

# Utility: generate and sign a JWT
def _generate_jwt(user_id):
    payload = {
        'sub': str(user_id),
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(hours=12)
    }
    token = jwt.encode(payload, current_app.config['JWT_SECRET'], algorithm='HS256')
    return token

# Utility: decode and verify a JWT
def _decode_jwt(token):
    try:
        return jwt.decode(token, current_app.config['JWT_SECRET'], algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

# REGISTER
@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400

    # hash password with bcrypt
    pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    try:
        users_col().insert_one({
            '_id': username,
            'password_hash': pw_hash
        })
    except DuplicateKeyError:
        return jsonify({'error': 'Username already exists'}), 409

    return jsonify({'message': 'User registered'}), 201

# LOGIN
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400

    user = users_col().find_one({'_id': username})
    if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password_hash']):
        return jsonify({'error': 'Invalid credentials'}), 401

    # generate JWT and hash it for storage
    token = _generate_jwt(username)
    token_hash = bcrypt.hashpw(token.encode('utf-8'), bcrypt.gensalt())

    # upsert session document
    sessions_col().update_one(
        {'user_id': username},
        {'$set': {
            'token_hash': token_hash,
            'created_at': datetime.utcnow()
        }},
        upsert=True
    )

    # set HttpOnly cookie
    resp = make_response(jsonify({'message': 'Logged in'}))
    resp.set_cookie(
        'access_token',
        token,
        httponly=True,
        secure=current_app.config.get('COOKIE_SECURE', False),
        samesite='Strict',
        max_age=12 * 3600  # match JWT expiry
    )
    return resp, 200

# LOGOUT
@auth_bp.route('/logout', methods=['POST'])
def logout():
    token = request.cookies.get('access_token')
    if token:
        # remove session record
        sessions_col().delete_one({'user_id': _decode_jwt(token).get('sub')})
    resp = make_response(jsonify({'message': 'Logged out'}))
    # Clear the cookie
    resp.set_cookie('access_token', '', expires=0)
    return resp, 200

# DECORATOR to protect your routes
from functools import wraps
def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        token = request.cookies.get('access_token')
        if not token:
            return jsonify({'error': 'Authentication required'}), 401

        payload = _decode_jwt(token)
        if not payload:
            return jsonify({'error': 'Invalid or expired token'}), 401

        # verify the token is the same one stored (token theft protection)
        session = sessions_col().find_one({'user_id': payload['sub']})
        if not session or not bcrypt.checkpw(token.encode('utf-8'), session['token_hash']):
            return jsonify({'error': 'Session not found'}), 401

        # you can attach user info to flask.g here if needed
        return f(*args, **kwargs)
    return wrap
