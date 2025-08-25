"""
J-Quants API株価データ一括処理ユーティリティ
登録済み企業に対してJ-Quants APIを使用して株価・財務データを取得・更新する機能
"""

import logging
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime, timedelta
import sys
import os

# パスの設定
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.utils.jquants_data_fetcher import JQuantsDataFetcher
from backend.models.database import (
    company_model, stock_price_model, financial_metrics_model,
    price_statistics_model, db_manager
)

logger = logging.getLogger(__name__)

class JQuantsBatchProcessor:
    """J-Quants API株価データ一括処理クラス"""
    
    def __init__(self, email: str = None, password: str = None, refresh_token: str = None):
        self.fetcher = JQuantsDataFetcher(email, password, refresh_token)
        self.success_count = 0
        self.error_count = 0
        self.skip_count = 0
        self.processing_results = []
    
    def get_all_companies(self) -> List[Dict[str, Any]]:
        """
        データベースから全ての登録済み企業を取得
        
        Returns:
            List[Dict]: 企業情報のリスト
        """
        try:
            companies = company_model.search()
            company_list = [dict(company) for company in companies]
            logger.info(f"登録済み企業数: {len(company_list)}")
            return company_list
        except Exception as e:
            logger.error(f"企業一覧取得エラー: {str(e)}")
            return []
    
    def should_update_data(self, company_id: int, last_update_days: int = 1) -> bool:
        """
        指定した企業のデータ更新が必要かチェック
        
        Args:
            company_id (int): 企業ID
            last_update_days (int): 更新間隔（日）
            
        Returns:
            bool: 更新が必要な場合True
        """
        try:
            # 最新の株価データを確認
            latest_price = stock_price_model.get_latest_price(company_id)
            
            if not latest_price:
                return True  # データが存在しない場合は更新
            
            last_update = datetime.fromisoformat(latest_price['price_date'])
            cutoff_date = datetime.now() - timedelta(days=last_update_days)
            
            return last_update.date() < cutoff_date.date()
            
        except Exception as e:
            logger.warning(f"更新判定エラー（company_id={company_id}）: {str(e)}")
            return True  # エラー時は更新
    
    def process_company_data(self, company: Dict[str, Any], force_update: bool = False, date: str = None) -> Dict[str, Any]:
        """
        単一企業の株価・財務データを処理
        
        Args:
            company (Dict): 企業情報
            force_update (bool): 強制更新フラグ
            date (str): 取得日付（YYYY-MM-DD形式、Noneの場合は最新）
            
        Returns:
            Dict: 処理結果
        """
        company_id = company['id']
        symbol = company['symbol']
        
        result = {
            'company_id': company_id,
            'symbol': symbol,
            'status': 'processing',
            'message': '',
            'data_updated': False,
            'errors': [],
            'data_source': 'j_quants'
        }
        
        try:
            # 更新判定
            if not force_update and not self.should_update_data(company_id):
                result.update({
                    'status': 'skipped',
                    'message': '最新データが既に存在'
                })
                self.skip_count += 1
                return result
            
            # J-Quants APIからデータ取得
            stock_data = self.fetcher.get_stock_info(symbol, date)
            
            if not stock_data:
                result.update({
                    'status': 'error',
                    'message': 'J-Quants APIからデータを取得できませんでした'
                })
                self.error_count += 1
                return result
            
            # データの妥当性チェック
            if not self.fetcher.validate_stock_data(stock_data):
                result.update({
                    'status': 'error',
                    'message': '取得したデータが無効です'
                })
                self.error_count += 1
                return result
            
            # 株価データの更新
            stock_result = self._update_stock_price(company_id, stock_data)
            if stock_result['success']:
                result['data_updated'] = True
            else:
                result['errors'].append(f"株価更新エラー: {stock_result['message']}")
            
            # 財務指標の更新
            financial_result = self._update_financial_metrics(company_id, stock_data)
            if financial_result['success']:
                result['data_updated'] = True
            else:
                result['errors'].append(f"財務指標更新エラー: {financial_result['message']}")
            
            # 価格統計の更新
            self._update_price_statistics(company_id)
            
            # 企業情報の更新（sector, marketが取得できた場合）
            if stock_data.get('sector') or stock_data.get('market'):
                self._update_company_info(company_id, stock_data)
            
            result.update({
                'status': 'success',
                'message': f"J-Quants APIでデータ更新完了（株価: {stock_data['price']}円）",
                'latest_price': stock_data['price'],
                'price_date': stock_data['price_date']
            })
            self.success_count += 1
            
        except Exception as e:
            result.update({
                'status': 'error',
                'message': f'処理エラー: {str(e)}'
            })
            self.error_count += 1
            logger.error(f"企業データ処理エラー（{symbol}）: {str(e)}")
        
        return result
    
    def _update_stock_price(self, company_id: int, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """株価データを更新"""
        try:
            price_result = stock_price_model.create_or_update(
                company_id=company_id,
                price=stock_data['price'],
                price_date=stock_data['price_date'],
                volume=stock_data.get('volume', 0)
            )
            
            return {
                'success': True,
                'action': price_result.get('action', 'unknown'),
                'message': price_result.get('message', 'success')
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': str(e)
            }
    
    def _update_financial_metrics(self, company_id: int, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """財務指標データを更新"""
        try:
            # 財務指標のマッピング
            financial_data = {}
            
            if stock_data.get('pbr') is not None:
                financial_data['pbr'] = float(stock_data['pbr'])
            
            if stock_data.get('per') is not None:
                financial_data['per'] = float(stock_data['per'])
            
            if stock_data.get('roe') is not None:
                financial_data['roe'] = float(stock_data['roe'])
            
            if stock_data.get('equity_ratio') is not None:
                financial_data['equity_ratio'] = float(stock_data['equity_ratio'])
            
            if stock_data.get('roa') is not None:
                financial_data['roa'] = float(stock_data['roa'])
            
            # データがある場合のみ更新
            if financial_data:
                financial_metrics_model.create_or_update(
                    company_id=company_id,
                    report_date=stock_data['price_date'],
                    **financial_data
                )
                
                return {
                    'success': True,
                    'message': f"財務指標更新: {list(financial_data.keys())}"
                }
            else:
                return {
                    'success': True,
                    'message': "更新可能な財務指標なし"
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': str(e)
            }
    
    def _update_price_statistics(self, company_id: int):
        """価格統計を更新"""
        try:
            current_month = datetime.now().strftime('%Y-%m')
            current_year = datetime.now().strftime('%Y')
            
            price_statistics_model.update_statistics(company_id, 'monthly', current_month)
            price_statistics_model.update_statistics(company_id, 'yearly', current_year)
            price_statistics_model.update_statistics(company_id, 'all_time', 'all')
            
        except Exception as e:
            logger.warning(f"価格統計更新エラー（company_id={company_id}）: {str(e)}")
    
    def _update_company_info(self, company_id: int, stock_data: Dict[str, Any]):
        """企業情報を更新"""
        try:
            update_data = {}
            
            if stock_data.get('sector'):
                update_data['sector'] = stock_data['sector']
            
            if stock_data.get('market'):
                update_data['market'] = stock_data['market']
            
            if update_data:
                company_model.update(company_id, **update_data)
                
        except Exception as e:
            logger.warning(f"企業情報更新エラー（company_id={company_id}）: {str(e)}")
    
    def process_all_companies(self, force_update: bool = False, max_companies: Optional[int] = None, date: str = None) -> Dict[str, Any]:
        """
        全ての登録済み企業の株価データを一括処理
        
        Args:
            force_update (bool): 強制更新フラグ
            max_companies (Optional[int]): 処理する最大企業数
            date (str): 取得日付（YYYY-MM-DD形式、Noneの場合は最新）
            
        Returns:
            Dict: 処理結果のサマリー
        """
        start_time = datetime.now()
        
        # カウンターをリセット
        self.success_count = 0
        self.error_count = 0
        self.skip_count = 0
        self.processing_results = []
        
        # J-Quants APIの状況確認
        api_status = self.fetcher.get_api_status()
        if not api_status['available']:
            return {
                'success': False,
                'message': f'J-Quants APIが利用できません: {api_status["message"]}',
                'summary': {'total': 0, 'success': 0, 'error': 0, 'skipped': 0}
            }
        
        logger.info(f"J-Quants API状況: {api_status['message']} (プラン: {api_status['plan']})")
        
        # 企業一覧を取得
        companies = self.get_all_companies()
        
        if not companies:
            return {
                'success': False,
                'message': '処理対象の企業が見つかりません',
                'summary': {'total': 0, 'success': 0, 'error': 0, 'skipped': 0}
            }
        
        # 処理する企業数を制限
        if max_companies:
            companies = companies[:max_companies]
        
        logger.info(f"J-Quants API株価データ一括処理開始: {len(companies)}社")
        
        # 各企業を処理
        for i, company in enumerate(companies):
            logger.info(f"処理中 ({i+1}/{len(companies)}): {company['symbol']} - {company['name']}")
            
            result = self.process_company_data(company, force_update, date)
            self.processing_results.append(result)
            
            # 進捗ログ
            if (i + 1) % 5 == 0:  # J-Quants APIはレート制限があるため5件ごと
                logger.info(f"進捗: {i+1}/{len(companies)} 完了 "
                           f"(成功:{self.success_count}, エラー:{self.error_count}, スキップ:{self.skip_count})")
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        summary = {
            'total': len(companies),
            'success': self.success_count,
            'error': self.error_count,
            'skipped': self.skip_count,
            'processing_time_seconds': processing_time,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'api_status': api_status
        }
        
        logger.info(f"J-Quants API株価データ一括処理完了: {summary}")
        
        return {
            'success': True,
            'message': f'{len(companies)}社の処理が完了しました（J-Quants API使用）',
            'summary': summary,
            'details': self.processing_results
        }
    
    def get_processing_summary(self) -> Dict[str, Any]:
        """最後の処理結果のサマリーを取得"""
        return {
            'total_processed': len(self.processing_results),
            'success': self.success_count,
            'error': self.error_count,
            'skipped': self.skip_count,
            'success_rate': self.success_count / len(self.processing_results) if self.processing_results else 0,
            'data_source': 'j_quants'
        }
