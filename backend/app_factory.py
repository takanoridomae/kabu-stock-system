"""
アプリケーションファクトリー
"""
import os
from flask import Flask
from config.settings import get_config
from backend.middleware.error_handlers import register_error_handlers


def create_app(environment: str = None) -> Flask:
    """
    Flaskアプリケーションの作成と設定
    
    Args:
        environment: 環境名 ('development', 'production', 'testing')
        
    Returns:
        Flask: 設定済みのFlaskアプリケーション
    """
    # 設定の取得
    config = get_config(environment)
    
    # プロジェクトルートの取得
    project_root = os.path.dirname(os.path.dirname(__file__))
    
    # Flaskアプリケーションの初期化（絶対パスを使用）
    app = Flask(__name__, 
                template_folder=os.path.join(project_root, config.TEMPLATE_FOLDER),
                static_folder=os.path.join(project_root, config.STATIC_FOLDER))
    
    # 設定の適用
    app.config['SECRET_KEY'] = config.SECRET_KEY
    app.config['DEBUG'] = config.DEBUG
    
    # ブループリントの登録
    register_blueprints(app, config)
    
    # エラーハンドラーの登録
    register_error_handlers(app)
    
    return app


def register_blueprints(app: Flask, config) -> None:
    """ブループリントの登録"""
    # Webページルート
    from backend.routes.web import web
    app.register_blueprint(web)
    
    # APIルート
    from backend.routes.api import api
    app.register_blueprint(api, url_prefix=config.API_PREFIX)
