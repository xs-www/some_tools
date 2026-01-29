from flask import jsonify, request, render_template
import traceback
from services.auth_service import AuthService
from controllers import bp_api, bp_ui

@bp_api.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get('username')
    password = data.get('password')
    auth_service = AuthService()
    try:
        res = auth_service.login(username, password)
        token = res.pop('token', None)
        return jsonify({'message': 'login successful', 'user': res, 'token': token}), 200
    except ValueError as ve:
        msg = str(ve)
        if 'required' in msg:
            return jsonify({'error': msg}), 400
        else:
            return jsonify({'error': msg}), 401
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': 'internal error', 'detail': str(e)}), 500


@bp_api.route('/register', methods=['POST'])
def register():
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


@bp_api.route('/check_username', methods=['POST'])
def check_username():
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


@bp_ui.route('/login', methods=['GET'])
def ui_login_page():
    # simple UI handler that renders the login page; front-end should call /api/login for submission
    return render_template('login.html')