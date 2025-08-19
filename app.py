"""
株式検索システム - メインアプリケーション
"""
import os
import sys

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(__file__))

# アプリケーションファクトリーのインポート
from backend.app_factory import create_app
from backend.utils.database_utils import init_database
from config.settings import get_config

# アプリケーションの作成
app = create_app()

if __name__ == '__main__':
    # 設定の取得
    config = get_config()
    
    # データベースの初期化
    init_database()
    
    # 開発サーバーの起動
    app.run(debug=config.DEBUG, host=config.HOST, port=config.PORT)
