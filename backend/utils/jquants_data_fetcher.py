"""
J-Quants API株価・財務データ取得ユーティリティ
日本取引所公式APIから株価やPBR等の財務指標データを取得する機能を提供
"""

import logging
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
import os
from decimal import Decimal

logger = logging.getLogger(__name__)

class JQuantsDataFetcher:
    """J-Quants API株価・財務データ取得クラス"""
    
    def __init__(self, email: str = None, password: str = None, refresh_token: str = None):
        self.email = email or os.getenv('JQUANTS_EMAIL')
        self.password = password or os.getenv('JQUANTS_PASSWORD')
        self.refresh_token = refresh_token or os.getenv('JQUANTS_REFRESH_TOKEN')
        self.client = None
        self.is_authenticated = False
        
        # 保存済みトークンがない場合、データベースから取得を試行
        if not self.refresh_token:
            self._load_saved_token()
        
        # 設定チェック
        if not any([self.email and self.password, self.refresh_token]):
            logger.warning("J-Quants APIの認証情報が設定されていません")
    
    def _load_saved_token(self):
        """保存済みトークンをデータベースから読み込み"""
        try:
            from backend.utils.token_manager import JQuantsTokenManager
            token_manager = JQuantsTokenManager()
            token_info = token_manager.get_refresh_token()
            
            if token_info:
                self.refresh_token = token_info['refresh_token']
                logger.info("保存済みリフレッシュトークンを読み込みました")
            else:
                logger.debug("保存済みトークンが見つかりませんでした")
                
        except Exception as e:
            logger.warning(f"保存済みトークン読み込みエラー: {str(e)}")
    
    def _initialize_client(self):
        """J-Quants APIクライアントを初期化（直接API実装）"""
        try:
            # 直接HTTP APIを使用したシンプルな実装
            import requests
            
            self.base_url = "https://api.jquants.com/v1"
            self.session = requests.Session()
            self.id_token = None
            
            # 認証を実行
            if self.refresh_token:
                success = self._authenticate_with_refresh_token()
            elif self.email and self.password:
                success = self._authenticate_with_credentials()
            else:
                logger.error("J-Quants APIの認証情報が不足しています")
                return False
            
            if success:
                self.is_authenticated = True
                logger.info("J-Quants APIクライアントを初期化しました")
                return True
            else:
                logger.error("J-Quants API認証に失敗しました")
                return False
            
        except Exception as e:
            logger.error(f"J-Quants APIクライアントの初期化に失敗: {str(e)}")
            return False
    
    def _authenticate_with_refresh_token(self):
        """リフレッシュトークンで認証（クエリパラメータ方式）"""
        try:
            # J-Quants APIの正しい形式：クエリパラメータでリフレッシュトークンを送信
            url = f"{self.base_url}/token/auth_refresh?refreshtoken={self.refresh_token}"
            headers = {"Content-Type": "application/json"}
            
            logger.info(f"J-Quants API認証開始: {self.base_url}/token/auth_refresh")
            logger.info(f"リフレッシュトークン長: {len(self.refresh_token)} 文字")
            logger.info(f"リフレッシュトークン（先頭20文字）: {self.refresh_token[:20]}...")
            
            # POSTリクエスト（ボディなし、クエリパラメータのみ）
            response = self.session.post(url, headers=headers, timeout=30)
            
            logger.info(f"認証レスポンスステータス: {response.status_code}")
            logger.info(f"認証レスポンスヘッダー: {dict(response.headers)}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"認証レスポンスデータ: {result}")
                
                # IDトークンの取得と検証
                self.id_token = result.get("idToken")
                if self.id_token:
                    logger.info(f"✅ IDトークン取得成功!")
                    logger.info(f"IDトークン長: {len(self.id_token)} 文字")
                    logger.info(f"IDトークン（先頭20文字）: {self.id_token[:20]}...")
                    logger.info(f"リフレッシュトークン → IDトークン変換完了")
                    return True
                else:
                    logger.error("❌ IDトークンがレスポンスに含まれていません")
                    logger.error(f"受信レスポンスキー: {list(result.keys())}")
                    return False
            else:
                try:
                    error_data = response.json()
                    logger.error(f"認証失敗 ({response.status_code}): {error_data}")
                except:
                    logger.error(f"認証失敗 ({response.status_code}): {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"リフレッシュトークン認証エラー: {str(e)}")
            return False
    
    def _authenticate_with_credentials(self):
        """メール・パスワードで認証"""
        try:
            url = f"{self.base_url}/token/auth_user"
            headers = {"Content-Type": "application/json"}
            data = {"mailaddress": self.email, "password": self.password}
            
            response = self.session.post(url, json=data, headers=headers)
            if response.status_code == 200:
                result = response.json()
                self.id_token = result.get("idToken")
                return self.id_token is not None
            else:
                logger.error(f"メール・パスワード認証失敗: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"メール・パスワード認証エラー: {str(e)}")
            return False
    
    def get_stock_info(self, symbol: str, date: str = None) -> Optional[Dict[str, Any]]:
        """
        指定された企業コードの株価・財務情報を取得
        
        Args:
            symbol (str): 企業コード（例: '7203'）
            date (str): 取得日付（YYYY-MM-DD形式、Noneの場合は最新）
            
        Returns:
            Dict[str, Any]: 株価・財務データ、取得できない場合はNone
        """
        if not self.is_authenticated and not self._initialize_client():
            logger.error("J-Quants APIの初期化に失敗しました")
            return None
        
        try:
            # 日付の設定（未指定の場合は前営業日）
            if not date:
                target_date = self._get_latest_business_date()
            else:
                target_date = date
            
            logger.info(f"J-Quants APIでデータ取得開始: {symbol} ({target_date})")
            
            # 株価データの取得
            stock_data = self._get_daily_quotes(symbol, target_date)
            if not stock_data:
                logger.warning(f"株価データが取得できませんでした: {symbol}")
                return None
            
            # 財務データの取得（四半期決算データ）
            financial_data = self._get_financial_statements(symbol)
            
            # 結果をマッピング
            result = {
                'symbol': symbol,
                'company_name': stock_data.get('CompanyName', ''),
                'sector': stock_data.get('Sector', ''),
                'market': self._get_market_name(stock_data.get('MarketCode', '')),
                'price': float(stock_data.get('Close', 0)),
                'volume': int(stock_data.get('Volume', 0)),
                'price_date': target_date,
                'currency': 'JPY',
                
                # 価格データ
                'day_high': float(stock_data.get('High', 0)),
                'day_low': float(stock_data.get('Low', 0)),
                'open_price': float(stock_data.get('Open', 0)),
                
                # 財務指標（利用可能な場合）
                'market_cap': financial_data.get('market_cap'),
                'pbr': financial_data.get('pbr'),
                'per': financial_data.get('per'),
                'roe': financial_data.get('roe'),
                'equity_ratio': financial_data.get('equity_ratio'),
                'roa': financial_data.get('roa'),
                
                # メタデータ
                'data_source': 'j_quants',
                'fetched_at': datetime.now().isoformat()
            }
            
            # データの妥当性チェック
            if not self.validate_stock_data(result):
                logger.warning(f"取得したデータが無効です: {symbol}")
                return None
            
            logger.info(f"J-Quants APIでデータ取得成功: {symbol}, price={result['price']}")
            return result
            
        except Exception as e:
            logger.error(f"J-Quants APIデータ取得エラー: {symbol}, error={str(e)}")
            return None
    
    def _get_daily_quotes(self, symbol: str, date: str) -> Optional[Dict[str, Any]]:
        """日次株価データを取得"""
        try:
            if not self.id_token:
                logger.error("認証トークンがありません")
                return None
            
            # J-Quants APIエンドポイント
            url = f"{self.base_url}/prices/daily_quotes"
            headers = {
                "Authorization": f"Bearer {self.id_token}",
                "Content-Type": "application/json"
            }
            
            params = {
                "code": symbol,
                "date": date
            }
            
            response = self.session.get(url, headers=headers, params=params)
            
            logger.info(f"株価データAPIレスポンス ({symbol}): {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"株価データ取得成功 ({symbol}): {data}")
                quotes = data.get("daily_quotes", [])
                
                if quotes and len(quotes) > 0:
                    return quotes[0]
                else:
                    logger.warning(f"株価データが空です ({symbol})")
            elif response.status_code == 401:
                logger.error("J-Quants API認証が無効です")
                return None
            else:
                try:
                    error_data = response.json()
                    logger.error(f"J-Quants API応答エラー ({response.status_code}): {error_data}")
                except:
                    logger.error(f"J-Quants API応答エラー ({response.status_code}): {response.text}")
            
            # データが見つからない場合、過去数日分を試す
            for days_back in range(1, 8):  # 過去7日分試す
                past_date = (datetime.strptime(date, '%Y-%m-%d') - timedelta(days=days_back)).strftime('%Y-%m-%d')
                
                params["date"] = past_date
                response = self.session.get(url, headers=headers, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    quotes = data.get("daily_quotes", [])
                    if quotes and len(quotes) > 0:
                        logger.info(f"過去データを使用: {symbol} ({past_date})")
                        return quotes[0]
            
            return None
            
        except Exception as e:
            logger.error(f"日次株価データ取得エラー: {symbol}, {str(e)}")
            return None
    
    def _get_financial_statements(self, symbol: str) -> Dict[str, Any]:
        """財務諸表データを取得"""
        try:
            if not self.id_token:
                logger.warning("認証トークンがないため財務データをスキップします")
                return {}
            
            # J-Quants API財務諸表エンドポイント
            url = f"{self.base_url}/fins/statements"
            headers = {
                "Authorization": f"Bearer {self.id_token}",
                "Content-Type": "application/json"
            }
            
            params = {"code": symbol}
            
            response = self.session.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                statements = data.get("statements", [])
                
                if not statements:
                    return {}
                
                # 最新の財務データを取得
                latest_data = statements[0] if statements else {}
                
                # 財務指標の計算
                result = {}
                
                # J-Quants APIの実際のフィールド名に合わせて調整
                # 注意: 実際のAPIレスポンス構造に応じて調整が必要
                if 'NetAssets' in latest_data and 'MarketCap' in latest_data:
                    net_assets = float(latest_data.get('NetAssets', 0))
                    market_cap = float(latest_data.get('MarketCap', 0))
                    if net_assets > 0:
                        result['pbr'] = market_cap / net_assets
                
                if 'NetIncome' in latest_data and 'MarketCap' in latest_data:
                    net_income = float(latest_data.get('NetIncome', 0))
                    market_cap = float(latest_data.get('MarketCap', 0))
                    if net_income > 0:
                        result['per'] = market_cap / net_income
                
                if 'NetIncome' in latest_data and 'NetAssets' in latest_data:
                    net_income = float(latest_data.get('NetIncome', 0))
                    net_assets = float(latest_data.get('NetAssets', 0))
                    if net_assets > 0:
                        result['roe'] = net_income / net_assets
                
                if 'NetAssets' in latest_data and 'TotalAssets' in latest_data:
                    net_assets = float(latest_data.get('NetAssets', 0))
                    total_assets = float(latest_data.get('TotalAssets', 0))
                    if total_assets > 0:
                        result['equity_ratio'] = net_assets / total_assets
                
                if 'NetIncome' in latest_data and 'TotalAssets' in latest_data:
                    net_income = float(latest_data.get('NetIncome', 0))
                    total_assets = float(latest_data.get('TotalAssets', 0))
                    if total_assets > 0:
                        result['roa'] = net_income / total_assets
                
                result['market_cap'] = latest_data.get('MarketCap')
                
                return result
            elif response.status_code == 401:
                logger.warning("財務データ取得で認証エラー")
                return {}
            else:
                logger.warning(f"財務データ取得エラー: {response.status_code}")
                return {}
            
        except Exception as e:
            logger.warning(f"財務諸表データ取得エラー: {symbol}, {str(e)}")
            return {}
    
    def _get_latest_business_date(self) -> str:
        """最新の営業日を取得"""
        today = datetime.now()
        
        # 土日を避ける
        while today.weekday() >= 5:  # 5=土曜日, 6=日曜日
            today -= timedelta(days=1)
        
        # 現在時刻が15:00以前の場合は前営業日を使用
        if today.hour < 15:
            today -= timedelta(days=1)
            while today.weekday() >= 5:
                today -= timedelta(days=1)
        
        return today.strftime('%Y-%m-%d')
    
    def _get_market_name(self, market_code: str) -> str:
        """市場コードを日本語名に変換"""
        market_map = {
            'TSE1': '東証プライム',
            'TSE2': '東証スタンダード',
            'TSE3': '東証グロース',
            'TSE': '東証',
            'JQS': 'JASDAQ',
            'JQG': 'JASDAQ',
            'MSC': 'マザーズ'
        }
        return market_map.get(market_code, market_code)
    
    def get_multiple_stocks(self, symbols: List[str], date: str = None) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        複数の企業コードの株価データを一括取得
        
        Args:
            symbols (List[str]): 企業コードのリスト
            date (str): 取得日付（YYYY-MM-DD形式、Noneの場合は最新）
            
        Returns:
            Dict[str, Optional[Dict]]: 企業コード別の株価データ
        """
        results = {}
        
        for i, symbol in enumerate(symbols):
            results[symbol] = self.get_stock_info(symbol, date)
            
            # 進捗ログ
            if (i + 1) % 10 == 0:
                logger.info(f"J-Quants API取得進捗: {i + 1}/{len(symbols)} 完了")
        
        logger.info(f"J-Quants API一括取得完了: {len(symbols)}件中{sum(1 for r in results.values() if r is not None)}件成功")
        return results
    
    def validate_stock_data(self, data: Dict[str, Any]) -> bool:
        """
        取得した株価データの妥当性を検証
        
        Args:
            data (Dict): 株価データ
            
        Returns:
            bool: データが妥当な場合True
        """
        required_fields = ['symbol', 'price', 'price_date']
        
        # 必須フィールドの確認
        for field in required_fields:
            if field not in data or data[field] is None:
                logger.warning(f"必須フィールドが不足: {field}")
                return False
        
        # 株価の妥当性確認
        if not isinstance(data['price'], (int, float)) or data['price'] <= 0:
            logger.warning(f"無効な株価: {data['price']}")
            return False
        
        # 日付の妥当性確認
        try:
            datetime.strptime(data['price_date'], '%Y-%m-%d')
        except ValueError:
            logger.warning(f"無効な日付形式: {data['price_date']}")
            return False
        
        return True
    
    def get_api_status(self) -> Dict[str, Any]:
        """J-Quants APIの状況を確認"""
        try:
            if not self.is_authenticated and not self._initialize_client():
                return {
                    'available': False,
                    'message': 'J-Quants APIの認証に失敗（認証情報を確認してください）',
                    'plan': 'Unknown',
                    'authenticated': False
                }
            
            # プラン情報を取得（可能な場合）
            plan = 'Unknown'
            try:
                if self.id_token:
                    # ユーザー情報APIがあれば使用
                    url = f"{self.base_url}/user"
                    headers = {"Authorization": f"Bearer {self.id_token}"}
                    response = self.session.get(url, headers=headers)
                    if response.status_code == 200:
                        user_data = response.json()
                        plan = user_data.get('plan', 'Free')
            except:
                plan = 'Free（推定）'
            
            return {
                'available': True,
                'message': 'J-Quants API利用可能',
                'plan': plan,
                'authenticated': self.is_authenticated
            }
            
        except Exception as e:
            return {
                'available': False,
                'message': f'J-Quants APIエラー: {str(e)}',
                'plan': 'Unknown',
                'authenticated': False
            }
