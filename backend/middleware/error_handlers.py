"""
エラーハンドラー
"""
from flask import jsonify, request


def register_error_handlers(app):
    """エラーハンドラーの登録"""
    
    @app.errorhandler(404)
    def not_found(error):
        """404エラーハンドラー"""
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': 'エンドポイントが見つかりません',
                'code': 404
            }), 404
        return "ページが見つかりません", 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """500エラーハンドラー"""
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': 'サーバー内部エラーが発生しました',
                'code': 500
            }), 500
        return "サーバーエラーが発生しました", 500
    
    @app.errorhandler(400)
    def bad_request(error):
        """400エラーハンドラー"""
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': '不正なリクエストです',
                'code': 400
            }), 400
        return "不正なリクエストです", 400
