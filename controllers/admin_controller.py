from controllers import bp_api, bp_ui
from flask import jsonify, request, render_template
import traceback
from services.tool_service import ToolService

@bp_ui.route('/admin', methods=['GET'])
def admin_page():
    """管理员页面入口（示例）。"""
    token = request.headers.get('Authorization', '')
    # 打印token
    print("Admin token:", token)
    return render_template('admin.html'), 200

@bp_api.route('/admin/tools', methods=['GET', 'POST'])
def admin_tools():
    # GET: 列表，POST: 创建
    try:
        if request.method == 'GET':
            tools = ToolService().list_tools()
            return jsonify({'tools': tools}), 200

        if request.method == 'POST':
            data = request.get_json(silent=True) or {}
            slug = data.get('slug')
            title = data.get('title')
            if not slug or not title:
                return jsonify({'error': 'slug and title required'}), 400
            try:
                tool = ToolService().create_tool(slug=slug, title=title, description=data.get('description'), route=data.get('route'), icon=data.get('icon'), tags=data.get('tags'))
                return jsonify({'tool': tool.to_dict()}), 201
            except Exception as e:
                traceback.print_exc()
                return jsonify({'error': 'internal error', 'detail': str(e)}), 500
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': 'internal error', 'detail': str(e)}), 500


@bp_api.route('/admin/update_tools', methods=['POST'])
def admin_update_tools():
    try:
        data = request.get_json(silent=True) or {}
        ident = data.get('id') or data.get('slug')
        if not ident:
            return jsonify({'error': 'id or slug required to identify tool'}), 400

        # resolve slug if id provided
        slug_to_use = None
        if isinstance(ident, int) or (isinstance(ident, str) and str(ident).isdigit()):
            tool = ToolService().get_tool(int(ident))
            if not tool:
                return jsonify({'error': 'tool not found'}), 404
            slug_to_use = tool['slug'] if isinstance(tool, dict) else tool.slug
        else:
            slug_to_use = ident

        updated = ToolService().update_tool(slug_to_use, **{
            'new_slug': data.get('slug_new') or data.get('new_slug') or data.get('newSlug') or None,
            'title': data.get('title'),
            'description': data.get('description'),
            'route': data.get('route'),
            'icon': data.get('icon'),
            'tags': data.get('tags'),
        })
        if not updated:
            return jsonify({'error': 'tool not found'}), 404
        # updated may be a model; try to serialize
        try:
            return jsonify({'tool': updated.to_dict()}), 200
        except Exception:
            return jsonify({'tool': updated}), 200
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 409
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': 'internal error', 'detail': str(e)}), 500


@bp_api.route('/admin/delete_tool', methods=['POST'])
def admin_delete_tool():
    try:
        data = request.get_json(silent=True) or {}
        ident = data.get('id') or data.get('slug')
        if not ident:
            return jsonify({'error': 'id or slug required'}), 400

        if isinstance(ident, int) or (isinstance(ident, str) and str(ident).isdigit()):
            ok = ToolService().delete_tool(int(ident))
        else:
            ok = ToolService().delete_tool(ident)
        if not ok:
            return jsonify({'error': 'not found'}), 404
        return jsonify({'deleted': True}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': 'internal error', 'detail': str(e)}), 500
