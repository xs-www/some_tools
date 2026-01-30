from datetime import datetime
from sqlalchemy import PrimaryKeyConstraint
from extensions import db

class UserFavorite(db.Model):
    """UserFavorite 表：使用整数 id 作为主键（自增），username 唯一。"""
    __tablename__ = 'UserFavorite'

    user_id = db.Column(db.Integer, primary_key=True)
    tool_id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'tool_id': self.tool_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class UserFavoriteDAO:

    @staticmethod
    def get_favorite_count(tool_id: int):
        return UserFavorite.query.filter_by(tool_id=tool_id).count()

    @staticmethod
    def get_user_favorites(user_id: int):
        return UserFavorite.query.filter_by(user_id=user_id).all()
    
    @staticmethod
    def add_favorite(user_id: int, tool_id: int):
        favorite = UserFavorite(user_id=user_id, tool_id=tool_id)
        try:
            db.session.add(favorite)
            db.session.commit()
            return favorite
        except Exception:
            db.session.rollback()
            raise
    
    @staticmethod
    def remove_favorite(user_id: int, tool_id: int):
        favorite = UserFavorite.query.filter_by(user_id=user_id, tool_id=tool_id).first()
        if not favorite:
            return False
        try:
            db.session.delete(favorite)
            db.session.commit()
            return True
        except Exception:
            db.session.rollback()
            raise