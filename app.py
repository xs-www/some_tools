from flask import Flask, render_template
import os
from sqlalchemy import inspect

from config import DevelopmentConfig
from extensions import db, migrate, cors
from controller import api_bp


def create_app(config_object=None):
    """创建并配置 Flask 应用（应用工厂模式）。
    不在此处实现任何具体路由或业务逻辑，仅完成框架级别初始化。
    """
    app = Flask(__name__)
    app.config.from_object(config_object or DevelopmentConfig)

    # 初始化第三方扩展（数据库、迁移、CORS 等)
    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app)

    # 注册蓝图（控制器层）
    app.register_blueprint(api_bp, url_prefix='/api')
    # 注册 UI 蓝图（非 /api 路由，如 /convert）
    try:
        from controller import ui_bp
        app.register_blueprint(ui_bp)
    except Exception:
        pass

    # 顶级 UI 路由
    @app.route('/')
    def root_index():
        return render_template('index.html')

    @app.route('/login')
    def login_page():
        return render_template('login.html')

    @app.route('/ui/home')
    def ui_home():
        # 动态从数据库读取工具，按标签分配到对应 tab。若工具未包含已知 tab 标签，则放入 'others'
        try:
            from mapper import ToolDAO
            tools = ToolDAO.list_tools()
        except Exception:
            tools = []

        tabs = {'stars': [], 'tools': [], 'others': [], 'settings': []}
        known_tabs = set(tabs.keys())
        for t in tools:
            tags_str = (t.get('tags') or '') if isinstance(t, dict) else ''
            tag_list = [x.strip().lower() for x in tags_str.split(',') if x.strip()]
            placed = False
            for tag in tag_list:
                if tag in known_tabs:
                    tabs[tag].append(t)
                    placed = True
                    break
            if not placed:
                tabs['others'].append(t)

        return render_template('home.html', tools_by_tab=tabs, auto_script='scripts/home.js')

    @app.route('/ui/admin')
    def ui_admin():
        return render_template('admin.html', auto_script='admin.js')

    @app.route('/convert/<slug>')
    def convert_tool_page(slug):
        try:
            from mapper import ToolDAO
            tool = ToolDAO.get_tool_by_slug(slug)
        except Exception:
            tool = None

        if not tool:
            try:
                from mapper import ToolDAO
                tool = ToolDAO.get_tool_by_slug(slug.replace('_', '-'))
            except Exception:
                tool = None

        if not tool:
            return render_template('404.html'), 404 if '404.html' in [] else ("Tool not found", 404)

        t = tool.to_dict() if hasattr(tool, 'to_dict') else tool
        tpl_name = f'convert/{slug}.html'
        try:
            # if template exists, render and include corresponding script under static/scripts/convert/<slug>.js
            return render_template(tpl_name, tool=t, auto_script=f'scripts/convert/{slug}.js')
        except Exception:
            # fallback to redirect
            route = t.get('route') or f'/convert/{slug}'
            if not route.startswith('/'):
                route = '/' + route
            from flask import redirect
            return redirect(route)

    # 启动前检查并创建数据库表（如果尚未创建）
    try:
        with app.app_context():
            inspector = inspect(db.engine)
            # 检查 User 表是否存在；若不存在则创建所有表
            if not inspector.has_table('User'):
                print('User table not found, creating database tables...')
                db.create_all()
                print('Database tables created')
            else:
                print('Database already initialized')
    except Exception as e:
        print('Failed to inspect/create database tables:', e)

    return app


if __name__ == '__main__':
    app = create_app()

    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=app.config.get('DEBUG', False))