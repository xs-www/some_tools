from flask import Blueprint, jsonify, request
import traceback
from service import AuthService

api_bp = Blueprint('api', __name__)


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