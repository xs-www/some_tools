from datetime import datetime
from extensions import db


class User(db.Model):
    """User 表模型，表名为 `User`，username 为主键。"""
    __tablename__ = 'User'

    username = db.Column(db.Text, primary_key=True)
    hashed_password = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            'username': self.username,
            'hashed_password': self.hashed_password,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class UserDAO:
    """简单的 DAO（Mapper）封装：增删改查（不包含任何接口调用）。"""

    @staticmethod
    def create_user(username: str, hashed_password: str) -> User:
        user = User(username=username, hashed_password=hashed_password)
        try:
            db.session.add(user)
            db.session.commit()
            return user
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def get_user(username: str) -> User | None:
        return User.query.get(username)

    @staticmethod
    def update_password(username: str, new_hashed_password: str) -> User | None:
        user = User.query.get(username)
        if not user:
            return None
        try:
            user.hashed_password = new_hashed_password
            db.session.commit()
            return user
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def delete_user(username: str) -> bool:
        user = User.query.get(username)
        if not user:
            return False
        try:
            db.session.delete(user)
            db.session.commit()
            return True
        except Exception:
            db.session.rollback()
            raise
