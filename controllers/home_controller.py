from controllers import bp_ui
from flask import render_template, request
import traceback
from services.tool_service import ToolService

@bp_ui.route('/home', methods=['GET'])
def ui_home_page():
    """主页（示例）：动态展示工具列表。"""
    try:
        tools = ToolService().list_tools()
        tools_by_tab = {
            'stars': [],
            'tools': [],
            'others': [],
        }
        for tool in tools:
            tags = tool['tags'] or ''
            tagset = set([s.strip().lower() for s in tags.split(',') if s.strip()])
            for tab in tools_by_tab.keys():
                if tab in tagset:
                    tools_by_tab[tab].append(tool)

    except Exception:
        traceback.print_exc()
        tools = []
    return render_template('home.html', tools_by_tab=tools_by_tab), 200
