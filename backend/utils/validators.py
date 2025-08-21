"""
データバリデーション機能
"""
import re
from datetime import datetime, date
from typing import Any, Union
from backend.utils.api_helpers import ValidationError


class StockDataValidator:
    """株式データ専用バリデータ"""
    
    @staticmethod
    def validate_price(price: Any) -> float:
        """
        株価のバリデーション
        
        Args:
            price: バリデーション対象の価格
            
        Returns:
            float: バリデーション済みの価格
            
        Raises:
            ValidationError: 価格が無効な場合
        """
        if price is None:
            raise ValidationError("価格は必須です")
        
        try:
            price_float = float(price)
        except (TypeError, ValueError):
            raise ValidationError("価格は数値である必要があります")
        
        if price_float <= 0:
            raise ValidationError("価格は正の数値である必要があります")
        
        if price_float > 1000000:  # 100万円上限
            raise ValidationError("価格は100万円以下である必要があります")
        
        return round(price_float, 2)
    
    @staticmethod
    def validate_volume(volume: Any) -> int:
        """
        出来高のバリデーション
        
        Args:
            volume: バリデーション対象の出来高
            
        Returns:
            int: バリデーション済みの出来高
            
        Raises:
            ValidationError: 出来高が無効な場合
        """
        if volume is None:
            return 0
        
        try:
            volume_int = int(volume)
        except (TypeError, ValueError):
            raise ValidationError("出来高は整数である必要があります")
        
        if volume_int < 0:
            raise ValidationError("出来高は0以上である必要があります")
        
        return volume_int
    
    @staticmethod
    def validate_company_id(company_id: Any) -> int:
        """
        企業IDのバリデーション
        
        Args:
            company_id: バリデーション対象の企業ID
            
        Returns:
            int: バリデーション済みの企業ID
            
        Raises:
            ValidationError: 企業IDが無効な場合
        """
        if company_id is None:
            raise ValidationError("企業IDは必須です")
        
        try:
            company_id_int = int(company_id)
        except (TypeError, ValueError):
            raise ValidationError("企業IDは整数である必要があります")
        
        if company_id_int <= 0:
            raise ValidationError("企業IDは正の整数である必要があります")
        
        return company_id_int
    
    @staticmethod
    def validate_symbol(symbol: Any) -> str:
        """
        企業コード（証券コード）のバリデーション
        
        Args:
            symbol: バリデーション対象の企業コード
            
        Returns:
            str: バリデーション済みの企業コード
            
        Raises:
            ValidationError: 企業コードが無効な場合
        """
        if not symbol:
            raise ValidationError("企業コードは必須です")
        
        symbol_str = str(symbol).strip()
        
        # 日本の証券コードは通常4桁の数字
        if not re.match(r'^\d{4}$', symbol_str):
            raise ValidationError("企業コードは4桁の数字である必要があります")
        
        return symbol_str
    
    @staticmethod
    def validate_company_name(name: Any) -> str:
        """
        企業名のバリデーション
        
        Args:
            name: バリデーション対象の企業名
            
        Returns:
            str: バリデーション済みの企業名
            
        Raises:
            ValidationError: 企業名が無効な場合
        """
        if not name:
            raise ValidationError("企業名は必須です")
        
        name_str = str(name).strip()
        
        if len(name_str) < 2:
            raise ValidationError("企業名は2文字以上である必要があります")
        
        if len(name_str) > 100:
            raise ValidationError("企業名は100文字以下である必要があります")
        
        return name_str
    
    @staticmethod
    def validate_date(date_value: Any, field_name: str = "日付") -> Union[str, None]:
        """
        日付のバリデーション
        
        Args:
            date_value: バリデーション対象の日付
            field_name: フィールド名（エラーメッセージ用）
            
        Returns:
            Union[str, None]: バリデーション済みの日付文字列またはNone
            
        Raises:
            ValidationError: 日付が無効な場合
        """
        if date_value is None:
            return None
        
        if isinstance(date_value, date):
            return date_value.strftime('%Y-%m-%d')
        
        if isinstance(date_value, datetime):
            return date_value.date().strftime('%Y-%m-%d')
        
        if isinstance(date_value, str):
            date_str = date_value.strip()
            if not date_str:
                return None
            
            # YYYY-MM-DD形式をチェック
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
                raise ValidationError(f"{field_name}はYYYY-MM-DD形式である必要があります")
            
            try:
                # 実際に日付として解析できるかチェック
                datetime.strptime(date_str, '%Y-%m-%d')
                return date_str
            except ValueError:
                raise ValidationError(f"{field_name}が無効な日付です")
        
        raise ValidationError(f"{field_name}の形式が正しくありません")


class FinancialMetricsValidator:
    """財務指標専用バリデータ"""
    
    @staticmethod
    def validate_ratio(value: Any, field_name: str, min_val: float = None, max_val: float = None) -> Union[float, None]:
        """
        比率系指標のバリデーション
        
        Args:
            value: バリデーション対象の値
            field_name: フィールド名
            min_val: 最小値
            max_val: 最大値
            
        Returns:
            Union[float, None]: バリデーション済みの値またはNone
            
        Raises:
            ValidationError: 値が無効な場合
        """
        if value is None:
            return None
        
        try:
            value_float = float(value)
        except (TypeError, ValueError):
            raise ValidationError(f"{field_name}は数値である必要があります")
        
        if min_val is not None and value_float < min_val:
            raise ValidationError(f"{field_name}は{min_val}以上である必要があります")
        
        if max_val is not None and value_float > max_val:
            raise ValidationError(f"{field_name}は{max_val}以下である必要があります")
        
        return round(value_float, 4)
    
    @staticmethod
    def validate_pbr(pbr: Any) -> Union[float, None]:
        """PBRのバリデーション"""
        return FinancialMetricsValidator.validate_ratio(pbr, "PBR", min_val=0, max_val=100)
    
    @staticmethod
    def validate_per(per: Any) -> Union[float, None]:
        """PERのバリデーション"""
        return FinancialMetricsValidator.validate_ratio(per, "PER", min_val=0, max_val=1000)
    
    @staticmethod
    def validate_equity_ratio(equity_ratio: Any) -> Union[float, None]:
        """自己資本比率のバリデーション"""
        return FinancialMetricsValidator.validate_ratio(equity_ratio, "自己資本比率", min_val=0, max_val=1)
    
    @staticmethod
    def validate_roe(roe: Any) -> Union[float, None]:
        """ROEのバリデーション"""
        return FinancialMetricsValidator.validate_ratio(roe, "ROE", min_val=-1, max_val=1)
    
    @staticmethod
    def validate_roa(roa: Any) -> Union[float, None]:
        """ROAのバリデーション"""
        return FinancialMetricsValidator.validate_ratio(roa, "ROA", min_val=-1, max_val=1)


class TechnicalIndicatorValidator:
    """テクニカル指標専用バリデータ"""
    
    @staticmethod
    def validate_rsi(rsi: Any) -> Union[float, None]:
        """RSIのバリデーション"""
        if rsi is None:
            return None
        
        try:
            rsi_float = float(rsi)
        except (TypeError, ValueError):
            raise ValidationError("RSIは数値である必要があります")
        
        if not (0 <= rsi_float <= 100):
            raise ValidationError("RSIは0から100の範囲である必要があります")
        
        return round(rsi_float, 4)
    
    @staticmethod
    def validate_price_indicator(value: Any, field_name: str) -> Union[float, None]:
        """価格系テクニカル指標のバリデーション"""
        if value is None:
            return None
        
        try:
            value_float = float(value)
        except (TypeError, ValueError):
            raise ValidationError(f"{field_name}は数値である必要があります")
        
        if value_float <= 0:
            raise ValidationError(f"{field_name}は正の数値である必要があります")
        
        if value_float > 1000000:  # 100万円上限
            raise ValidationError(f"{field_name}は100万円以下である必要があります")
        
        return round(value_float, 2)


def validate_stock_price_data(data: dict) -> dict:
    """
    株価データの包括的バリデーション
    
    Args:
        data: バリデーション対象のデータ
        
    Returns:
        dict: バリデーション済みのデータ
    """
    validator = StockDataValidator()
    
    validated_data = {
        'company_id': validator.validate_company_id(data.get('company_id')),
        'price': validator.validate_price(data.get('price')),
        'volume': validator.validate_volume(data.get('volume', 0)),
        'price_date': validator.validate_date(data.get('price_date'), "価格日付")
    }
    
    return validated_data


def validate_financial_metrics_data(data: dict) -> dict:
    """
    財務指標データの包括的バリデーション
    
    Args:
        data: バリデーション対象のデータ
        
    Returns:
        dict: バリデーション済みのデータ
    """
    stock_validator = StockDataValidator()
    financial_validator = FinancialMetricsValidator()
    
    validated_data = {
        'company_id': stock_validator.validate_company_id(data.get('company_id')),
        'report_date': stock_validator.validate_date(data.get('report_date'), "報告日付"),
        'pbr': financial_validator.validate_pbr(data.get('pbr')),
        'per': financial_validator.validate_per(data.get('per')),
        'equity_ratio': financial_validator.validate_equity_ratio(data.get('equity_ratio')),
        'roe': financial_validator.validate_roe(data.get('roe')),
        'roa': financial_validator.validate_roa(data.get('roa'))
    }
    
    return validated_data


def validate_company_data(data: dict) -> dict:
    """
    企業データの包括的バリデーション
    
    Args:
        data: バリデーション対象のデータ
        
    Returns:
        dict: バリデーション済みのデータ
    """
    validator = StockDataValidator()
    
    validated_data = {
        'symbol': validator.validate_symbol(data.get('symbol')),
        'name': validator.validate_company_name(data.get('name')),
        'sector': str(data.get('sector', '')).strip() if data.get('sector') else '',
        'market': str(data.get('market', '')).strip() if data.get('market') else ''
    }
    
    return validated_data
