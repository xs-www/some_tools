from controllers import bp_api
from flask import jsonify, request
import traceback
from services.favorite_service import UserFavoriteService

@bp_api.route('/favorites/<int:user_id>', methods=['GET'])
def get_user_favorites(user_id):
    try:
        favorites = UserFavoriteService.get_user_favorites(user_id)
        return jsonify([f.to_dict() for f in favorites])
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@bp_api.route('/favorites', methods=['POST'])
def add_favorite():
    data = request.get_json(silent=True) or {}
    user_id = data.get('user_id')
    tool_id = data.get('tool_id')
    try:
        favorite = UserFavoriteService.create_favorite(user_id, tool_id)
        return jsonify(favorite.to_dict()), 201
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500