from daos.favorite_dao import UserFavoriteDAO

class UserFavoriteService:

    @staticmethod
    def get_favorite_count(tool_id: int):
        return UserFavoriteDAO.get_favorite_count(tool_id)

    @staticmethod
    def get_user_favorites(user_id: int):
        return UserFavoriteDAO.get_user_favorites(user_id)

    @staticmethod
    def create_favorite(user_id: int, tool_id: int):
        return UserFavoriteDAO.add_favorite(user_id, tool_id)

    @staticmethod
    def delete_favorite(user_id: int, tool_id: int):
        return UserFavoriteDAO.remove_favorite(user_id, tool_id)