"""
API共通ヘルパー関数
"""
from functools import wraps
from flask import jsonify
from typing import Callable, Any, Tuple, Dict


class ValidationError(Exception):
    """バリデーションエラー"""
    pass


class BusinessLogicError(Exception):
    """ビジネスロジックエラー"""
    pass


def create_success_response(data: Any = None, message: str = None, **kwargs) -> Dict:
    """
    成功レスポンスを作成
    
    Args:
        data: レスポンスデータ
        message: 成功メッセージ
        **kwargs: 追加のレスポンスフィールド
        
    Returns:
        Dict: 標準化されたレスポンス
    """
    response = {
        'success': True
    }
    
    if data is not None:
        response['data'] = data
    
    if message:
        response['message'] = message
    
    response.update(kwargs)
    return response


def create_error_response(error: str, code: int = 500, **kwargs) -> Tuple[Dict, int]:
    """
    エラーレスポンスを作成
    
    Args:
        error: エラーメッセージ
        code: HTTPステータスコード
        **kwargs: 追加のレスポンスフィールド
        
    Returns:
        Tuple[Dict, int]: レスポンスとステータスコード
    """
    response = {
        'success': False,
        'error': error,
        'code': code
    }
    
    response.update(kwargs)
    return response, code


def handle_api_error(error: Exception, default_status: int = 500) -> Tuple[Dict, int]:
    """
    API例外を適切なレスポンスに変換
    
    Args:
        error: 発生した例外
        default_status: デフォルトのHTTPステータスコード
        
    Returns:
        Tuple[Dict, int]: エラーレスポンスとステータスコード
    """
    if isinstance(error, ValidationError):
        return create_error_response(str(error), 400)
    elif isinstance(error, BusinessLogicError):
        return create_error_response(str(error), 422)
    elif isinstance(error, ValueError):
        return create_error_response(f"無効な値です: {str(error)}", 400)
    elif isinstance(error, KeyError):
        return create_error_response(f"必須フィールドが不足しています: {str(error)}", 400)
    else:
        return create_error_response(f"サーバーエラーが発生しました: {str(error)}", default_status)


def api_error_handler(func: Callable) -> Callable:
    """
    API関数のエラーハンドリングデコレータ
    
    Args:
        func: デコレートする関数
        
    Returns:
        Callable: エラーハンドリングが追加された関数
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            # 結果がタプルでない場合（レスポンスのみ）、jsonify()を適用
            if not isinstance(result, tuple):
                return jsonify(result)
            return result
        except Exception as e:
            error_response, status_code = handle_api_error(e)
            return jsonify(error_response), status_code
    
    return wrapper


def validate_required_fields(data: Dict, required_fields: list) -> None:
    """
    必須フィールドのバリデーション
    
    Args:
        data: バリデーション対象のデータ
        required_fields: 必須フィールドのリスト
        
    Raises:
        ValidationError: 必須フィールドが不足している場合
    """
    missing_fields = []
    
    for field in required_fields:
        if field not in data or data[field] is None or data[field] == '':
            missing_fields.append(field)
    
    if missing_fields:
        raise ValidationError(f"以下の必須フィールドが不足しています: {', '.join(missing_fields)}")


def validate_json_request(func: Callable) -> Callable:
    """
    JSONリクエストのバリデーションデコレータ
    
    Args:
        func: デコレートする関数
        
    Returns:
        Callable: JSONバリデーションが追加された関数
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        from flask import request
        
        if not request.is_json:
            error_response, status_code = create_error_response(
                "Content-Type must be application/json", 400
            )
            return jsonify(error_response), status_code
        
        data = request.get_json()
        if not data:
            error_response, status_code = create_error_response(
                "リクエストボディが空または無効なJSONです", 400
            )
            return jsonify(error_response), status_code
        
        return func(*args, **kwargs)
    
    return wrapper


def paginate_response(data: list, page: int = 1, per_page: int = 20) -> Dict:
    """
    ページネーション付きレスポンスを作成
    
    Args:
        data: ページネーション対象のデータ
        page: ページ番号（1から開始）
        per_page: ページあたりのアイテム数
        
    Returns:
        Dict: ページネーション情報付きのレスポンス
    """
    total = len(data)
    start = (page - 1) * per_page
    end = start + per_page
    
    paginated_data = data[start:end]
    
    return create_success_response(
        data=paginated_data,
        pagination={
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page,
            'has_next': end < total,
            'has_prev': page > 1
        }
    )
