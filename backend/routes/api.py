from flask import Blueprint, request, jsonify
from datetime import datetime
import json
import os
import sys

# プロジェクトルートをパスに追加
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

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
