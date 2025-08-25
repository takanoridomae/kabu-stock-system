from flask import Blueprint, request, jsonify
from datetime import datetime
import json
import os
import sys

# プロジェクトルートをパスに追加
from backend.utils.path_utils import setup_project_path
setup_project_path()

# データベースモデルのインポート
from backend.models.database import (
    company_model, stock_price_model, financial_metrics_model,
    price_statistics_model, technical_indicators_model, db_manager
)

# APIブループリントの作成
api = Blueprint('api', __name__, url_prefix='/api')

@api.route('/companies', methods=['GET'])
def get_companies():
    """企業一覧を取得"""
    try:
        companies = company_model.search()
        return jsonify({
            'success': True,
            'data': [dict(company) for company in companies],
            'count': len(companies)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/companies/search', methods=['POST'])
def search_companies():
    """企業検索"""
    try:
        data = request.get_json() or {}
        
        symbol = data.get('symbol', '')
        company_name = data.get('company_name', '')
        sector = data.get('sector', '')
        
        # 基本的な企業検索
        companies = company_model.search(symbol=symbol, name=company_name, sector=sector)
        
        # 各企業の詳細情報を追加
        detailed_companies = []
        for company in companies:
            company_data = dict(company)
            
            # 最新株価を取得
            latest_price = stock_price_model.get_latest_price(company['id'])
            if latest_price:
                company_data['current_price'] = latest_price['price']
                company_data['price_date'] = latest_price['price_date']
                company_data['volume'] = latest_price['volume']
            else:
                company_data['current_price'] = None
                company_data['price_date'] = None
                company_data['volume'] = None
            
            # 最新財務指標を取得
            latest_metrics = financial_metrics_model.get_latest_metrics(company['id'])
            if latest_metrics:
                company_data['pbr'] = latest_metrics['pbr']
                company_data['per'] = latest_metrics['per']
                company_data['equity_ratio'] = latest_metrics['equity_ratio']
                company_data['roe'] = latest_metrics['roe']
                company_data['roa'] = latest_metrics['roa']
                company_data['report_date'] = latest_metrics['report_date']
            else:
                company_data.update({
                    'pbr': None, 'per': None, 'equity_ratio': None,
                    'roe': None, 'roa': None, 'report_date': None
                })
            
            # 価格統計を取得
            current_month = datetime.now().strftime('%Y-%m')
            current_year = datetime.now().strftime('%Y')
            
            monthly_stats = price_statistics_model.get_statistics(company['id'], 'monthly')
            yearly_stats = price_statistics_model.get_statistics(company['id'], 'yearly')
            all_time_stats = price_statistics_model.get_statistics(company['id'], 'all_time')
            
            # 統計データを追加
            company_data['monthly_min'] = None
            company_data['monthly_max'] = None
            company_data['yearly_min'] = None
            company_data['yearly_max'] = None
            company_data['all_time_min'] = None
            company_data['all_time_max'] = None
            
            for stat in monthly_stats:
                if stat['period_value'] == current_month:
                    company_data['monthly_min'] = stat['min_price']
                    company_data['monthly_max'] = stat['max_price']
                    break
            
            for stat in yearly_stats:
                if stat['period_value'] == current_year:
                    company_data['yearly_min'] = stat['min_price']
                    company_data['yearly_max'] = stat['max_price']
                    break
            
            for stat in all_time_stats:
                if stat['period_value'] == 'all':
                    company_data['all_time_min'] = stat['min_price']
                    company_data['all_time_max'] = stat['max_price']
                    break
            
            detailed_companies.append(company_data)
        
        return jsonify({
            'success': True,
            'data': detailed_companies,
            'count': len(detailed_companies)
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/companies/<int:company_id>', methods=['GET'])
def get_company_detail(company_id):
    """企業詳細情報を取得"""
    try:
        company = company_model.get_by_id(company_id)
        if not company:
            return jsonify({
                'success': False,
                'error': '企業が見つかりません'
            }), 404
        
        company_data = dict(company)
        
        # 株価履歴
        price_history = stock_price_model.get_price_history(company_id, 30)
        company_data['price_history'] = [dict(price) for price in price_history]
        
        # 財務指標
        latest_metrics = financial_metrics_model.get_latest_metrics(company_id)
        company_data['financial_metrics'] = dict(latest_metrics) if latest_metrics else None
        
        # テクニカル指標
        latest_indicators = technical_indicators_model.get_latest_indicators(company_id)
        company_data['technical_indicators'] = dict(latest_indicators) if latest_indicators else None
        
        # 価格統計
        statistics = price_statistics_model.get_statistics(company_id)
        company_data['price_statistics'] = [dict(stat) for stat in statistics]
        
        return jsonify({
            'success': True,
            'data': company_data
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/companies/register', methods=['POST'])
def register_company():
    """企業情報を登録"""
    try:
        data = request.get_json()
        
        if not data.get('symbol') or not data.get('name'):
            return jsonify({
                'success': False,
                'error': '企業コードと企業名は必須です'
            }), 400
        
        # 企業情報の登録/更新
        existing_company = company_model.get_by_symbol(data['symbol'])
        if existing_company:
            company_id = existing_company['id']
            company_model.update(company_id, **{
                k: v for k, v in data.items() 
                if k in ['name', 'sector', 'market']
            })
        else:
            company_id = company_model.create(
                data['symbol'], data['name'],
                data.get('sector', ''), data.get('market', '')
            )
        
        # 株価情報の登録（旧形式：下位互換性のため）
        if 'price' in data:
            stock_price_model.create(
                company_id, data['price'],
                data.get('price_date'), data.get('volume', 0)
            )
            
            # 価格統計の更新
            current_month = datetime.now().strftime('%Y-%m')
            current_year = datetime.now().strftime('%Y')
            
            price_statistics_model.update_statistics(company_id, 'monthly', current_month)
            price_statistics_model.update_statistics(company_id, 'yearly', current_year)
            price_statistics_model.update_statistics(company_id, 'all_time', 'all')
        
        # 財務指標の登録（旧形式：下位互換性のため）
        financial_fields = ['pbr', 'per', 'equity_ratio', 'roe', 'roa']
        if any(field in data for field in financial_fields):
            metrics = {field: data.get(field) for field in financial_fields}
            financial_metrics_model.create(
                company_id, data.get('report_date'), **metrics
            )
        
        # テクニカル指標の登録（旧形式：下位互換性のため）
        technical_fields = ['rsi', 'macd', 'sma_25', 'sma_75', 'bollinger_upper', 'bollinger_lower']
        if any(field in data for field in technical_fields):
            indicators = {field: data.get(field) for field in technical_fields}
            technical_indicators_model.create(
                company_id, data.get('indicator_date'), **indicators
            )
        
        return jsonify({
            'success': True,
            'message': '企業データが正常に登録されました',
            'company_id': company_id
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/data/stock_price/safe', methods=['POST'])
def add_stock_price_safe():
    """株価データを安全に追加（重複チェック付き）"""
    try:
        data = request.get_json()
        
        # 必須パラメータのチェック
        required_fields = ['company_id', 'price']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'{field}は必須です'
                }), 400
        
        # 安全なデータ投入
        result = stock_price_model.create_or_update(
            data['company_id'],
            data['price'],
            data.get('price_date'),
            data.get('volume', 0)
        )
        
        response_data = {
            'success': True,
            'result': result
        }
        
        # 新規作成の場合は価格統計も更新
        if result['status'] == 'created':
            company_id = data['company_id']
            price_date = data.get('price_date') or datetime.now().date()
            
            if isinstance(price_date, str):
                from datetime import datetime as dt
                price_date = dt.strptime(price_date, '%Y-%m-%d').date()
            
            current_month = price_date.strftime('%Y-%m')
            current_year = price_date.strftime('%Y')
            
            price_statistics_model.update_statistics(company_id, 'monthly', current_month)
            price_statistics_model.update_statistics(company_id, 'yearly', current_year)
            price_statistics_model.update_statistics(company_id, 'all_time', 'all')
            
            response_data['statistics_updated'] = True
        
        return jsonify(response_data)
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/data/financial_metrics/safe', methods=['POST'])
def add_financial_metrics_safe():
    """財務指標データを安全に追加（重複チェック付き）"""
    try:
        data = request.get_json()
        
        # 必須パラメータのチェック
        if 'company_id' not in data:
            return jsonify({
                'success': False,
                'error': 'company_idは必須です'
            }), 400
        
        # 財務指標フィールドのチェック
        financial_fields = ['pbr', 'per', 'equity_ratio', 'roe', 'roa']
        metrics = {field: data.get(field) for field in financial_fields if field in data}
        
        if not metrics:
            return jsonify({
                'success': False,
                'error': '少なくとも一つの財務指標が必要です'
            }), 400
        
        # 安全なデータ投入
        result = financial_metrics_model.create_or_update(
            data['company_id'],
            data.get('report_date'),
            **metrics
        )
        
        return jsonify({
            'success': True,
            'result': result
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/data/technical_indicators/safe', methods=['POST'])
def add_technical_indicators_safe():
    """テクニカル指標データを安全に追加（重複チェック付き）"""
    try:
        data = request.get_json()
        
        # 必須パラメータのチェック
        if 'company_id' not in data:
            return jsonify({
                'success': False,
                'error': 'company_idは必須です'
            }), 400
        
        # テクニカル指標フィールドのチェック
        technical_fields = ['rsi', 'macd', 'sma_25', 'sma_75', 'bollinger_upper', 'bollinger_lower']
        indicators = {field: data.get(field) for field in technical_fields if field in data}
        
        if not indicators:
            return jsonify({
                'success': False,
                'error': '少なくとも一つのテクニカル指標が必要です'
            }), 400
        
        # 安全なデータ投入
        result = technical_indicators_model.create_or_update(
            data['company_id'],
            data.get('indicator_date'),
            **indicators
        )
        
        return jsonify({
            'success': True,
            'result': result
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/data/force_update/stock_price', methods=['PUT'])
def force_update_stock_price():
    """株価データを強制更新（データ修正用）"""
    try:
        data = request.get_json()
        
        # 必須パラメータのチェック
        required_fields = ['company_id', 'price_date', 'price']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'{field}は必須です'
                }), 400
        
        # 既存データの確認
        existing = stock_price_model.get_conflicting_data(
            data['company_id'], data['price_date']
        )
        
        if not existing:
            return jsonify({
                'success': False,
                'error': '更新対象のデータが見つかりません'
            }), 404
        
        # 強制更新
        rows_updated = stock_price_model.force_update(
            data['company_id'],
            data['price'],
            data['price_date'],
            data.get('volume', 0)
        )
        
        return jsonify({
            'success': True,
            'message': f'{rows_updated}件のデータを更新しました',
            'rows_updated': rows_updated
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/export', methods=['GET'])
def export_data():
    """データベースのJSONエクスポート"""
    try:
        # 全テーブルのデータを取得
        tables = ['companies', 'stock_prices', 'financial_metrics', 'price_statistics', 'technical_indicators']
        export_data = {}
        
        for table in tables:
            query = f"SELECT * FROM {table}"
            rows = db_manager.execute_query(query)
            export_data[table] = [dict(row) for row in rows]
        
        # JSONファイルとして保存
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'kabu_data_export_{timestamp}.json'
        filepath = os.path.join('jsonfile', filename)
        
        os.makedirs('jsonfile', exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
        
        return jsonify({
            'success': True,
            'message': f'データが {filename} にエクスポートされました',
            'filename': filename,
            'export_data': export_data
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/import', methods=['POST'])
def import_data():
    """JSONデータのインポート"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'インポートするデータがありません'
            }), 400
        
        imported_counts = {}
        
        # 企業データのインポート
        if 'companies' in data:
            count = 0
            for company_data in data['companies']:
                try:
                    company_model.create(
                        company_data['symbol'], company_data['name'],
                        company_data.get('sector', ''), company_data.get('market', '')
                    )
                    count += 1
                except:
                    # 重複の場合は更新
                    existing = company_model.get_by_symbol(company_data['symbol'])
                    if existing:
                        company_model.update(existing['id'], **{
                            k: v for k, v in company_data.items()
                            if k in ['name', 'sector', 'market']
                        })
                        count += 1
            imported_counts['companies'] = count
        
        # 株価データのインポート
        if 'stock_prices' in data:
            count = 0
            for price_data in data['stock_prices']:
                try:
                    stock_price_model.create(
                        price_data['company_id'], price_data['price'],
                        price_data['price_date'], price_data.get('volume', 0)
                    )
                    count += 1
                except:
                    pass  # 重複は無視
            imported_counts['stock_prices'] = count
        
        # 財務指標データのインポート
        if 'financial_metrics' in data:
            count = 0
            for metrics_data in data['financial_metrics']:
                try:
                    metrics = {k: v for k, v in metrics_data.items() 
                             if k in ['pbr', 'per', 'equity_ratio', 'roe', 'roa']}
                    financial_metrics_model.create(
                        metrics_data['company_id'],
                        metrics_data['report_date'],
                        **metrics
                    )
                    count += 1
                except:
                    pass  # 重複は無視
            imported_counts['financial_metrics'] = count
        
        return jsonify({
            'success': True,
            'message': 'データが正常にインポートされました',
            'imported_counts': imported_counts
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/stock-data/fetch', methods=['POST'])
def fetch_stock_data():
    """株価・財務データの手動取得"""
    try:
        # 株価データ処理モジュールのインポート
        from backend.utils.stock_batch_processor import StockBatchProcessor
        
        data = request.get_json()
        force_update = data.get('force_update', False) if data else False
        max_companies = data.get('max_companies') if data else None
        specific_symbols = data.get('symbols', []) if data else []
        
        processor = StockBatchProcessor()
        
        # 特定の企業コードが指定された場合
        if specific_symbols:
            results = []
            companies = []
            
            # 指定されたシンボルの企業情報を取得
            for symbol in specific_symbols:
                company = company_model.get_by_symbol(symbol)
                if company:
                    companies.append(dict(company))
                else:
                    results.append({
                        'symbol': symbol,
                        'status': 'error',
                        'message': f'企業コード {symbol} は登録されていません'
                    })
            
            # 見つかった企業を処理
            for company in companies:
                result = processor.process_company_data(company, force_update)
                results.append(result)
            
            summary = {
                'total': len(specific_symbols),
                'found_companies': len(companies),
                'success': sum(1 for r in results if r.get('status') == 'success'),
                'error': sum(1 for r in results if r.get('status') == 'error'),
                'skipped': sum(1 for r in results if r.get('status') == 'skipped')
            }
            
            return jsonify({
                'success': True,
                'message': f'{len(specific_symbols)}件の企業データ取得処理が完了しました',
                'summary': summary,
                'details': results
            })
        
        # 全企業の一括処理
        else:
            result = processor.process_all_companies(force_update, max_companies)
            return jsonify(result)
            
    except ImportError as e:
        return jsonify({
            'success': False,
            'error': '株価データ取得モジュールの読み込みに失敗しました',
            'details': str(e)
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/stock-data/fetch/<symbol>', methods=['POST'])
def fetch_single_stock_data(symbol):
    """単一企業の株価・財務データ取得"""
    try:
        from backend.utils.stock_batch_processor import StockBatchProcessor
        
        data = request.get_json()
        force_update = data.get('force_update', False) if data else False
        
        # 企業情報の確認
        company = company_model.get_by_symbol(symbol)
        if not company:
            return jsonify({
                'success': False,
                'error': f'企業コード {symbol} は登録されていません'
            }), 404
        
        processor = StockBatchProcessor()
        result = processor.process_company_data(dict(company), force_update)
        
        return jsonify({
            'success': result['status'] == 'success',
            'message': result['message'],
            'data': result
        })
        
    except ImportError as e:
        return jsonify({
            'success': False,
            'error': '株価データ取得モジュールの読み込みに失敗しました',
            'details': str(e)
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/stock-data/status', methods=['GET'])
def get_stock_data_status():
    """株価データの更新状況を確認"""
    try:
        companies = company_model.search()
        total_companies = len(companies)
        
        status_info = {
            'total_companies': total_companies,
            'companies_with_price_data': 0,
            'companies_with_financial_data': 0,
            'last_updated': None,
            'companies_need_update': 0
        }
        
        from datetime import datetime, timedelta
        cutoff_date = datetime.now() - timedelta(days=1)
        
        for company in companies:
            company_dict = dict(company)
            company_id = company_dict['id']
            
            # 株価データの確認
            latest_price = stock_price_model.get_latest_price(company_id)
            if latest_price:
                status_info['companies_with_price_data'] += 1
                
                price_date = datetime.fromisoformat(latest_price['price_date'])
                if not status_info['last_updated'] or price_date > datetime.fromisoformat(status_info['last_updated']):
                    status_info['last_updated'] = price_date.isoformat()
                
                if price_date.date() < cutoff_date.date():
                    status_info['companies_need_update'] += 1
            else:
                status_info['companies_need_update'] += 1
            
            # 財務データの確認
            financial_data = financial_metrics_model.get_latest_metrics(company_id)
            if financial_data:
                status_info['companies_with_financial_data'] += 1
        
        return jsonify({
            'success': True,
            'data': status_info
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/jquants-data/fetch', methods=['POST'])
def fetch_jquants_data():
    """J-Quants API株価・財務データの手動取得"""
    try:
        # J-Quants株価データ処理モジュールのインポート
        from backend.utils.jquants_batch_processor import JQuantsBatchProcessor
        
        data = request.get_json()
        force_update = data.get('force_update', False) if data else False
        max_companies = data.get('max_companies') if data else None
        specific_symbols = data.get('symbols', []) if data else []
        target_date = data.get('date') if data else None  # 特定日付の指定
        
        # 認証情報の取得（環境変数、リクエスト、または保存済みトークンから）
        email = data.get('email') if data else None
        password = data.get('password') if data else None
        refresh_token = data.get('refresh_token') if data else None
        
        # 認証情報がない場合、保存済みトークンを自動使用
        if not refresh_token and not (email and password):
            logger.info("認証情報が提供されていません。保存済みトークンを使用します")
        
        processor = JQuantsBatchProcessor(email, password, refresh_token)
        
        # 特定の企業コードが指定された場合
        if specific_symbols:
            results = []
            companies = []
            
            # 指定されたシンボルの企業情報を取得
            for symbol in specific_symbols:
                company = company_model.get_by_symbol(symbol)
                if company:
                    companies.append(dict(company))
                else:
                    results.append({
                        'symbol': symbol,
                        'status': 'error',
                        'message': f'企業コード {symbol} は登録されていません'
                    })
            
            # 見つかった企業を処理
            for company in companies:
                result = processor.process_company_data(company, force_update, target_date)
                results.append(result)
            
            summary = {
                'total': len(specific_symbols),
                'found_companies': len(companies),
                'success': sum(1 for r in results if r.get('status') == 'success'),
                'error': sum(1 for r in results if r.get('status') == 'error'),
                'skipped': sum(1 for r in results if r.get('status') == 'skipped')
            }
            
            return jsonify({
                'success': True,
                'message': f'{len(specific_symbols)}件の企業データ取得処理が完了しました（J-Quants API使用）',
                'summary': summary,
                'details': results
            })
        
        # 全企業の一括処理
        else:
            result = processor.process_all_companies(force_update, max_companies, target_date)
            return jsonify(result)
            
    except ImportError as e:
        return jsonify({
            'success': False,
            'error': 'J-Quants APIデータ取得モジュールの読み込みに失敗しました',
            'details': str(e)
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/jquants-data/fetch/<symbol>', methods=['POST'])
def fetch_single_jquants_data(symbol):
    """単一企業のJ-Quants API株価・財務データ取得"""
    try:
        from backend.utils.jquants_batch_processor import JQuantsBatchProcessor
        
        data = request.get_json()
        force_update = data.get('force_update', False) if data else False
        target_date = data.get('date') if data else None
        
        # 認証情報の取得
        email = data.get('email') if data else None
        password = data.get('password') if data else None
        refresh_token = data.get('refresh_token') if data else None
        
        # 企業情報の確認
        company = company_model.get_by_symbol(symbol)
        if not company:
            return jsonify({
                'success': False,
                'error': f'企業コード {symbol} は登録されていません'
            }), 404
        
        processor = JQuantsBatchProcessor(email, password, refresh_token)
        result = processor.process_company_data(dict(company), force_update, target_date)
        
        return jsonify({
            'success': result['status'] == 'success',
            'message': result['message'],
            'data': result
        })
        
    except ImportError as e:
        return jsonify({
            'success': False,
            'error': 'J-Quants APIデータ取得モジュールの読み込みに失敗しました',
            'details': str(e)
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/jquants-data/status', methods=['GET'])
def get_jquants_status():
    """J-Quants APIの利用状況を確認"""
    try:
        from backend.utils.jquants_data_fetcher import JQuantsDataFetcher
        
        # 認証情報なしでステータスのみ確認
        fetcher = JQuantsDataFetcher()
        status = fetcher.get_api_status()
        
        return jsonify({
            'success': True,
            'data': status
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/jquants-data/test-auth', methods=['POST'])
def test_jquants_auth():
    """J-Quants API認証テスト（デバッグ用）"""
    try:
        from backend.utils.jquants_data_fetcher import JQuantsDataFetcher
        
        data = request.get_json()
        refresh_token = data.get('refresh_token')
        email = data.get('email')
        password = data.get('password')
        
        # 認証情報がない場合、保存済みトークンを自動使用
        if not refresh_token and not (email and password):
            logger.info("認証情報が提供されていません。保存済みトークンを使用します")
        
        # 認証テスト（空の場合は自動的に保存済みトークンを読み込み）
        fetcher = JQuantsDataFetcher(email, password, refresh_token)
        
        # 初期化（認証）を実行
        auth_result = fetcher._initialize_client()
        
        if auth_result:
            # 認証成功時、簡単なデータ取得テストも実行
            test_symbol = "7203"  # トヨタ
            test_date = fetcher._get_latest_business_date()
            
            stock_data = fetcher._get_daily_quotes(test_symbol, test_date)
            
            return jsonify({
                'success': True,
                'message': 'J-Quants API認証成功',
                'auth_status': {
                    'authenticated': fetcher.is_authenticated,
                    'id_token_length': len(fetcher.id_token) if fetcher.id_token else 0
                },
                'test_data': {
                    'symbol': test_symbol,
                    'date': test_date,
                    'data_available': stock_data is not None,
                    'data': stock_data if stock_data else None
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': 'J-Quants API認証に失敗しました',
                'auth_status': {
                    'authenticated': fetcher.is_authenticated,
                    'id_token_length': 0
                }
            }), 401
            
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': f'認証テスト中にエラーが発生しました: {str(e)}',
            'traceback': traceback.format_exc()
        }), 500

@api.route('/jquants-data/validate-token', methods=['POST'])
def validate_jquants_token():
    """J-Quants APIリフレッシュトークンの形式チェック"""
    try:
        data = request.get_json()
        refresh_token = data.get('refresh_token', '')
        
        # トークンの基本チェック
        checks = {
            'length': len(refresh_token),
            'not_empty': bool(refresh_token.strip()),
            'no_spaces': ' ' not in refresh_token,
            'alphanumeric_check': refresh_token.replace('-', '').replace('_', '').isalnum(),
            'min_length': len(refresh_token) >= 32,
            'max_length': len(refresh_token) <= 512
        }
        
        # J-Quants APIの実際の形式チェック（実測値に基づく）
        suspected_issues = []
        
        if not checks['not_empty']:
            suspected_issues.append('トークンが空です')
        
        if checks['length'] < 100:
            suspected_issues.append('トークンが短すぎます（100文字未満）')
        
        if checks['length'] > 2500:
            suspected_issues.append('トークンが長すぎます（2500文字超過）')
        
        if not checks['no_spaces']:
            suspected_issues.append('トークンにスペースが含まれています')
        
        # J-Quants特有のJWT形式チェック
        if not refresh_token.startswith('eyJ'):
            suspected_issues.append('JWTトークンの開始文字列が正しくありません')
        
        # 一般的なJWTトークンの形式チェック
        jwt_parts = refresh_token.count('.')
        is_jwt_like = jwt_parts == 2
        
        return jsonify({
            'success': True,
            'token_info': {
                'length': checks['length'],
                'valid_format': len(suspected_issues) == 0,
                'is_jwt_like': is_jwt_like,
                'jwt_parts': jwt_parts + 1 if jwt_parts >= 0 else 0,
                'first_20_chars': refresh_token[:20] if refresh_token else '',
                'last_20_chars': refresh_token[-20:] if len(refresh_token) >= 20 else '',
                'suspected_issues': suspected_issues,
                'checks': checks
            },
            'recommendations': [
                '1. J-Quants APIポータルサイトでリフレッシュトークンを再確認',
                '2. コピー時にスペースや改行が入っていないか確認',
                '3. トークンの有効期限（1週間）を確認',
                '4. アカウントの利用制限状況を確認',
                '5. トークンが1500-2000文字程度であることは正常です'
            ]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/jquants-token/save', methods=['POST'])
def save_jquants_token():
    """J-Quants APIリフレッシュトークンを保存"""
    try:
        from backend.utils.token_manager import JQuantsTokenManager
        
        data = request.get_json()
        refresh_token = data.get('refresh_token')
        plan_type = data.get('plan_type', 'Standard')
        user_identifier = data.get('user_identifier', 'default')
        
        if not refresh_token:
            return jsonify({
                'success': False,
                'error': 'リフレッシュトークンが提供されていません'
            }), 400
        
        token_manager = JQuantsTokenManager()
        success = token_manager.save_refresh_token(refresh_token, user_identifier, plan_type)
        
        if success:
            expiry_info = token_manager.check_token_expiry(user_identifier)
            return jsonify({
                'success': True,
                'message': 'リフレッシュトークンを保存しました',
                'expiry_info': expiry_info
            })
        else:
            return jsonify({
                'success': False,
                'error': 'トークンの保存に失敗しました'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/jquants-token/status', methods=['GET'])
def get_jquants_token_status():
    """J-Quants APIトークンの状況を確認"""
    try:
        from backend.utils.token_manager import JQuantsTokenManager
        
        user_identifier = request.args.get('user_identifier', 'default')
        token_manager = JQuantsTokenManager()
        
        # トークンの有効期限チェック
        expiry_info = token_manager.check_token_expiry(user_identifier)
        
        # 保存されているトークン情報を取得
        token_info = token_manager.get_refresh_token(user_identifier)
        
        result = {
            'expiry_info': expiry_info,
            'has_saved_token': token_info is not None
        }
        
        if token_info:
            result['token_info'] = {
                'plan_type': token_info.get('plan_type'),
                'created_at': token_info.get('created_at'),
                'expires_at': token_info.get('expires_at'),
                'last_used_at': token_info.get('last_used_at')
            }
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/files/list', methods=['GET'])
def list_data_files():
    """jsonfileディレクトリ内のファイル一覧を取得"""
    try:
        jsonfile_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'jsonfile')
        
        if not os.path.exists(jsonfile_dir):
            return jsonify({
                'success': True,
                'data': [],
                'message': 'jsonfileディレクトリが見つかりません'
            })
        
        files = []
        for filename in os.listdir(jsonfile_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(jsonfile_dir, filename)
                file_stats = os.stat(filepath)
                
                files.append({
                    'filename': filename,
                    'size': file_stats.st_size,
                    'modified_date': datetime.fromtimestamp(file_stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                    'created_date': datetime.fromtimestamp(file_stats.st_ctime).strftime('%Y-%m-%d %H:%M:%S')
                })
        
        # 更新日時でソート（新しい順）
        files.sort(key=lambda x: x['modified_date'], reverse=True)
        
        return jsonify({
            'success': True,
            'data': files,
            'count': len(files)
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/files/load/<filename>', methods=['GET'])
def load_data_file(filename):
    """指定されたJSONファイルの内容を読み込み"""
    try:
        # セキュリティ: ファイル名の検証（パストラバーサル攻撃防止）
        if not filename or '..' in filename or '/' in filename or '\\' in filename:
            return jsonify({
                'success': False,
                'error': '無効なファイル名です'
            }), 400
        
        if not filename.endswith('.json'):
            return jsonify({
                'success': False,
                'error': 'JSONファイルのみ読み込み可能です'
            }), 400
        
        jsonfile_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'jsonfile')
        filepath = os.path.join(jsonfile_dir, filename)
        
        if not os.path.exists(filepath):
            return jsonify({
                'success': False,
                'error': 'ファイルが見つかりません'
            }), 404
        
        # ファイルサイズチェック（10MB制限）
        file_size = os.path.getsize(filepath)
        if file_size > 10 * 1024 * 1024:  # 10MB
            return jsonify({
                'success': False,
                'error': 'ファイルサイズが大きすぎます（最大10MB）'
            }), 413
        
        # JSONファイルを読み込み
        with open(filepath, 'r', encoding='utf-8') as f:
            file_content = json.load(f)
        
        # ファイル情報も含めて返す
        file_stats = os.stat(filepath)
        
        return jsonify({
            'success': True,
            'data': file_content,
            'file_info': {
                'filename': filename,
                'size': file_stats.st_size,
                'modified_date': datetime.fromtimestamp(file_stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                'created_date': datetime.fromtimestamp(file_stats.st_ctime).strftime('%Y-%m-%d %H:%M:%S')
            }
        })
    
    except json.JSONDecodeError as e:
        return jsonify({
            'success': False,
            'error': f'JSONファイルの解析に失敗しました: {str(e)}'
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api.route('/files/load-and-import/<filename>', methods=['POST'])
def load_and_import_file(filename):
    """ファイル読み込みと同時にデータベースにインポート"""
    try:
        # まずファイルを読み込み
        load_response = load_data_file(filename)
        load_data = json.loads(load_response.data)
        
        if not load_data['success']:
            return load_response
        
        # インポート処理を実行
        file_content = load_data['data']
        
        imported_counts = {}
        
        # 企業データのインポート
        if 'companies' in file_content:
            count = 0
            for company_data in file_content['companies']:
                try:
                    company_model.create(
                        company_data['symbol'], company_data['name'],
                        company_data.get('sector', ''), company_data.get('market', '')
                    )
                    count += 1
                except:
                    # 重複の場合は更新
                    existing = company_model.get_by_symbol(company_data['symbol'])
                    if existing:
                        company_model.update(existing['id'], **{
                            k: v for k, v in company_data.items()
                            if k in ['name', 'sector', 'market']
                        })
                        count += 1
            imported_counts['companies'] = count
        
        # 株価データのインポート
        if 'stock_prices' in file_content:
            count = 0
            for price_data in file_content['stock_prices']:
                try:
                    stock_price_model.create(
                        price_data['company_id'], price_data['price'],
                        price_data['price_date'], price_data.get('volume', 0)
                    )
                    count += 1
                except:
                    pass  # 重複は無視
            imported_counts['stock_prices'] = count
        
        # 財務指標データのインポート
        if 'financial_metrics' in file_content:
            count = 0
            for metrics_data in file_content['financial_metrics']:
                try:
                    metrics = {k: v for k, v in metrics_data.items() 
                             if k in ['pbr', 'per', 'equity_ratio', 'roe', 'roa']}
                    financial_metrics_model.create(
                        metrics_data['company_id'],
                        metrics_data['report_date'],
                        **metrics
                    )
                    count += 1
                except:
                    pass  # 重複は無視
            imported_counts['financial_metrics'] = count
        
        return jsonify({
            'success': True,
            'message': f'{filename} が正常に読み込まれ、データベースにインポートされました',
            'file_info': load_data['file_info'],
            'imported_counts': imported_counts
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
