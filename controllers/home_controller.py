from controllers import bp_ui
from flask import render_template, request
import traceback
from services.tool_service import ToolService

@bp_ui.route('/home', methods=['GET'])
def ui_home_page():
    """主页（示例）：动态展示工具列表。"""
    try:
        tools = ToolService().list_tools()
    except Exception:
        traceback.print_exc()
        tools = []
    return render_template('home.html', tools=tools)
