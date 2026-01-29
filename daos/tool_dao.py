from extensions import db
#from mapper import Tool

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

class ToolDAO:
    @staticmethod
    def list_tools():
        return [t.to_dict() for t in Tool.query.order_by(Tool.id).all()]

    @staticmethod
    def get_tool_by_slug(slug):
        return Tool.query.filter_by(slug=slug).first()

    @staticmethod
    def create_tool(slug, title, description=None, route=None, icon=None, tags=None):
        t = Tool(slug=slug, title=title, description=description, route=route, icon=icon, tags=tags)
        db.session.add(t)
        db.session.commit()
        return t

    @staticmethod
    def update_tool_by_slug(slug, **kwargs):
        tool = Tool.query.filter_by(slug=slug).first()
        if not tool:
            return None
        new_slug = kwargs.pop('new_slug', None)
        if new_slug and new_slug != slug:
            if Tool.query.filter_by(slug=new_slug).first():
                raise ValueError('slug exists')
            tool.slug = new_slug
        for k in ('title','description','route','icon','tags'):
            if k in kwargs and kwargs[k] is not None:
                setattr(tool, k, kwargs[k])
        db.session.commit()
        return tool
