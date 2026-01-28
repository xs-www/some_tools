from flask import Blueprint, jsonify, request, render_template, send_file, after_this_request
import traceback
import tempfile
import shutil
import os
from werkzeug.utils import secure_filename
from service import AuthService, ConvertService
import traceback
from service import AuthService

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


# 全局错误处理钩子（示例）
@api_bp.app_errorhandler(404)
def handle_404(err):
    return jsonify({"error": "Not Found"}), 404