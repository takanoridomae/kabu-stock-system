"""
J-Quants APIトークン管理ユーティリティ
リフレッシュトークンの保存、有効期限管理、自動更新機能
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path
import sqlite3
from typing import List

logger = logging.getLogger(__name__)

class JQuantsTokenManager:
    """J-Quants APIトークン管理クラス"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'database', 'tokens.db')
        self.token_table = 'jquants_tokens'
        self._initialize_db()
    
    def _initialize_db(self):
        """トークン管理用データベースを初期化"""
        try:
            # ディレクトリが存在しない場合は作成
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(f'''
                    CREATE TABLE IF NOT EXISTS {self.token_table} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_identifier TEXT UNIQUE,
                        refresh_token TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP NOT NULL,
                        last_used_at TIMESTAMP,
                        is_active BOOLEAN DEFAULT 1,
                        plan_type TEXT DEFAULT 'Standard',
                        notes TEXT
                    )
                ''')
                conn.commit()
                logger.info("トークン管理データベースを初期化しました")
        except Exception as e:
            logger.error(f"トークン管理DB初期化エラー: {str(e)}")
    
    def save_refresh_token(self, refresh_token: str, user_identifier: str = 'default', plan_type: str = 'Standard') -> bool:
        """
        リフレッシュトークンを保存
        
        Args:
            refresh_token (str): リフレッシュトークン
            user_identifier (str): ユーザー識別子
            plan_type (str): プランタイプ (Standard, Light, Free)
            
        Returns:
            bool: 保存成功の場合True
        """
        try:
            # 有効期限を計算（1週間後）
            expires_at = datetime.now() + timedelta(days=7)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 既存のトークンを無効化
                cursor.execute(f'''
                    UPDATE {self.token_table} 
                    SET is_active = 0 
                    WHERE user_identifier = ?
                ''', (user_identifier,))
                
                # 新しいトークンを保存
                cursor.execute(f'''
                    INSERT INTO {self.token_table} 
                    (user_identifier, refresh_token, expires_at, plan_type, last_used_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_identifier, refresh_token, expires_at, plan_type, datetime.now()))
                
                conn.commit()
                
                logger.info(f"リフレッシュトークンを保存しました (ユーザー: {user_identifier}, 有効期限: {expires_at})")
                return True
                
        except Exception as e:
            logger.error(f"トークン保存エラー: {str(e)}")
            return False
    
    def get_refresh_token(self, user_identifier: str = 'default') -> Optional[Dict[str, Any]]:
        """
        有効なリフレッシュトークンを取得
        
        Args:
            user_identifier (str): ユーザー識別子
            
        Returns:
            Optional[Dict]: トークン情報、見つからない場合はNone
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row  # 辞書形式で結果を取得
                cursor = conn.cursor()
                
                cursor.execute(f'''
                    SELECT * FROM {self.token_table}
                    WHERE user_identifier = ? 
                    AND is_active = 1 
                    AND expires_at > datetime('now')
                    ORDER BY created_at DESC
                    LIMIT 1
                ''', (user_identifier,))
                
                row = cursor.fetchone()
                if row:
                    token_info = dict(row)
                    
                    # 最終使用日時を更新
                    cursor.execute(f'''
                        UPDATE {self.token_table}
                        SET last_used_at = datetime('now')
                        WHERE id = ?
                    ''', (token_info['id'],))
                    conn.commit()
                    
                    logger.info(f"有効なリフレッシュトークンを取得しました (ユーザー: {user_identifier})")
                    return token_info
                else:
                    logger.warning(f"有効なリフレッシュトークンが見つかりません (ユーザー: {user_identifier})")
                    return None
                    
        except Exception as e:
            logger.error(f"トークン取得エラー: {str(e)}")
            return None
    
    def check_token_expiry(self, user_identifier: str = 'default') -> Dict[str, Any]:
        """
        トークンの有効期限をチェック
        
        Args:
            user_identifier (str): ユーザー識別子
            
        Returns:
            Dict: 有効期限情報
        """
        try:
            token_info = self.get_refresh_token(user_identifier)
            
            if not token_info:
                return {
                    'valid': False,
                    'status': 'not_found',
                    'message': 'トークンが見つかりません',
                    'days_remaining': 0
                }
            
            expires_at = datetime.fromisoformat(token_info['expires_at'])
            now = datetime.now()
            time_remaining = expires_at - now
            days_remaining = time_remaining.days
            
            if time_remaining.total_seconds() <= 0:
                return {
                    'valid': False,
                    'status': 'expired',
                    'message': 'トークンの有効期限が切れています',
                    'days_remaining': 0,
                    'expired_since': abs(days_remaining)
                }
            elif days_remaining <= 1:
                return {
                    'valid': True,
                    'status': 'expiring_soon',
                    'message': f'トークンは{int(time_remaining.total_seconds() // 3600)}時間後に期限切れになります',
                    'days_remaining': days_remaining,
                    'hours_remaining': int(time_remaining.total_seconds() // 3600)
                }
            elif days_remaining <= 2:
                return {
                    'valid': True,
                    'status': 'warning',
                    'message': f'トークンは{days_remaining}日後に期限切れになります',
                    'days_remaining': days_remaining
                }
            else:
                return {
                    'valid': True,
                    'status': 'valid',
                    'message': f'トークンは{days_remaining}日間有効です',
                    'days_remaining': days_remaining
                }
                
        except Exception as e:
            logger.error(f"トークン期限チェックエラー: {str(e)}")
            return {
                'valid': False,
                'status': 'error',
                'message': f'チェック中にエラーが発生しました: {str(e)}',
                'days_remaining': 0
            }
    
    def get_all_tokens(self) -> List[Dict[str, Any]]:
        """全てのトークン情報を取得（管理用）"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute(f'''
                    SELECT 
                        user_identifier,
                        plan_type,
                        created_at,
                        expires_at,
                        last_used_at,
                        is_active,
                        CASE 
                            WHEN expires_at > datetime('now') THEN 'valid'
                            ELSE 'expired'
                        END as status
                    FROM {self.token_table}
                    ORDER BY created_at DESC
                ''')
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"全トークン情報取得エラー: {str(e)}")
            return []
    
    def cleanup_expired_tokens(self) -> int:
        """期限切れトークンのクリーンアップ"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 30日以上前に期限切れになったトークンを削除
                cleanup_date = datetime.now() - timedelta(days=30)
                cursor.execute(f'''
                    DELETE FROM {self.token_table}
                    WHERE expires_at < ? AND is_active = 0
                ''', (cleanup_date,))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                if deleted_count > 0:
                    logger.info(f"期限切れトークンを{deleted_count}件削除しました")
                
                return deleted_count
                
        except Exception as e:
            logger.error(f"トークンクリーンアップエラー: {str(e)}")
            return 0
    
    def invalidate_token(self, user_identifier: str = 'default') -> bool:
        """トークンを無効化"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute(f'''
                    UPDATE {self.token_table}
                    SET is_active = 0
                    WHERE user_identifier = ? AND is_active = 1
                ''', (user_identifier,))
                
                updated_count = cursor.rowcount
                conn.commit()
                
                if updated_count > 0:
                    logger.info(f"トークンを無効化しました (ユーザー: {user_identifier})")
                    return True
                else:
                    logger.warning(f"無効化するトークンが見つかりません (ユーザー: {user_identifier})")
                    return False
                    
        except Exception as e:
            logger.error(f"トークン無効化エラー: {str(e)}")
            return False
