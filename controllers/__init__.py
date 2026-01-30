from flask import Blueprint
import importlib
from pathlib import Path
import logging
import re

# central blueprints that modules should import and use
bp_api = Blueprint('api', __name__)
bp_ui = Blueprint('ui', __name__)

def _find_decorated_view_names(pkg_dir: Path):

    """扫描 controllers 目录下每个模块，找出用 bp_api.route / bp_ui.route 装饰的视图函数名。

    返回结构: { 'api': {name: [filenames...]}, 'ui': {name: [filenames...]}}
    """
    results = {'api': {}, 'ui': {}}
    route_decorators = {
        'api': re.compile(r"@\s*bp_api\.route\b"),
        'ui': re.compile(r"@\s*bp_ui\.route\b"),
    }

    for p in pkg_dir.iterdir():
        if not (p.is_file() and p.suffix == '.py' and p.name != '__init__.py' and not p.name.startswith('_')):
            continue
        text = p.read_text(encoding='utf-8')
        lines = text.splitlines()
        for i, line in enumerate(lines):
            for key, patt in route_decorators.items():
                if patt.search(line):
                    # search forward up to next 6 lines for a def statement
                    name = None
                    for j in range(i + 1, min(i + 7, len(lines))):
                        m = re.match(r"\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", lines[j])
                        if m:
                            name = m.group(1)
                            break
                    if not name:
                        # try a bit backward in case decorator cluster above def
                        for j in range(max(0, i - 4), i):
                            m = re.match(r"\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", lines[j])
                            if m:
                                name = m.group(1)
                                break
                    if name:
                        results[key].setdefault(name, []).append(str(p))
    return results


# central place to register and expose blueprints from modules
def register_blueprints(app):
    """Import controller modules (so they bind views to the central blueprints) and register them on the app.

    Modules should import `bp_api` / `bp_ui` from this package and use them for route definitions,
    e.g. `from controllers import bp_api` then `@bp_api.route('/login')`.
    """
    # dynamically discover controller modules in this package directory
    pkg_dir = Path(__file__).parent
    module_names = sorted([
        p.stem for p in pkg_dir.iterdir()
        if p.is_file() and p.suffix == '.py' and p.name != '__init__.py' and not p.name.startswith('_')
    ])

    # import discovered controller modules so they bind routes to bp_api/bp_ui
    for name in module_names:
        mod_name = f"{__name__}.{name}"
        try:
            importlib.import_module(mod_name)
            logging.getLogger(__name__).info("Imported controller module: %s", mod_name)
        except Exception:
            logging.getLogger(__name__).exception("Failed to import controller module: %s", mod_name)

    # 检测视图函数名重复，避免 Flask 在注册 blueprint 时抛出覆盖 endpoint 的 AssertionError
    try:
        dup_info = _find_decorated_view_names(pkg_dir)
        dup_messages = []
        for scope in ('api', 'ui'):
            for name, files in dup_info[scope].items():
                if len(files) > 1:
                    dup_messages.append(f"{scope}: view function '{name}' defined in multiple files: {files}")
        if dup_messages:
            msg = ("Detected duplicate view function names for central blueprints.\n"
                   + "Rename duplicated functions or explicitly set unique endpoint names in @bp_api.route(..., endpoint='...') / @bp_ui.route(..., endpoint='...').\n"
                   + "Conflicts:\n" + "\n".join(dup_messages))
            logging.getLogger(__name__).error(msg)
            raise RuntimeError(msg)
    except Exception as e:
        # 如果扫描过程本身出错，记录但不阻止后续尝试（保守处理）
        logging.getLogger(__name__).exception("Error while scanning controller view names: %s", e)

    # register central blueprints on the app (do this after importing modules so routes are bound)
    try:
        app.register_blueprint(bp_api, url_prefix='/api')
    except AssertionError:
        # 明确捕获 endpoint 覆盖的情形，记录详情并重新抛出以便上层可见
        logging.getLogger(__name__).exception("Failed to register bp_api: endpoint conflict (duplicate view names)")
        raise
    except Exception:
        logging.getLogger(__name__).exception("Failed to register bp_api")
    try:
        app.register_blueprint(bp_ui, url_prefix='/ui')
    except AssertionError:
        logging.getLogger(__name__).exception("Failed to register bp_ui: endpoint conflict (duplicate view names)")
        raise
    except Exception:
        logging.getLogger(__name__).exception("Failed to register bp_ui")
