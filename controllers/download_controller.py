from controllers import bp_api
from flask import jsonify, request, send_file, after_this_request
import traceback
import os
import tempfile
from services.auth_service import AuthService
from services.download_service import DownloadService


@bp_api.route('/download', methods=['POST'])
def download_file():
    """旧示例接口：保持简单的 JSON 回显（兼容历史）。"""
    try:
        file_path = request.json.get('file_path')
        if not file_path or not os.path.exists(file_path):
            return jsonify({'error': 'file not found'}), 404

        # 这里可以添加权限检查等逻辑

        return jsonify({'file_path': file_path}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': 'internal error', 'detail': str(e)}), 500


@bp_api.route('/download_temp', methods=['GET', 'POST'])
def download_temp():
    """代理下载临时生成文件。

    - GET: 兼容老的 query string: /api/download_temp?path=...&delete=0
    - POST: 接收 JSON {'path':..., 'delete': '0'|'1'}，返回 application/pdf bytes for proxying
    """
    svc = DownloadService()
    try:
        if request.method == 'GET':
            file_path = request.args.get('path')
            delete_after = request.args.get('delete', '1') != '0'
        else:
            data = request.get_json(silent=True) or {}
            file_path = data.get('path')
            delete_after = str(data.get('delete', '1')) != '0'

        try:
            real_path = svc.resolve_temp_path(file_path)
        except FileNotFoundError:
            return jsonify({'error': 'file not found'}), 404
        except PermissionError:
            return jsonify({'error': 'access to path not allowed'}), 403

        # auth check (optional)
        auth_hdr = request.headers.get('Authorization', '')
        if auth_hdr.startswith('Bearer '):
            token = auth_hdr.split(' ', 1)[1].strip()
            try:
                username = AuthService().verify_token(token)
            except Exception:
                username = None
            if not username:
                return jsonify({'error': 'invalid token'}), 403

        download_name = os.path.basename(real_path)

        @after_this_request
        def _cleanup(response):
            if delete_after:
                try:
                    svc.cleanup(real_path)
                except Exception:
                    traceback.print_exc()
            return response

        if request.method == 'GET':
            return send_file(real_path, mimetype='application/pdf', as_attachment=True, download_name=download_name)
        else:
            # POST: return bytes so frontend can embed blob
            # Flask send_file also works but we want to return raw bytes with proper headers
            return send_file(real_path, mimetype='application/pdf', as_attachment=False, download_name=download_name)

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': 'internal error', 'detail': str(e)}), 500