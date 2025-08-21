"""
ログ管理ユーティリティ
"""
import logging
import os
from datetime import datetime
from typing import Optional
from config.settings import get_config
from backend.utils.path_utils import get_relative_path, ensure_directory_exists


class CustomFormatter(logging.Formatter):
    """カスタムログフォーマッター"""
    
    def format(self, record):
        # ログレベルに応じた色付け（開発環境用）
        colors = {
            'DEBUG': '\033[36m',    # シアン
            'INFO': '\033[32m',     # 緑
            'WARNING': '\033[33m',  # 黄
            'ERROR': '\033[31m',    # 赤
            'CRITICAL': '\033[35m'  # マゼンタ
        }
        reset = '\033[0m'
        
        if hasattr(record, 'levelname') and record.levelname in colors:
            record.levelname = f"{colors[record.levelname]}{record.levelname}{reset}"
        
        return super().format(record)


class KabuLogger:
    """株式検索システム専用ロガー"""
    
    _instance = None
    _loggers = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._setup_logging()
        return cls._instance
    
    def _setup_logging(self):
        """ログ設定の初期化"""
        self.config = get_config()
        
        # ログディレクトリの作成
        log_dir = get_relative_path('logs')
        ensure_directory_exists(log_dir)
        
        # ログファイルパス
        self.log_file = os.path.join(log_dir, 'kabu_system.log')
        self.error_log_file = os.path.join(log_dir, 'kabu_error.log')
        
        # ルートロガーの設定
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG if self.config.DEBUG else logging.INFO)
        
        # 既存のハンドラーをクリア
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # フォーマッター
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
        console_formatter = CustomFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # ファイルハンドラー（全ログ）
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
        
        # ファイルハンドラー（エラーのみ）
        error_handler = logging.FileHandler(self.error_log_file, encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        root_logger.addHandler(error_handler)
        
        # コンソールハンドラー（開発環境のみ）
        if self.config.DEBUG:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            console_handler.setFormatter(console_formatter)
            root_logger.addHandler(console_handler)
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        指定した名前のロガーを取得
        
        Args:
            name: ロガー名
            
        Returns:
            logging.Logger: 設定済みロガー
        """
        if name not in self._loggers:
            logger = logging.getLogger(name)
            self._loggers[name] = logger
        
        return self._loggers[name]


# グローバルロガーインスタンス
_kabu_logger = None


def get_logger(name: str = 'kabu_system') -> logging.Logger:
    """
    ロガーを取得する共通関数
    
    Args:
        name: ロガー名
        
    Returns:
        logging.Logger: 設定済みロガー
    """
    global _kabu_logger
    
    if _kabu_logger is None:
        _kabu_logger = KabuLogger()
    
    return _kabu_logger.get_logger(name)


def log_api_access(endpoint: str, method: str, status_code: int, 
                  execution_time: float, user_id: Optional[str] = None):
    """
    API アクセスログを記録
    
    Args:
        endpoint: アクセスされたエンドポイント
        method: HTTPメソッド
        status_code: レスポンスステータスコード
        execution_time: 実行時間（秒）
        user_id: ユーザーID（認証機能実装時用）
    """
    logger = get_logger('api_access')
    
    log_message = f"{method} {endpoint} - Status: {status_code} - Time: {execution_time:.3f}s"
    if user_id:
        log_message += f" - User: {user_id}"
    
    if status_code >= 500:
        logger.error(log_message)
    elif status_code >= 400:
        logger.warning(log_message)
    else:
        logger.info(log_message)


def log_database_operation(operation: str, table: str, record_id: Optional[int] = None, 
                          execution_time: float = None, error: Optional[str] = None):
    """
    データベース操作ログを記録
    
    Args:
        operation: 操作種別（SELECT, INSERT, UPDATE, DELETE）
        table: 対象テーブル
        record_id: 対象レコードID
        execution_time: 実行時間（秒）
        error: エラーメッセージ
    """
    logger = get_logger('database')
    
    log_message = f"{operation} {table}"
    if record_id:
        log_message += f" (ID: {record_id})"
    if execution_time:
        log_message += f" - Time: {execution_time:.3f}s"
    
    if error:
        logger.error(f"{log_message} - Error: {error}")
    else:
        logger.info(log_message)


def log_business_logic(action: str, details: str, level: str = 'info'):
    """
    ビジネスロジックログを記録
    
    Args:
        action: 実行されたアクション
        details: 詳細情報
        level: ログレベル（debug, info, warning, error）
    """
    logger = get_logger('business_logic')
    
    log_message = f"{action} - {details}"
    
    if level == 'debug':
        logger.debug(log_message)
    elif level == 'warning':
        logger.warning(log_message)
    elif level == 'error':
        logger.error(log_message)
    else:
        logger.info(log_message)


def log_security_event(event_type: str, details: str, severity: str = 'warning', 
                      ip_address: Optional[str] = None):
    """
    セキュリティイベントログを記録
    
    Args:
        event_type: イベントタイプ
        details: 詳細情報
        severity: 重要度（info, warning, error, critical）
        ip_address: IPアドレス
    """
    logger = get_logger('security')
    
    log_message = f"[{event_type.upper()}] {details}"
    if ip_address:
        log_message += f" - IP: {ip_address}"
    
    if severity == 'critical':
        logger.critical(log_message)
    elif severity == 'error':
        logger.error(log_message)
    elif severity == 'warning':
        logger.warning(log_message)
    else:
        logger.info(log_message)


def log_performance_metric(operation: str, execution_time: float, 
                          additional_metrics: Optional[dict] = None):
    """
    パフォーマンスメトリクスログを記録
    
    Args:
        operation: 操作名
        execution_time: 実行時間（秒）
        additional_metrics: 追加メトリクス
    """
    logger = get_logger('performance')
    
    log_message = f"{operation} - Execution time: {execution_time:.3f}s"
    
    if additional_metrics:
        metrics_str = ', '.join([f"{k}: {v}" for k, v in additional_metrics.items()])
        log_message += f" - {metrics_str}"
    
    # パフォーマンス問題の閾値チェック
    if execution_time > 5.0:  # 5秒以上
        logger.warning(f"SLOW OPERATION - {log_message}")
    elif execution_time > 1.0:  # 1秒以上
        logger.info(f"MODERATE OPERATION - {log_message}")
    else:
        logger.debug(log_message)
