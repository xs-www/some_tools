from daos.user_dao import UserDAO
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta
from config import BaseConfig
import importlib

_jwt = None
try:
    _jwt = importlib.import_module('jwt')
    if not (hasattr(_jwt, 'encode') and hasattr(_jwt, 'decode')):
        _jwt = None
except Exception:
    _jwt = None

_ifallback = None
if _jwt is None:
    from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired
    _ifallback = {
        'Serializer': Serializer,
        'BadSignature': BadSignature,
        'SignatureExpired': SignatureExpired,
    }

class AuthService:
    def _generate_token(self, username: str):
        secret = BaseConfig.JWT_SECRET
        if _jwt is not None:
            expires = datetime.utcnow() + timedelta(days=BaseConfig.JWT_EXPIRES_DAYS)
            payload = {
                'sub': username,
                'iat': datetime.utcnow().timestamp(),
                'exp': expires.timestamp(),
            }
            token = _jwt.encode(payload, secret, algorithm='HS256')
            if isinstance(token, bytes):
                token = token.decode('utf-8')
            return token
        else:
            expires_seconds = int(86400 * BaseConfig.JWT_EXPIRES_DAYS)
            s = _ifallback['Serializer'](secret, expires_in=expires_seconds)
            token = s.dumps({'sub': username})
            if isinstance(token, bytes):
                token = token.decode('utf-8')
            return token

    def login(self, username: str, password: str):
        if not username or not password:
            raise ValueError('username and password required')
        user = UserDAO.get_user_by_username(username)
        if not user:
            raise ValueError('invalid credentials')
        if not check_password_hash(user.hashed_password, password):
            raise ValueError('invalid credentials')
        token = self._generate_token(username)
        result = user.to_dict()
        result['token'] = token
        return result

    def register(self, username: str, password: str):
        if not username or not password:
            raise ValueError('username and password required')
        existing = UserDAO.get_user_by_username(username)
        if existing:
            raise ValueError('user already exists')
        hashed = generate_password_hash(password)
        user = UserDAO.create_user(username, hashed)
        return user.to_dict()

    def verify_token(self, token: str):
        secret = BaseConfig.JWT_SECRET
        if _jwt is not None:
            try:
                payload = _jwt.decode(token, secret, algorithms=['HS256'])
                return payload.get('sub')
            except Exception:
                return None
        else:
            try:
                s = _ifallback['Serializer'](secret)
                data = s.loads(token)
                return data.get('sub')
            except _ifallback['SignatureExpired']:
                return None
            except Exception:
                return None

    def check_username_available(self, username: str):
        if not username:
            raise ValueError('username required')
        existing = UserDAO.get_user_by_username(username)
        return existing is None
