"""
プロジェクトパス管理ユーティリティ
"""
import os
import sys
from pathlib import Path


def get_project_root() -> str:
    """
    プロジェクトルートディレクトリのパスを取得
    
    Returns:
        str: プロジェクトルートの絶対パス
    """
    # このファイルから見たプロジェクトルート
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent
    return str(project_root.resolve())


def setup_project_path() -> None:
    """
    プロジェクトルートをPythonパスに追加
    重複追加を防ぐ
    """
    project_root = get_project_root()
    
    if project_root not in sys.path:
        sys.path.insert(0, project_root)


def get_relative_path(*path_parts: str) -> str:
    """
    プロジェクトルートからの相対パスを構築
    
    Args:
        *path_parts: パス要素
        
    Returns:
        str: 構築されたパス
    """
    project_root = get_project_root()
    return os.path.join(project_root, *path_parts)


def ensure_directory_exists(directory_path: str) -> None:
    """
    ディレクトリの存在を確認し、なければ作成
    
    Args:
        directory_path: 確認するディレクトリパス
    """
    os.makedirs(directory_path, exist_ok=True)
