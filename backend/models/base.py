"""
データベースモデル共通基底クラス
"""
import sqlite3
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union, Any, Tuple
from datetime import datetime
from backend.utils.logger import get_logger, log_database_operation


class BaseModel(ABC):
    """データベースモデルの共通基底クラス"""
    
    def __init__(self, db_manager, table_name: str, unique_fields: List[str]):
        """
        初期化
        
        Args:
            db_manager: データベースマネージャー
            table_name: テーブル名
            unique_fields: 一意性チェック用フィールド
        """
        self.db = db_manager
        self.table_name = table_name
        self.unique_fields = unique_fields
        self.logger = get_logger(f'model.{table_name}')
    
    def _log_operation(self, operation: str, record_id: Optional[int] = None, 
                      execution_time: float = None, error: Optional[str] = None):
        """操作ログを記録"""
        log_database_operation(operation, self.table_name, record_id, execution_time, error)
    
    def get_by_id(self, record_id: int) -> Optional[sqlite3.Row]:
        """
        IDで単一レコードを取得
        
        Args:
            record_id: レコードID
            
        Returns:
            Optional[sqlite3.Row]: 見つかったレコードまたはNone
        """
        start_time = datetime.now()
        
        try:
            query = f"SELECT * FROM {self.table_name} WHERE id = ?"
            results = self.db.execute_query(query, (record_id,))
            
            execution_time = (datetime.now() - start_time).total_seconds()
            self._log_operation("SELECT", record_id, execution_time)
            
            return results[0] if results else None
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self._log_operation("SELECT", record_id, execution_time, str(e))
            raise
    
    def get_all(self, limit: Optional[int] = None, offset: int = 0) -> List[sqlite3.Row]:
        """
        全レコードを取得
        
        Args:
            limit: 取得件数制限
            offset: オフセット
            
        Returns:
            List[sqlite3.Row]: 取得されたレコードリスト
        """
        start_time = datetime.now()
        
        try:
            query = f"SELECT * FROM {self.table_name} ORDER BY id"
            
            if limit:
                query += f" LIMIT {limit} OFFSET {offset}"
            
            results = self.db.execute_query(query)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            self._log_operation("SELECT_ALL", execution_time=execution_time)
            
            return results
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self._log_operation("SELECT_ALL", execution_time=execution_time, error=str(e))
            raise
    
    def delete(self, record_id: int) -> int:
        """
        レコードを削除
        
        Args:
            record_id: 削除対象のレコードID
            
        Returns:
            int: 削除された行数
        """
        start_time = datetime.now()
        
        try:
            query = f"DELETE FROM {self.table_name} WHERE id = ?"
            rows_affected = self.db.execute_update(query, (record_id,))
            
            execution_time = (datetime.now() - start_time).total_seconds()
            self._log_operation("DELETE", record_id, execution_time)
            
            return rows_affected
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self._log_operation("DELETE", record_id, execution_time, str(e))
            raise
    
    def _build_where_clause(self, conditions: Dict[str, Any]) -> Tuple[str, tuple]:
        """
        WHERE句を構築
        
        Args:
            conditions: 条件辞書
            
        Returns:
            Tuple[str, tuple]: WHERE句とパラメータ
        """
        if not conditions:
            return "", ()
        
        where_parts = []
        params = []
        
        for field, value in conditions.items():
            if value is not None:
                where_parts.append(f"{field} = ?")
                params.append(value)
        
        where_clause = " WHERE " + " AND ".join(where_parts) if where_parts else ""
        return where_clause, tuple(params)
    
    def find_by_conditions(self, conditions: Dict[str, Any]) -> List[sqlite3.Row]:
        """
        条件でレコードを検索
        
        Args:
            conditions: 検索条件
            
        Returns:
            List[sqlite3.Row]: 見つかったレコードリスト
        """
        start_time = datetime.now()
        
        try:
            where_clause, params = self._build_where_clause(conditions)
            query = f"SELECT * FROM {self.table_name}{where_clause} ORDER BY id"
            
            results = self.db.execute_query(query, params)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            self._log_operation("SELECT_BY_CONDITIONS", execution_time=execution_time)
            
            return results
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self._log_operation("SELECT_BY_CONDITIONS", execution_time=execution_time, error=str(e))
            raise
    
    def get_conflicting_record(self, unique_data: Dict[str, Any]) -> Optional[sqlite3.Row]:
        """
        一意制約に違反するレコードを取得
        
        Args:
            unique_data: 一意性チェック用データ
            
        Returns:
            Optional[sqlite3.Row]: 競合するレコードまたはNone
        """
        conditions = {field: unique_data.get(field) for field in self.unique_fields}
        results = self.find_by_conditions(conditions)
        return results[0] if results else None
    
    def create_or_update_generic(self, unique_data: Dict[str, Any], 
                               update_data: Dict[str, Any]) -> Dict[str, Union[int, str]]:
        """
        汎用的な作成または更新処理
        
        Args:
            unique_data: 一意性チェック用データ
            update_data: 更新用データ
            
        Returns:
            Dict[str, Union[int, str]]: 処理結果
        """
        start_time = datetime.now()
        
        try:
            # 既存レコードの確認
            existing = self.get_conflicting_record(unique_data)
            
            if existing:
                # データ比較
                has_difference = self._has_data_difference(existing, update_data)
                
                if has_difference:
                    execution_time = (datetime.now() - start_time).total_seconds()
                    self._log_operation("CHECK_CONFLICT", existing['id'], execution_time)
                    
                    return {
                        'id': existing['id'],
                        'status': 'warning',
                        'message': f'競合するデータが既に存在します。',
                        'existing_data': dict(existing),
                        'new_data': update_data
                    }
                else:
                    execution_time = (datetime.now() - start_time).total_seconds()
                    self._log_operation("NO_CHANGE", existing['id'], execution_time)
                    
                    return {
                        'id': existing['id'],
                        'status': 'unchanged',
                        'message': '同じデータが既に存在します'
                    }
            else:
                # 新規作成
                all_data = {**unique_data, **update_data}
                new_id = self._create_record(all_data)
                
                execution_time = (datetime.now() - start_time).total_seconds()
                self._log_operation("INSERT", new_id, execution_time)
                
                return {
                    'id': new_id,
                    'status': 'created',
                    'message': '新規データを作成しました'
                }
                
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self._log_operation("CREATE_OR_UPDATE", execution_time=execution_time, error=str(e))
            raise
    
    def force_update_generic(self, unique_data: Dict[str, Any], 
                           update_data: Dict[str, Any]) -> int:
        """
        汎用的な強制更新処理
        
        Args:
            unique_data: 一意性チェック用データ
            update_data: 更新用データ
            
        Returns:
            int: 更新された行数
        """
        start_time = datetime.now()
        
        try:
            where_clause, where_params = self._build_where_clause(unique_data)
            
            if not where_clause:
                raise ValueError("更新条件が指定されていません")
            
            # SET句の構築
            set_parts = []
            set_params = []
            
            for field, value in update_data.items():
                set_parts.append(f"{field} = ?")
                set_params.append(value)
            
            if not set_parts:
                raise ValueError("更新データが指定されていません")
            
            # UPDATE文の実行
            query = f"UPDATE {self.table_name} SET {', '.join(set_parts)}{where_clause}"
            params = tuple(set_params + list(where_params))
            
            rows_affected = self.db.execute_update(query, params)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            self._log_operation("UPDATE", execution_time=execution_time)
            
            return rows_affected
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self._log_operation("UPDATE", execution_time=execution_time, error=str(e))
            raise
    
    def _has_data_difference(self, existing_record: sqlite3.Row, 
                           new_data: Dict[str, Any], tolerance: float = 0.0001) -> bool:
        """
        既存レコードと新データの差異をチェック
        
        Args:
            existing_record: 既存レコード
            new_data: 新しいデータ
            tolerance: 数値比較の許容誤差
            
        Returns:
            bool: 差異がある場合True
        """
        for field, new_value in new_data.items():
            if field not in existing_record.keys():
                continue
            
            existing_value = existing_record[field]
            
            # None値の比較
            if existing_value is None and new_value is None:
                continue
            if existing_value is None or new_value is None:
                return True
            
            # 数値の比較（許容誤差あり）
            if isinstance(existing_value, (int, float)) and isinstance(new_value, (int, float)):
                if abs(float(existing_value) - float(new_value)) > tolerance:
                    return True
            # 文字列の比較
            elif str(existing_value) != str(new_value):
                return True
        
        return False
    
    @abstractmethod
    def _create_record(self, data: Dict[str, Any]) -> int:
        """
        レコード作成の具象実装
        
        Args:
            data: 作成するデータ
            
        Returns:
            int: 作成されたレコードのID
        """
        pass
    
    @abstractmethod
    def _get_create_fields(self) -> List[str]:
        """
        作成時に使用するフィールドリストを取得
        
        Returns:
            List[str]: フィールド名のリスト
        """
        pass
