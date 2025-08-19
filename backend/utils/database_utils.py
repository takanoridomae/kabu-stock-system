"""
データベース関連ユーティリティ
"""
import os
import sqlite3
from typing import Optional
from config.settings import get_config


def get_db_connection(db_path: Optional[str] = None):
    """データベース接続を取得"""
    if db_path is None:
        config = get_config()
        db_path = config.DATABASE_PATH
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # 辞書形式でアクセス可能
    return conn


def init_database(db_path: Optional[str] = None, schema_path: Optional[str] = None) -> bool:
    """
    データベースの初期化
    
    Args:
        db_path: データベースファイルパス
        schema_path: スキーマファイルパス
        
    Returns:
        bool: 初期化成功の可否
    """
    config = get_config()
    
    if db_path is None:
        db_path = config.DATABASE_PATH
    if schema_path is None:
        schema_path = config.DATABASE_SCHEMA_PATH
    
    # データベースディレクトリの作成
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)
    
    # スキーマファイルの存在確認
    if not os.path.exists(schema_path):
        print(f"警告: {schema_path}が見つかりません。")
        return False
    
    try:
        # スキーマの読み込み
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = f.read()
        
        # データベースの初期化
        conn = get_db_connection(db_path)
        # スキーマを実行（IF NOT EXISTSにより既存テーブルがあっても安全）
        conn.executescript(schema)
        conn.close()
        
        print("データベースが正常に初期化されました。")
        return True
        
    except sqlite3.Error as e:
        print(f"データベース初期化エラー: {e}")
        print("既存のデータベースファイルとの競合が発生している可能性があります。")
        return False
    except Exception as e:
        print(f"予期しないエラー: {e}")
        return False


def check_database_health(db_path: Optional[str] = None) -> bool:
    """
    データベースの健全性チェック
    
    Args:
        db_path: データベースファイルパス
        
    Returns:
        bool: データベースが正常かどうか
    """
    if db_path is None:
        config = get_config()
        db_path = config.DATABASE_PATH
    
    try:
        conn = get_db_connection(db_path)
        
        # 基本テーブルの存在確認
        cursor = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name IN ('companies', 'stock_prices', 'financial_metrics')
        """)
        
        tables = [row[0] for row in cursor.fetchall()]
        required_tables = ['companies', 'stock_prices', 'financial_metrics']
        
        conn.close()
        
        # 必要なテーブルがすべて存在するかチェック
        missing_tables = set(required_tables) - set(tables)
        if missing_tables:
            print(f"不足しているテーブル: {missing_tables}")
            return False
        
        return True
        
    except Exception as e:
        print(f"データベース健全性チェックエラー: {e}")
        return False
