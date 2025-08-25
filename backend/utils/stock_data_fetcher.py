"""
株価・財務データ取得ユーティリティ
外部APIから株価やPBR等の財務指標データを取得する機能を提供
"""

import yfinance as yf
import logging
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
import requests
from time import sleep
import random

logger = logging.getLogger(__name__)

class StockDataFetcher:
    """株価・財務データ取得クラス"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.rate_limit_delay = 2  # APIコール間の待機時間（秒）
        self.max_retries = 3  # 最大リトライ回数
        self.retry_delays = [2, 5, 10]  # リトライ間隔（秒）
    
    def _format_jp_symbol(self, symbol: str) -> str:
        """日本株式コードをyfinance形式に変換"""
        # 4桁の株式コードに'.T'（東証）を付加
        if len(symbol) == 4 and symbol.isdigit():
            return f"{symbol}.T"
        return symbol
    
    def get_stock_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        指定された企業コードの株価・財務情報を取得（リトライ機能付き）
        
        Args:
            symbol (str): 企業コード（例: '7203'）
            
        Returns:
            Dict[str, Any]: 株価・財務データ、取得できない場合はNone
        """
        for attempt in range(self.max_retries + 1):
            try:
                formatted_symbol = self._format_jp_symbol(symbol)
                
                if attempt > 0:
                    delay = self.retry_delays[min(attempt - 1, len(self.retry_delays) - 1)]
                    logger.info(f"リトライ {attempt}/{self.max_retries} - {delay}秒後に再試行: {symbol}")
                    sleep(delay)
                else:
                    logger.info(f"株価データ取得開始: {symbol} ({formatted_symbol})")
                
                # ランダムな待機時間でレート制限を回避
                if attempt > 0:
                    sleep(random.uniform(1, 3))
                
                # yfinanceで企業情報を取得
                ticker = yf.Ticker(formatted_symbol)
                
                # 基本情報の取得
                info = ticker.info
                if not info or len(info) < 3:  # 空のレスポンスチェックを改善
                    if attempt < self.max_retries:
                        logger.warning(f"企業情報が不完全です（試行 {attempt + 1}）: {symbol}")
                        continue
                    else:
                        logger.warning(f"企業情報が取得できませんでした: {symbol}")
                        return None
                
                # 最新の株価データを取得（過去5日分）
                hist = ticker.history(period="5d")
                if hist.empty:
                    if attempt < self.max_retries:
                        logger.warning(f"株価履歴が空です（試行 {attempt + 1}）: {symbol}")
                        continue
                    else:
                        logger.warning(f"株価履歴が取得できませんでした: {symbol}")
                        return None
            
                # 最新の株価データ
                latest_data = hist.iloc[-1]
                latest_date = hist.index[-1].date()
                
                # 財務指標の取得（利用可能な場合）
                result = {
                'symbol': symbol,
                'formatted_symbol': formatted_symbol,
                'company_name': info.get('longName', ''),
                'sector': info.get('sector', ''),
                'market': self._get_market_name(info.get('exchange', '')),
                'price': round(float(latest_data['Close']), 2),
                'volume': int(latest_data['Volume']) if not pd.isna(latest_data['Volume']) else 0,
                'price_date': latest_date.isoformat(),
                'currency': info.get('currency', 'JPY'),
                
                # 財務指標
                'market_cap': info.get('marketCap'),
                'pbr': info.get('priceToBook'),  # PBR
                'per': info.get('trailingPE'),   # PER
                'forward_pe': info.get('forwardPE'),
                'roe': info.get('returnOnEquity'),  # ROE
                'debt_to_equity': info.get('debtToEquity'),
                'current_ratio': info.get('currentRatio'),
                'revenue_growth': info.get('revenueGrowth'),
                'earnings_growth': info.get('earningsGrowth'),
                
                # 価格統計
                'day_high': float(latest_data['High']),
                'day_low': float(latest_data['Low']),
                'fifty_two_week_high': info.get('fiftyTwoWeekHigh'),
                'fifty_two_week_low': info.get('fiftyTwoWeekLow'),
                
                # メタデータ
                'data_source': 'yfinance',
                'fetched_at': datetime.now().isoformat()
            }
            
                # データの妥当性チェック
                if result['price'] <= 0:
                    if attempt < self.max_retries:
                        logger.warning(f"無効な株価データ（試行 {attempt + 1}）: {symbol}, price={result['price']}")
                        continue
                    else:
                        logger.warning(f"無効な株価データ: {symbol}, price={result['price']}")
                        return None
                
                logger.info(f"株価データ取得成功: {symbol}, price={result['price']}")
                return result
                
            except requests.exceptions.HTTPError as e:
                if '429' in str(e):  # レート制限エラー
                    if attempt < self.max_retries:
                        logger.warning(f"レート制限エラー（試行 {attempt + 1}）: {symbol}")
                        continue
                    else:
                        logger.error(f"レート制限エラー（最大試行回数到達）: {symbol}")
                        return None
                else:
                    logger.error(f"HTTP エラー: {symbol}, error={str(e)}")
                    if attempt < self.max_retries:
                        continue
                    return None
            except Exception as e:
                if attempt < self.max_retries:
                    logger.warning(f"株価データ取得エラー（試行 {attempt + 1}）: {symbol}, error={str(e)}")
                    continue
                else:
                    logger.error(f"株価データ取得エラー（最大試行回数到達）: {symbol}, error={str(e)}")
                    return None
        
        # すべてのリトライが失敗した場合
        logger.error(f"株価データ取得失敗（全試行終了）: {symbol}")
        return None
    
    def _get_market_name(self, exchange: str) -> str:
        """取引所コードを日本語名に変換"""
        exchange_map = {
            'TSE': '東証',
            'TYO': '東証',
            'JPX': '東証',
            'TSE.T': '東証',
            'TOKYO': '東証'
        }
        return exchange_map.get(exchange.upper(), exchange)
    
    def get_multiple_stocks(self, symbols: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        複数の企業コードの株価データを一括取得
        
        Args:
            symbols (List[str]): 企業コードのリスト
            
        Returns:
            Dict[str, Optional[Dict]]: 企業コード別の株価データ
        """
        results = {}
        
        for i, symbol in enumerate(symbols):
            if i > 0:
                # より長い待機時間とランダム性を追加
                delay = self.rate_limit_delay + random.uniform(1, 3)
                sleep(delay)
            
            results[symbol] = self.get_stock_info(symbol)
            
            # 進捗ログ
            if (i + 1) % 10 == 0:
                logger.info(f"取得進捗: {i + 1}/{len(symbols)} 完了")
        
        logger.info(f"一括取得完了: {len(symbols)}件中{sum(1 for r in results.values() if r is not None)}件成功")
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
            datetime.fromisoformat(data['price_date'])
        except ValueError:
            logger.warning(f"無効な日付形式: {data['price_date']}")
            return False
        
        return True

# pandas import（yfinanceで使用）
try:
    import pandas as pd
except ImportError:
    logger.error("pandasライブラリが見つかりません。yfinanceの動作に必要です。")
    raise ImportError("pandas is required for yfinance to work properly")
