from mapper import UserDAO
from werkzeug.security import check_password_hash, generate_password_hash
import importlib
from datetime import datetime, timedelta
from config import BaseConfig

# 尝试导入 PyJWT，若所导入模块不提供 encode/decode，则回退到 itsdangerous
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


class BaseService:
    """服务层基类。具体业务服务继承此类并实现所需方法。

    本文件不实现任何接口，仅提供结构和示例方法签名。
    """

    def __init__(self, db_session=None):
        self.db_session = db_session

    def get(self, *args, **kwargs):
        """示例：获取资源（未实现）"""
        raise NotImplementedError

    def create(self, *args, **kwargs):
        """示例：创建资源（未实现）"""
        raise NotImplementedError

    def update(self, *args, **kwargs):
        """示例：更新资源（未实现）"""
        raise NotImplementedError

    def delete(self, *args, **kwargs):
        """示例：删除资源（未实现）"""
        raise NotImplementedError


class AuthService(BaseService):
    """认证相关的业务服务（示例）。

    登录现在会返回 token，token 有效期基于配置（默认 15 天）。重复登录会刷新 token（返回新的 token）。
    """

    def _generate_token(self, username: str):
        secret = BaseConfig.JWT_SECRET
        if _jwt is not None:
            # 使用 PyJWT
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
            # 使用 itsdangerous 回退实现（基于过期秒数）
            expires_seconds = int(86400 * BaseConfig.JWT_EXPIRES_DAYS)
            s = _ifallback['Serializer'](secret, expires_in=expires_seconds)
            token = s.dumps({'sub': username})
            if isinstance(token, bytes):
                token = token.decode('utf-8')
            return token

    def login(self, username: str, password: str):
        """登录逻辑：返回用户 dict 或抛出 ValueError。成功时返回 (user_dict, token)。"""
        if not username or not password:
            raise ValueError('username and password required')

        user = UserDAO.get_user(username)
        if not user:
            raise ValueError('invalid credentials')

        if not check_password_hash(user.hashed_password, password):
            raise ValueError('invalid credentials')

        token = self._generate_token(username)
        result = user.to_dict()
        result['token'] = token
        return result

    def register(self, username: str, password: str):
        """注册逻辑：
        - 参数校验
        - 检查用户是否已存在
        - 生成密码哈希并创建用户
        返回用户 dict 或抛出 ValueError（400/409）
        """
        if not username or not password:
            raise ValueError('username and password required')

        existing = UserDAO.get_user(username)
        if existing:
            raise ValueError('user already exists')

        hashed = generate_password_hash(password)
        user = UserDAO.create_user(username, hashed)
        return user.to_dict()

    def check_username_available(self, username: str) -> bool:
        """检查用户名是否可用，username 为空抛出 ValueError，返回 True 表示可用。"""
        if not username:
            raise ValueError('username required')
        existing = UserDAO.get_user(username)
        return existing is None

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