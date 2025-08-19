"""
アプリケーション設定管理
"""
import os
from typing import Dict, Any


class Config:
    """基本設定クラス"""
    
    # 基本設定
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-here')
    
    # データベース設定
    DATABASE_PATH = os.environ.get('DATABASE_PATH', 'database/kabu_system.db')
    DATABASE_SCHEMA_PATH = os.environ.get('DATABASE_SCHEMA_PATH', 'database/schema.sql')
    
    # Flask設定
    TEMPLATE_FOLDER = 'frontend/templates'
    STATIC_FOLDER = 'frontend/static'
    
    # API設定
    API_PREFIX = '/api'
    
    # エクスポート設定
    EXPORT_DIRECTORY = 'jsonfile'
    
    # デバッグ設定
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    # サーバー設定
    HOST = os.environ.get('FLASK_HOST', '0.0.0.0')
    PORT = int(os.environ.get('FLASK_PORT', 5000))


class DevelopmentConfig(Config):
    """開発環境設定"""
    DEBUG = True
    

class ProductionConfig(Config):
    """本番環境設定"""
    DEBUG = False
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    @classmethod
    def validate(cls) -> None:
        """本番環境設定の検証"""
        if not cls.SECRET_KEY:
            raise ValueError("本番環境ではSECRET_KEYの設定が必須です")


class TestConfig(Config):
    """テスト環境設定"""
    TESTING = True
    DATABASE_PATH = ':memory:'  # テスト用インメモリDB


# 環境別設定マッピング
config_map: Dict[str, Any] = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestConfig,
    'default': DevelopmentConfig
}


def get_config(environment: str = None) -> Config:
    """環境に応じた設定クラスを取得"""
    if environment is None:
        environment = os.environ.get('FLASK_ENV', 'default')
    
    config_class = config_map.get(environment, DevelopmentConfig)
    return config_class()
