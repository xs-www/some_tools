from datetime import datetime
from extensions import db
from sqlalchemy import PrimaryKeyConstraint


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


class Tool(db.Model):
    """小工具表：由开发者维护，包含 slug/title/description/route/icon/tags 等字段。"""
    __tablename__ = 'Tool'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    slug = db.Column(db.Text, unique=True, nullable=False)
    title = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    route = db.Column(db.Text)
    icon = db.Column(db.Text)
    tags = db.Column(db.Text)

    def to_dict(self):
        return {
            'id': self.id,
            'slug': self.slug,
            'title': self.title,
            'description': self.description,
            'route': self.route,
            'icon': self.icon,
            'tags': self.tags,
        }


class Favorite(db.Model):
    """收藏表：user_id 与 tool_id 为联合主键，记录用户对工具的收藏时间。"""
    __tablename__ = 'Favorite'
    user_id = db.Column(db.Integer, nullable=False)
    tool_id = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint('user_id', 'tool_id', name='pk_favorite_user_tool'),
    )

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'tool_id': self.tool_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class UserDAO:
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
    def get_user_by_username(username: str) -> User | None:
        return User.query.filter_by(username=username).first()

    @staticmethod
    def get_user_by_id(user_id: int) -> User | None:
        return User.query.get(user_id)

    @staticmethod
    def update_password(username: str, new_hashed_password: str) -> User | None:
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
    def delete_user(username: str) -> bool:
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


class ToolDAO:
    @staticmethod
    def create_tool(slug: str, title: str, description: str = None, route: str = None, icon: str = None, tags: str = None) -> Tool:
        tool = Tool(slug=slug, title=title, description=description, route=route, icon=icon, tags=tags)
        try:
            db.session.add(tool)
            db.session.commit()
            return tool
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def get_tool_by_id(tool_id: int) -> Tool | None:
        return Tool.query.get(tool_id)

    @staticmethod
    def get_tool_by_slug(slug: str) -> Tool | None:
        return Tool.query.filter_by(slug=slug).first()

    @staticmethod
    def list_tools() -> list:
        return [t.to_dict() for t in Tool.query.order_by(Tool.id).all()]

    @staticmethod
    def delete_tool(tool_id: int) -> bool:
        tool = Tool.query.get(tool_id)
        if not tool:
            return False
        try:
            db.session.delete(tool)
            db.session.commit()
            return True
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def update_tool_by_slug(slug: str, **kwargs) -> Tool | None:
        """Update fields of a tool identified by slug. Returns the updated Tool or None if not found."""
        tool = Tool.query.filter_by(slug=slug).first()
        if not tool:
            return None
        try:
            # support renaming via new_slug kwarg to avoid conflict with positional slug
            new_slug = kwargs.pop('new_slug', None)
            if new_slug and new_slug != slug:
                # check uniqueness
                if Tool.query.filter_by(slug=new_slug).first():
                    raise ValueError('slug already exists')
                tool.slug = new_slug
            # only allow updating known columns
            for key in ('title', 'description', 'route', 'icon', 'tags'):
                if key in kwargs and kwargs[key] is not None:
                    setattr(tool, key, kwargs[key])
            db.session.commit()
            return tool
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def update_tool_by_id(tool_id: int, **kwargs) -> Tool | None:
        tool = Tool.query.get(tool_id)
        if not tool:
            return None
        try:
            for key in ('slug', 'title', 'description', 'route', 'icon', 'tags'):
                if key in kwargs and kwargs[key] is not None:
                    setattr(tool, key, kwargs[key])
            db.session.commit()
            return tool
        except Exception:
            db.session.rollback()
            raise


class FavoriteDAO:
    @staticmethod
    def add_favorite(user_id: int, tool_id: int) -> Favorite:
        fav = Favorite(user_id=user_id, tool_id=tool_id)
        try:
            db.session.add(fav)
            db.session.commit()
            return fav
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def remove_favorite(user_id: int, tool_id: int) -> bool:
        fav = Favorite.query.get((user_id, tool_id))
        if not fav:
            return False
        try:
            db.session.delete(fav)
            db.session.commit()
            return True
        except Exception:
            db.session.rollback()
            raise

    @staticmethod
    def list_favorites_for_user(user_id: int) -> list:
        rows = Favorite.query.filter_by(user_id=user_id).order_by(Favorite.created_at.desc()).all()
        return [r.to_dict() for r in rows]


# Helper: ensure SQLite user id sequence starts from at least 1000001
def ensure_user_id_sequence(engine, min_start=1000001):
    """If using SQLite, set sqlite_sequence for table User so next id >= min_start.

    Usage: with app.app_context(): ensure_user_id_sequence(db.engine)
    """
    try:
        # Only applicable for SQLite
        if 'sqlite' not in str(engine.url):
            return
        conn = engine.connect()
        res = conn.execute("SELECT seq FROM sqlite_sequence WHERE name='User'")
        row = res.fetchone()
        if row is None:
            # no sequence row yet; insert one with seq = min_start - 1
            conn.execute(f"INSERT INTO sqlite_sequence(name,seq) VALUES ('User', {min_start-1})")
        else:
            seq = int(row[0])
            if seq < (min_start-1):
                conn.execute(f"UPDATE sqlite_sequence SET seq={min_start-1} WHERE name='User'")
        conn.close()
    except Exception:
        # ignore failures; user can set sequence manually if needed
        pass
