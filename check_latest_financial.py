#!/usr/bin/env python3
# 最新財務指標データ確認

from backend.models.database import db_manager

print('=== 最新財務指標データ（トヨタ） ===')

try:
    # 最新の財務指標データを確認
    query = '''
    SELECT * FROM financial_metrics 
    WHERE company_id = 1 
    ORDER BY report_date DESC, id DESC 
    LIMIT 5
    '''
    results = db_manager.execute_query(query)

    for row in results:
        print(f'ID: {row["id"]}, Date: {row["report_date"]}, PBR: {row["pbr"]}, PER: {row["per"]}, ROE: {row["roe"]}')
    
    print(f'\n=== 全ての財務データ ===')
    all_query = 'SELECT * FROM financial_metrics ORDER BY id DESC LIMIT 10'
    all_results = db_manager.execute_query(all_query)
    
    for row in all_results:
        print(f'ID: {row["id"]}, Company: {row["company_id"]}, Date: {row["report_date"]}, PBR: {row["pbr"]}, PER: {row["per"]}')

except Exception as e:
    print(f'エラー: {e}')
    import traceback
    traceback.print_exc()
