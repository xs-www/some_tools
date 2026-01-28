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

    # 初始化第三方扩展（数据库、迁移、CORS 等）
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

    @app.route('/ui/home')
    def ui_home():
        return render_template('home.html')

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