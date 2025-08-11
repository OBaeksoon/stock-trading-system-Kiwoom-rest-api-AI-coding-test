import json
import sys
import logging
import os
import configparser
import pandas as pd
from utils.db_utils import get_db_connection

def calculate_moving_averages(df):
    """Pandas를 사용하여 이동평균선을 계산합니다."""
    if df.empty:
        return df
    
    ma_periods = [5, 10, 20, 60, 120, 240]
    for period in ma_periods:
        if len(df) >= period:
            df[f'ma{period}'] = df['close'].rolling(window=period).mean()
        else:
            df[f'ma{period}'] = None # 데이터가 부족하면 NaN으로 채움
    
    return df

def standardize_chart_data(raw_chart_data, chart_type):
    """API 응답 데이터를 프론트엔드 형식으로 표준화합니다."""
    if not raw_chart_data:
        return []

    standardized_data = []
    for item in raw_chart_data:
        date_key = 'stk_dttm' if chart_type == 'minute' else 'stk_dt'
        
        def clean_numeric(value):
            if isinstance(value, str):
                cleaned_value = value.replace('+', '').replace('-', '').replace(',', '').strip()
                return float(cleaned_value) if cleaned_value else 0.0
            elif isinstance(value, (int, float)):
                return float(value)
            return 0.0

        close_price = clean_numeric(item.get('cur_prc'))
        change = clean_numeric(item.get('prdy_vrss'))
        date_val = item.get(date_key)
        
        standardized_item = {
            'date': str(date_val) if date_val is not None else '',
            'open': clean_numeric(item.get('stk_oprc')),
            'high': clean_numeric(item.get('stk_hgprc')),
            'low': clean_numeric(item.get('stk_lwprc')),
            'close': close_price,
            'volume': int(clean_numeric(item.get('vol'))),
            'change': change,
            'prev_close': close_price - change if change is not None else None
        }
        standardized_data.append(standardized_item)
    
    return standardized_data

def get_chart_data_from_api(stock_code, chart_type):
    """
    API에서 직접 차트 데이터를 조회하고, 표준화 및 이동평균선 계산 후 JSON으로 반환합니다.
    """
    api = KiwoomAPI()
    if not api.token:
        return json.dumps({"error": "API 접근 토큰을 발급받을 수 없습니다."})

    try:
        response = api.get_chart_data(stock_code, chart_type)
        if not response:
            return json.dumps({"error": f"API로부터 데이터를 가져오지 못했습니다: {stock_code}, {chart_type}"})

        chart_data_key_map = {
            'daily': 'stk_dt_pole_chart_qry', 'weekly': 'stk_wk_pole_chart_qry', 'minute': 'stk_min_pole_chart_qry'
        }
        raw_data = response.get(chart_data_key_map.get(chart_type), [])
        
        if not raw_data:
            return json.dumps([])

        # 데이터 표준화
        chart_data = standardize_chart_data(raw_data, chart_type)
        
        # 데이터프레임으로 변환
        df = pd.DataFrame(chart_data)
        if df.empty:
            return json.dumps([])

        # 일봉/주봉의 경우 이동평균선 계산
        if chart_type in ['daily', 'weekly']:
            df = calculate_moving_averages(df)
        
        # NaN 값을 None으로 변환하여 JSON 호환성 확보
        df = df.astype(object).where(pd.notnull(df), None)
        
        return json.dumps(df.to_dict('records'))
            
    except Exception as e:
        logger.error(f"데이터 처리 중 오류 발생: {e}", exc_info=True)
        return json.dumps({"error": f"데이터 처리 중 심각한 오류 발생: {e}"})

if __name__ == "__main__":
    # pandas 라이브러리 확인
    try:
        import pandas
    except ImportError:
        print(json.dumps({"error": "서버에 'pandas' 라이브러리가 설치되지 않았습니다."}))
        sys.exit(1)
    
    # 인자값 확인
    if len(sys.argv) != 3:
        print(json.dumps({"error": "정확한 인자(종목코드, 차트종류)를 전달해야 합니다."}))
        sys.exit(1)
        
    stock_code_arg = sys.argv[1]
    chart_type_arg = sys.argv[2]
    
    if chart_type_arg not in ['daily', 'weekly', 'minute']:
        print(json.dumps({"error": "차트 종류는 'daily', 'weekly', 'minute' 중 하나여야 합니다."}))
        sys.exit(1)
    
    # 메인 함수 실행 및 결과 출력
    result_json = get_chart_data_from_api(stock_code_arg, chart_type_arg)
    print(result_json)