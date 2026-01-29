from flask import Blueprint, jsonify, request, render_template, send_file, after_this_request
import traceback
import tempfile
import shutil
import os
from werkzeug.utils import secure_filename
from service import AuthService, ConvertService
import traceback
from service import AuthService
from mapper import ToolDAO
from jinja2 import TemplateNotFound

api_bp = Blueprint('api', __name__)

# UI blueprint for non-API pages (upload/convert etc.)
ui_bp = Blueprint('ui', __name__)


@ui_bp.route('/convert', methods=['GET', 'POST'])
def convert_view():
    """控制层：处理上传、调用 ConvertService 并返回 PDF（预览或下载）。"""
    if request.method == 'GET':
        return render_template('convert.html')

    upload = request.files.get('file')
    if not upload:
        return 'No file uploaded', 400

    filename = secure_filename(upload.filename)
    if not filename:
        return 'Invalid filename', 400

    # 可选参数：pages=1-3,5 ; action=preview|download
    pages = request.form.get('pages') or None
    action = request.form.get('action') or 'download'

    tmpdir = tempfile.mkdtemp(prefix='docconvert_')
    input_path = os.path.join(tmpdir, filename)
    upload.save(input_path)

    service = ConvertService()
    try:
        pdf_path = service.convert_docx_to_pdf(input_path, tmpdir, pages=pages)
    except Exception as e:
        # 打印完整堆栈以便调试
        traceback.print_exc()
        shutil.rmtree(tmpdir, ignore_errors=True)
        return f'Conversion failed: {e}', 500

    pdf_filename = os.path.basename(pdf_path)

    @after_this_request
    def cleanup(response):
        try:
            shutil.rmtree(tmpdir)
        except Exception:
            pass
        return response

    as_attachment = True if action == 'download' else False
    return send_file(pdf_path, as_attachment=as_attachment, download_name=pdf_filename)


def register_tool_routes(bp):
    """Dynamically register UI routes based on Tool.route values.

    For each tool returned by ToolDAO.list_tools(), this function will:
    - normalize tool.route to start with '/'
    - attempt to render the template '<route>.html' (e.g. route '/convert/x' -> 'convert/x.html')
    - if template not found, redirect to the configured route

    This should be called after the UI blueprint is created and before the app is served.
    """
    try:
        tools = ToolDAO.list_tools()
    except Exception:
        tools = []

    for t in tools:
        try:
            route = t.get('route') or f"/convert/{t.get('slug')}"
            if not route.startswith('/'):
                route = '/' + route
            template_name = route.lstrip('/') + '.html'
            endpoint = f"tool_route_{t.get('id')}"

            def make_view(tool, route, template_name):
                def view():
                    try:
                        return render_template(template_name, tool=tool)
                    except TemplateNotFound:
                        from flask import redirect
                        return redirect(route)
                return view

            # avoid duplicate rule errors
            try:
                bp.add_url_rule(route, endpoint, make_view(t, route, template_name), methods=['GET'])
            except Exception:
                # ignore duplicate or invalid routes
                pass
        except Exception:
            # skip problematic tool entries
            traceback.print_exc()


@ui_bp.route('/convert/<slug>', methods=['GET'])
def convert_tool_page(slug):
    """通用入口：根据 Tool.slug 渲染对应的工具页面或重定向到 tool.route。

    规则：
    - 优先尝试渲染模板 `convert/<slug>.html`（如果存在），并把 tool 对象传入模板。
    - 若模板不存在，则读取 tool.route 字段并重定向到该路径（确保以 / 开头）。
    - 若找不到工具则返回 404 页面。
    """
    try:
        tool = ToolDAO.get_tool_by_slug(slug)
    except Exception:
        tool = None

    if not tool:
        # 尝试用下划线/中划线互换查找（兼容 slug 命名差异）
        try:
            tool = ToolDAO.get_tool_by_slug(slug.replace('_', '-'))
        except Exception:
            tool = None

    if not tool:
        return render_template('404.html'), 404 if '404.html' in [] else ("Tool not found", 404)

    t = tool.to_dict() if hasattr(tool, 'to_dict') else tool
    # 优先渲染模板 convert/<slug>.html
    tpl_name = f'convert/{slug}.html'
    try:
        return render_template(tpl_name, tool=t)
    except Exception:
        # 模板不存在或渲染失败，回退到重定向到 tool.route
        route = t.get('route') or f'/convert/{slug}'
        if not route.startswith('/'):
            route = '/' + route
        from flask import redirect
        return redirect(route)


# 在这里可以注册各个子蓝图或视图函数
@api_bp.route('/', methods=['GET'])
def index():
    """示例根接口（仅用于框架测试，可删除）"""
    return jsonify({"message": "API root - no endpoints implemented"})


@api_bp.route('/login', methods=['POST'])
def login():
    """控制层：只接收请求、调用 service 并处理结果与错误映射。业务逻辑在 `service.AuthService` 中实现。"""
    data = request.get_json(silent=True) or {}
    username = data.get('username')
    password = data.get('password')

    auth_service = AuthService()
    try:
        res = auth_service.login(username, password)
        # res 包含 user 字段和 token
        token = res.pop('token', None)
        return jsonify({'message': 'login successful', 'user': res, 'token': token}), 200
    except ValueError as ve:
        msg = str(ve)
        if 'required' in msg:
            return jsonify({'error': msg}), 400
        else:
            return jsonify({'error': msg}), 401
    except Exception as e:
        # 打印完整异常栈用于调试
        traceback.print_exc()
        # 在开发环境可以返回详情，默认返回通用信息
        return jsonify({'error': 'internal error', 'detail': str(e)}), 500


@api_bp.route('/register', methods=['POST'])
def register():
    """控制层：注册接口，业务逻辑在 service 层实现。"""
    data = request.get_json(silent=True) or {}
    username = data.get('username')
    password = data.get('password')

    auth_service = AuthService()
    try:
        user_dict = auth_service.register(username, password)
        return jsonify({'message': 'registered', 'user': user_dict}), 201
    except ValueError as ve:
        msg = str(ve)
        if 'required' in msg:
            return jsonify({'error': msg}), 400
        elif 'exists' in msg:
            return jsonify({'error': msg}), 409
        else:
            return jsonify({'error': msg}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': 'internal error', 'detail': str(e)}), 500


@api_bp.route('/check_username', methods=['POST'])
def check_username():
    """检查用户名是否可用（不包含复杂验证）。请求体：{"username": "..."} 返回 {"available": true/false}。"""
    data = request.get_json(silent=True) or {}
    username = data.get('username')

    auth_service = AuthService()
    try:
        available = auth_service.check_username_available(username)
        return jsonify({'available': available}), 200
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': 'internal error', 'detail': str(e)}), 500


# Admin: 管理员接口，用于创建/查看工具（简单实现：以用户名 'admin' 作为管理员）
@api_bp.route('/admin/tools', methods=['GET', 'POST'])
def admin_tools():
    auth = request.headers.get('Authorization') or ''
    token = None
    if auth.startswith('Bearer '):
        token = auth.split(' ', 1)[1].strip()

    auth_service = AuthService()
    username = None
    if token:
        username = auth_service.verify_token(token)

    # GET: 列出所有工具（公开）
    if request.method == 'GET':
        try:
            tools = ToolDAO.list_tools()
            return jsonify({'tools': tools}), 200
        except Exception as e:
            traceback.print_exc()
            return jsonify({'error': 'internal error', 'detail': str(e)}), 500

    # POST: 仅管理员创建工具
    if request.method == 'POST':
        if username != 'admin':
            return jsonify({'error': 'forbidden'}), 403
        data = request.get_json(silent=True) or {}
        slug = data.get('slug')
        title = data.get('title')
        if not slug or not title:
            return jsonify({'error': 'slug and title required'}), 400
        try:
            # check exists
            existing = ToolDAO.get_tool_by_slug(slug)
            if existing:
                return jsonify({'error': 'tool already exists'}), 409
            tool = ToolDAO.create_tool(slug=slug, title=title, description=data.get('description'), route=data.get('route'), icon=data.get('icon'), tags=data.get('tags'))
            return jsonify({'tool': tool.to_dict()}), 201
        except Exception as e:
            traceback.print_exc()
            return jsonify({'error': 'internal error', 'detail': str(e)}), 500


# PUT: 更新已存在的工具（根据 slug），仅管理员可用
@api_bp.route('/admin/tools/<slug>', methods=['PUT'])
def admin_update_tool(slug):
    auth = request.headers.get('Authorization') or ''
    token = None
    if auth.startswith('Bearer '):
        token = auth.split(' ', 1)[1].strip()

    auth_service = AuthService()
    username = None
    if token:
        username = auth_service.verify_token(token)

    if username != 'admin':
        return jsonify({'error': 'forbidden'}), 403

    data = request.get_json(silent=True) or {}
    try:
        updated = ToolDAO.update_tool_by_slug(slug, **{
            'new_slug': data.get('slug'),
            'title': data.get('title'),
            'description': data.get('description'),
            'route': data.get('route'),
            'icon': data.get('icon'),
            'tags': data.get('tags'),
        })
        if not updated:
            return jsonify({'error': 'tool not found'}), 404
        return jsonify({'tool': updated.to_dict()}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': 'internal error', 'detail': str(e)}), 500


# 全局错误处理钩子（示例）
@api_bp.app_errorhandler(404)
def handle_404(err):
    return jsonify({"error": "Not Found"}), 404