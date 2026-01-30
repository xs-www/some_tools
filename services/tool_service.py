from daos.tool_dao import ToolDAO

class ToolService:
    def list_tools(self):
        return ToolDAO.list_tools()

    def get_tool(self, slug_or_id):
        return ToolDAO.get_tool_by_slug(slug_or_id)

    def create_tool(self, **kwargs):
        return ToolDAO.create_tool(**kwargs)

    def update_tool(self, slug, **kwargs):
        return ToolDAO.update_tool_by_slug(slug, **kwargs)
