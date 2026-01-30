from flask import Flask, jsonify
import os
from sqlalchemy import inspect

from config import DevelopmentConfig
from extensions import db, migrate, cors

# try to import new controllers package
try:
    from controllers import register_blueprints
    #from controller import register_tool_routes as legacy_register_tool_routes
    has_new_controllers = True
except Exception:
    register_blueprints = None
    legacy_register_tool_routes = None
    has_new_controllers = False


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
    if register_blueprints:
        register_blueprints(app)
    else:
        try:
            from controllers import api_bp, ui_bp
            app.register_blueprint(api_bp, url_prefix='/api')
            app.register_blueprint(ui_bp)
        except Exception:
            pass

    # debug helper: list registered routes when in DEBUG
    try:
        if app.config.get('DEBUG'):
            @app.route('/__routes__')
            def _list_routes():
                rules = []
                for r in sorted(app.url_map.iter_rules(), key=lambda x: (str(x.rule), x.endpoint)):
                    rules.append({
                        'rule': str(r.rule),
                        'endpoint': r.endpoint,
                        'methods': sorted([m for m in r.methods if m not in ('HEAD','OPTIONS')])
                    })
                return jsonify({'routes': rules})
    except Exception:
        pass

    # if legacy register_tool_routes exists, call it to add dynamic routes
    try:
        if legacy_register_tool_routes:
            legacy_register_tool_routes(app.blueprints.get('ui') or app)
    except Exception:
        pass

    # 创建表（启动时检查并创建数据库表）
    try:
        with app.app_context():
            inspector = inspect(db.engine)
            # 检查 User 表是否存在；若不存在则创建所有表
            if not inspector.has_table('User'):
                db.create_all()
    except Exception:
        pass

    return app


if __name__ == '__main__':
    app = create_app()

    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=app.config.get('DEBUG', False))