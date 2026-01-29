from controllers import bp_api, bp_ui
from flask import jsonify, request
import traceback
from services.auth_service import AuthService
from services.tool_service import ToolService
from daos.tool_dao import ToolDAO

def admin_page_legacy():
    """备用的管理员页面函数（不再作为路由注册，避免与新的 admin_controller 冲突）。"""
    return "Admin Page - legacy", 200

@bp_api.route('/tools', methods=['GET'])
def list_tools():
    """返回所有工具的简洁列表。支持 query param tag（逗号分隔）进行过滤。"""
    q_tag = request.args.get('tag')
    try:
        tools = ToolService().list_tools()
        if q_tag:
            wanted = set([t.strip().lower() for t in q_tag.split(',') if t.strip()])
            out = []
            for t in tools:
                tags = [(t.get('tags') or '').lower()]
                tagset = set([s.strip() for s in (t.get('tags') or '').split(',') if s.strip()])
                if tagset & wanted:
                    out.append(t)
            tools = out
        return jsonify({'tools': tools}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': 'internal error', 'detail': str(e)}), 500

@bp_api.route('/tools/<ident>', methods=['GET'])
def get_tool(ident):
    """通过 slug 或 id 获取工具详细信息。"""
    try:
        tool = None
        if ident.isdigit():
            tool = ToolDAO.get_tool_by_id(int(ident))
        if not tool:
            tool = ToolDAO.get_tool_by_slug(ident)
        if not tool:
            return jsonify({'error': 'not found'}), 404
        return jsonify({'tool': tool.to_dict()}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': 'internal error', 'detail': str(e)}), 500


@bp_api.route('/tools', methods=['POST'])
def create_tool():
    """创建工具（管理员）。"""
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
    slug = data.get('slug')
    title = data.get('title')
    if not slug or not title:
        return jsonify({'error': 'slug and title required'}), 400
    try:
        existing = ToolDAO.get_tool_by_slug(slug)
        if existing:
            return jsonify({'error': 'tool already exists'}), 409
        tool = ToolDAO.create_tool(slug=slug, title=title, description=data.get('description'), route=data.get('route'), icon=data.get('icon'), tags=data.get('tags'))
        return jsonify({'tool': tool.to_dict()}), 201
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': 'internal error', 'detail': str(e)}), 500


@bp_api.route('/tools/update_tools', methods=['POST'])
def update_tools():
    """使用 POST 更新工具（管理员）。请求体需包含 'slug' 指定要更新的工具，其他字段为要修改的值。"""
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
    slug = data.get('slug')
    if not slug:
        return jsonify({'error': 'slug required to identify tool'}), 400
    try:
        updated = ToolDAO.update_tool_by_slug(slug, **{
            'new_slug': data.get('slug_new') or data.get('new_slug') or data.get('newSlug') or data.get('slug'),
            'title': data.get('title'),
            'description': data.get('description'),
            'route': data.get('route'),
            'icon': data.get('icon'),
            'tags': data.get('tags'),
        })
        if not updated:
            return jsonify({'error': 'not found'}), 404
        return jsonify({'tool': updated.to_dict()}), 200
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 409
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': 'internal error', 'detail': str(e)}), 500


@bp_api.route('/tools/delete_tool', methods=['POST'])
def delete_tool():
    """使用 POST 删除工具（管理员）。请求体包含 'id' 或 'slug'。"""
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
    ident = data.get('id') or data.get('slug')
    if not ident:
        return jsonify({'error': 'id or slug required'}), 400
    try:
        if isinstance(ident, int) or (isinstance(ident, str) and str(ident).isdigit()):
            ok = ToolDAO.delete_tool(int(ident))
        else:
            tool = ToolDAO.get_tool_by_slug(ident)
            if not tool:
                return jsonify({'error': 'not found'}), 404
            ok = ToolDAO.delete_tool(tool.id)
        if not ok:
            return jsonify({'error': 'not found'}), 404
        return jsonify({'deleted': True}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': 'internal error', 'detail': str(e)}), 500
