from datetime import datetime
from sqlalchemy import PrimaryKeyConstraint
from extensions import db

class User(db.Model):
    """User 表：使用整数 id 作为主键（自增），username 唯一。"""
    __tablename__ = 'User'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.Text, unique=True, nullable=False, index=True)
    hashed_password = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

class UserDAO:
    @staticmethod
    def create_user(username: str, hashed_password: str):
        user = User(username=username, hashed_password=hashed_password)
        try:
            db.session.add(user)
            db.session.commit()
            return user
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def get_user_by_username(username: str):
        return User.query.filter_by(username=username).first()

    @staticmethod
    def get_user_by_id(user_id: int):
        return User.query.get(user_id)

    @staticmethod
    def update_password(username: str, new_hashed_password: str):
        user = User.query.filter_by(username=username).first()
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
    def delete_user(username: str):
        user = User.query.filter_by(username=username).first()
        if not user:
            return False
        try:
            db.session.delete(user)
            db.session.commit()
            return True
        except Exception:
            db.session.rollback()
            raise
