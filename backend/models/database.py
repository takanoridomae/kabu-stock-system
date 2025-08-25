import sqlite3
import os
import sys
from datetime import datetime
from typing import List, Dict, Optional, Union

# プロジェクトルートをパスに追加（相対インポート回避）
from backend.utils.path_utils import setup_project_path
setup_project_path()

class DatabaseManager:
    """データベース管理クラス"""
    
    def __init__(self, db_path: str = 'database/kabu_system.db'):
        self.db_path = db_path
        self.ensure_database_exists()
    
    def ensure_database_exists(self):
        """データベースファイルとディレクトリの存在確認"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def get_connection(self):
        """データベース接続を取得"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def execute_query(self, query: str, params: tuple = ()) -> List[sqlite3.Row]:
        """クエリ実行（SELECT用）"""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return cursor.fetchall()
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """クエリ実行（INSERT/UPDATE/DELETE用）"""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor.rowcount
    
    def execute_insert(self, query: str, params: tuple = ()) -> int:
        """INSERT実行してIDを返す"""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor.lastrowid

class Company:
    """企業情報モデル"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create(self, symbol: str, name: str, sector: str = '', market: str = '') -> int:
        """企業情報を作成"""
        query = """
        INSERT INTO companies (symbol, name, sector, market)
        VALUES (?, ?, ?, ?)
        """
        return self.db.execute_insert(query, (symbol, name, sector, market))
    
    def get_by_symbol(self, symbol: str) -> Optional[sqlite3.Row]:
        """企業コードで企業情報を取得"""
        query = "SELECT * FROM companies WHERE symbol = ?"
        results = self.db.execute_query(query, (symbol,))
        return results[0] if results else None
    
    def get_by_id(self, company_id: int) -> Optional[sqlite3.Row]:
        """IDで企業情報を取得"""
        query = "SELECT * FROM companies WHERE id = ?"
        results = self.db.execute_query(query, (company_id,))
        return results[0] if results else None
    
    def search(self, symbol: str = '', name: str = '', sector: str = '') -> List[sqlite3.Row]:
        """企業情報を検索"""
        query = "SELECT * FROM companies WHERE 1=1"
        params = []
        
        if symbol:
            query += " AND symbol LIKE ?"
            params.append(f"%{symbol}%")
        
        if name:
            query += " AND name LIKE ?"
            params.append(f"%{name}%")
        
        if sector:
            query += " AND sector LIKE ?"
            params.append(f"%{sector}%")
        
        query += " ORDER BY symbol"
        return self.db.execute_query(query, tuple(params))
    
    def update(self, company_id: int, **kwargs) -> int:
        """企業情報を更新"""
        fields = []
        params = []
        
        for field, value in kwargs.items():
            if field in ['symbol', 'name', 'sector', 'market']:
                fields.append(f"{field} = ?")
                params.append(value)
        
        if not fields:
            return 0
        
        params.append(company_id)
        query = f"UPDATE companies SET {', '.join(fields)} WHERE id = ?"
        return self.db.execute_update(query, tuple(params))

class StockPrice:
    """株価情報モデル"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create(self, company_id: int, price: float, price_date: str = None, volume: int = 0) -> int:
        """株価情報を作成（旧形式：下位互換性のため残存）"""
        if price_date is None:
            price_date = datetime.now().date()
        
        query = """
        INSERT OR REPLACE INTO stock_prices (company_id, price, price_date, volume)
        VALUES (?, ?, ?, ?)
        """
        return self.db.execute_insert(query, (company_id, price, price_date, volume))
    
    def create_or_update(self, company_id: int, price: float, price_date: str = None, volume: int = 0) -> Dict[str, Union[int, str]]:
        """株価情報を作成または更新（重複チェック付き）"""
        if price_date is None:
            price_date = datetime.now().date()
        
        # 既存データの確認
        existing_query = """
        SELECT id, price, volume FROM stock_prices 
        WHERE company_id = ? AND price_date = ?
        """
        existing = self.db.execute_query(existing_query, (company_id, price_date))
        
        if existing:
            # 既存データがある場合：データ内容を比較
            existing_data = existing[0]
            if (abs(float(existing_data['price']) - float(price)) > 0.01 or 
                existing_data['volume'] != volume):
                # データが異なる場合は警告を返す
                return {
                    'id': existing_data['id'],
                    'status': 'warning',
                    'message': f'同日の異なるデータが既に存在します。既存: 価格{existing_data["price"]}, 出来高{existing_data["volume"]} vs 新規: 価格{price}, 出来高{volume}',
                    'existing_data': dict(existing_data),
                    'new_data': {'price': price, 'volume': volume}
                }
            else:
                # 同じデータの場合は何もしない
                return {
                    'id': existing_data['id'],
                    'status': 'unchanged',
                    'message': '同じデータが既に存在します'
                }
        else:
            # 新規作成
            query = """
            INSERT INTO stock_prices (company_id, price, price_date, volume)
            VALUES (?, ?, ?, ?)
            """
            new_id = self.db.execute_insert(query, (company_id, price, price_date, volume))
            return {
                'id': new_id,
                'status': 'created',
                'message': '新規データを作成しました'
            }

    def force_update(self, company_id: int, price: float, price_date: str, volume: int = 0) -> int:
        """強制更新（データ修正用）"""
        query = """
        UPDATE stock_prices 
        SET price = ?, volume = ?
        WHERE company_id = ? AND price_date = ?
        """
        return self.db.execute_update(query, (price, volume, company_id, price_date))

    def get_conflicting_data(self, company_id: int, price_date: str) -> Optional[sqlite3.Row]:
        """指定日の既存データを確認"""
        query = """
        SELECT * FROM stock_prices 
        WHERE company_id = ? AND price_date = ?
        """
        results = self.db.execute_query(query, (company_id, price_date))
        return results[0] if results else None
    
    def get_latest_price(self, company_id: int) -> Optional[sqlite3.Row]:
        """最新の株価を取得"""
        query = """
        SELECT * FROM stock_prices 
        WHERE company_id = ? 
        ORDER BY price_date DESC 
        LIMIT 1
        """
        results = self.db.execute_query(query, (company_id,))
        return results[0] if results else None
    
    def get_price_history(self, company_id: int, days: int = 30) -> List[sqlite3.Row]:
        """株価履歴を取得"""
        query = """
        SELECT * FROM stock_prices 
        WHERE company_id = ? 
        ORDER BY price_date DESC 
        LIMIT ?
        """
        return self.db.execute_query(query, (company_id, days))

class FinancialMetrics:
    """財務指標モデル"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create(self, company_id: int, report_date: str = None, **metrics) -> int:
        """財務指標を作成（旧形式：下位互換性のため残存）"""
        if report_date is None:
            report_date = datetime.now().date()
        
        query = """
        INSERT OR REPLACE INTO financial_metrics 
        (company_id, pbr, per, equity_ratio, roe, roa, net_sales, operating_profit, report_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            company_id,
            metrics.get('pbr'),
            metrics.get('per'),
            metrics.get('equity_ratio'),
            metrics.get('roe'),
            metrics.get('roa'),
            metrics.get('net_sales'),
            metrics.get('operating_profit'),
            report_date
        )
        
        return self.db.execute_insert(query, params)
    
    def create_or_update(self, company_id: int, report_date: str = None, **metrics) -> Dict[str, Union[int, str]]:
        """財務指標を作成または更新（重複チェック付き）"""
        if report_date is None:
            report_date = datetime.now().date()
        
        # 既存データの確認
        existing_query = """
        SELECT id, pbr, per, equity_ratio, roe, roa, net_sales, operating_profit FROM financial_metrics 
        WHERE company_id = ? AND report_date = ?
        """
        existing = self.db.execute_query(existing_query, (company_id, report_date))
        
        if existing:
            # 既存データがある場合：データ内容を比較
            existing_data = existing[0]
            existing_metrics = {
                'pbr': existing_data['pbr'],
                'per': existing_data['per'],
                'equity_ratio': existing_data['equity_ratio'],
                'roe': existing_data['roe'],
                'roa': existing_data['roa'],
                'net_sales': existing_data['net_sales'],
                'operating_profit': existing_data['operating_profit']
            }
            
            new_metrics = {
                'pbr': metrics.get('pbr'),
                'per': metrics.get('per'),
                'equity_ratio': metrics.get('equity_ratio'),
                'roe': metrics.get('roe'),
                'roa': metrics.get('roa'),
                'net_sales': metrics.get('net_sales'),
                'operating_profit': metrics.get('operating_profit')
            }
            
            # データ差異をチェック
            has_difference = False
            for key in existing_metrics:
                existing_val = existing_metrics[key]
                new_val = new_metrics[key]
                if existing_val is not None and new_val is not None:
                    if abs(float(existing_val) - float(new_val)) > 0.0001:
                        has_difference = True
                        break
                elif existing_val != new_val:
                    has_difference = True
                    break
            
            if has_difference:
                # データが異なる場合は警告を返す
                return {
                    'id': existing_data['id'],
                    'status': 'warning',
                    'message': f'同一報告日の異なる財務指標データが既に存在します。',
                    'existing_data': existing_metrics,
                    'new_data': new_metrics
                }
            else:
                # 同じデータの場合は何もしない
                return {
                    'id': existing_data['id'],
                    'status': 'unchanged',
                    'message': '同じ財務指標データが既に存在します'
                }
        else:
            # 新規作成
            query = """
            INSERT INTO financial_metrics 
            (company_id, pbr, per, equity_ratio, roe, roa, net_sales, operating_profit, report_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            params = (
                company_id,
                metrics.get('pbr'),
                metrics.get('per'),
                metrics.get('equity_ratio'),
                metrics.get('roe'),
                metrics.get('roa'),
                metrics.get('net_sales'),
                metrics.get('operating_profit'),
                report_date
            )
            
            new_id = self.db.execute_insert(query, params)
            return {
                'id': new_id,
                'status': 'created',
                'message': '新規財務指標データを作成しました'
            }

    def force_update(self, company_id: int, report_date: str, **metrics) -> int:
        """強制更新（データ修正用）"""
        query = """
        UPDATE financial_metrics 
        SET pbr = ?, per = ?, equity_ratio = ?, roe = ?, roa = ?, net_sales = ?, operating_profit = ?
        WHERE company_id = ? AND report_date = ?
        """
        
        params = (
            metrics.get('pbr'),
            metrics.get('per'),
            metrics.get('equity_ratio'),
            metrics.get('roe'),
            metrics.get('roa'),
            metrics.get('net_sales'),
            metrics.get('operating_profit'),
            company_id,
            report_date
        )
        
        return self.db.execute_update(query, params)

    def get_conflicting_data(self, company_id: int, report_date: str) -> Optional[sqlite3.Row]:
        """指定報告日の既存データを確認"""
        query = """
        SELECT * FROM financial_metrics 
        WHERE company_id = ? AND report_date = ?
        """
        results = self.db.execute_query(query, (company_id, report_date))
        return results[0] if results else None
    
    def get_latest_metrics(self, company_id: int) -> Optional[sqlite3.Row]:
        """最新の財務指標を取得"""
        query = """
        SELECT * FROM financial_metrics 
        WHERE company_id = ? 
        ORDER BY report_date DESC 
        LIMIT 1
        """
        results = self.db.execute_query(query, (company_id,))
        return results[0] if results else None

class PriceStatistics:
    """価格統計モデル"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def update_statistics(self, company_id: int, period_type: str, period_value: str):
        """価格統計を更新"""
        if period_type == 'monthly':
            date_filter = f"strftime('%Y-%m', price_date) = '{period_value}'"
        elif period_type == 'yearly':
            date_filter = f"strftime('%Y', price_date) = '{period_value}'"
        else:  # all_time
            date_filter = "1=1"
        
        # 統計計算
        stats_query = f"""
        SELECT 
            MIN(price) as min_price,
            MAX(price) as max_price,
            AVG(price) as avg_price
        FROM stock_prices 
        WHERE company_id = ? AND {date_filter}
        """
        
        results = self.db.execute_query(stats_query, (company_id,))
        if not results or not results[0]['min_price']:
            return 0
        
        stats = results[0]
        
        # 統計データの挿入/更新
        query = """
        INSERT OR REPLACE INTO price_statistics 
        (company_id, period_type, period_value, min_price, max_price, avg_price)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        
        return self.db.execute_update(query, (
            company_id, period_type, period_value,
            stats['min_price'], stats['max_price'], stats['avg_price']
        ))
    
    def get_statistics(self, company_id: int, period_type: str = None) -> List[sqlite3.Row]:
        """価格統計を取得"""
        query = "SELECT * FROM price_statistics WHERE company_id = ?"
        params = [company_id]
        
        if period_type:
            query += " AND period_type = ?"
            params.append(period_type)
        
        query += " ORDER BY period_value DESC"
        return self.db.execute_query(query, tuple(params))

class TechnicalIndicators:
    """テクニカル指標モデル"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def create(self, company_id: int, indicator_date: str = None, **indicators) -> int:
        """テクニカル指標を作成（旧形式：下位互換性のため残存）"""
        if indicator_date is None:
            indicator_date = datetime.now().date()
        
        query = """
        INSERT OR REPLACE INTO technical_indicators 
        (company_id, indicator_date, rsi, macd, sma_25, sma_75, bollinger_upper, bollinger_lower)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            company_id,
            indicator_date,
            indicators.get('rsi'),
            indicators.get('macd'),
            indicators.get('sma_25'),
            indicators.get('sma_75'),
            indicators.get('bollinger_upper'),
            indicators.get('bollinger_lower')
        )
        
        return self.db.execute_insert(query, params)
    
    def create_or_update(self, company_id: int, indicator_date: str = None, **indicators) -> Dict[str, Union[int, str]]:
        """テクニカル指標を作成または更新（重複チェック付き）"""
        if indicator_date is None:
            indicator_date = datetime.now().date()
        
        # 既存データの確認
        existing_query = """
        SELECT id, rsi, macd, sma_25, sma_75, bollinger_upper, bollinger_lower 
        FROM technical_indicators 
        WHERE company_id = ? AND indicator_date = ?
        """
        existing = self.db.execute_query(existing_query, (company_id, indicator_date))
        
        if existing:
            # 既存データがある場合：データ内容を比較
            existing_data = existing[0]
            existing_indicators = {
                'rsi': existing_data['rsi'],
                'macd': existing_data['macd'],
                'sma_25': existing_data['sma_25'],
                'sma_75': existing_data['sma_75'],
                'bollinger_upper': existing_data['bollinger_upper'],
                'bollinger_lower': existing_data['bollinger_lower']
            }
            
            new_indicators = {
                'rsi': indicators.get('rsi'),
                'macd': indicators.get('macd'),
                'sma_25': indicators.get('sma_25'),
                'sma_75': indicators.get('sma_75'),
                'bollinger_upper': indicators.get('bollinger_upper'),
                'bollinger_lower': indicators.get('bollinger_lower')
            }
            
            # データ差異をチェック
            has_difference = False
            for key in existing_indicators:
                existing_val = existing_indicators[key]
                new_val = new_indicators[key]
                if existing_val is not None and new_val is not None:
                    if abs(float(existing_val) - float(new_val)) > 0.0001:
                        has_difference = True
                        break
                elif existing_val != new_val:
                    has_difference = True
                    break
            
            if has_difference:
                # データが異なる場合は警告を返す
                return {
                    'id': existing_data['id'],
                    'status': 'warning',
                    'message': f'同一日付の異なるテクニカル指標データが既に存在します。',
                    'existing_data': existing_indicators,
                    'new_data': new_indicators
                }
            else:
                # 同じデータの場合は何もしない
                return {
                    'id': existing_data['id'],
                    'status': 'unchanged',
                    'message': '同じテクニカル指標データが既に存在します'
                }
        else:
            # 新規作成
            query = """
            INSERT INTO technical_indicators 
            (company_id, indicator_date, rsi, macd, sma_25, sma_75, bollinger_upper, bollinger_lower)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            params = (
                company_id,
                indicator_date,
                indicators.get('rsi'),
                indicators.get('macd'),
                indicators.get('sma_25'),
                indicators.get('sma_75'),
                indicators.get('bollinger_upper'),
                indicators.get('bollinger_lower')
            )
            
            new_id = self.db.execute_insert(query, params)
            return {
                'id': new_id,
                'status': 'created',
                'message': '新規テクニカル指標データを作成しました'
            }

    def force_update(self, company_id: int, indicator_date: str, **indicators) -> int:
        """強制更新（データ修正用）"""
        query = """
        UPDATE technical_indicators 
        SET rsi = ?, macd = ?, sma_25 = ?, sma_75 = ?, bollinger_upper = ?, bollinger_lower = ?
        WHERE company_id = ? AND indicator_date = ?
        """
        
        params = (
            indicators.get('rsi'),
            indicators.get('macd'),
            indicators.get('sma_25'),
            indicators.get('sma_75'),
            indicators.get('bollinger_upper'),
            indicators.get('bollinger_lower'),
            company_id,
            indicator_date
        )
        
        return self.db.execute_update(query, params)

    def get_conflicting_data(self, company_id: int, indicator_date: str) -> Optional[sqlite3.Row]:
        """指定日の既存データを確認"""
        query = """
        SELECT * FROM technical_indicators 
        WHERE company_id = ? AND indicator_date = ?
        """
        results = self.db.execute_query(query, (company_id, indicator_date))
        return results[0] if results else None
    
    def get_latest_indicators(self, company_id: int) -> Optional[sqlite3.Row]:
        """最新のテクニカル指標を取得"""
        query = """
        SELECT * FROM technical_indicators 
        WHERE company_id = ? 
        ORDER BY indicator_date DESC 
        LIMIT 1
        """
        results = self.db.execute_query(query, (company_id,))
        return results[0] if results else None

# データベースマネージャーのシングルトンインスタンス
db_manager = DatabaseManager()

# モデルインスタンス
company_model = Company(db_manager)
stock_price_model = StockPrice(db_manager)
financial_metrics_model = FinancialMetrics(db_manager)
price_statistics_model = PriceStatistics(db_manager)
technical_indicators_model = TechnicalIndicators(db_manager)
