import os
import sys
import json
import configparser
import pandas as pd
import pandas_ta as ta
from datetime import datetime, timedelta

# 프로젝트 루트 경로 설정 (이 파일의 상위 폴더)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(PROJECT_ROOT)

# kiwoom_api 모듈 임포트
from python_modules.kiwoom_api import get_db_connection

def get_daily_data_with_indicators(stock_code, days=100):
    """
    지정된 종목의 일봉 데이터와 기술적 분석 지표를 반환합니다.
    """
    try:
        conn = get_db_connection()
        if conn is None:
            return pd.DataFrame()
        
        cursor = conn.cursor()
        cursor.execute(
            "SELECT chart_data FROM stock_chart_data WHERE stock_code = ? AND chart_type = 'daily'",
            (stock_code,)
        )
        result = cursor.fetchone()
        
        if not result or not result[0]:
            return pd.DataFrame()
        
        # JSON 데이터를 파싱
        chart_data = json.loads(result[0])
        
        # DataFrame으로 변환
        df = pd.DataFrame(chart_data)
        
        if df.empty:
            return pd.DataFrame()
        
        # 날짜 컬럼 처리
        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
        df = df.sort_values(by='date', ascending=True).reset_index(drop=True)
        
        # 데이터 타입 변환
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 기술적 지표 계산
        if len(df) >= 20:  # 최소 20일 데이터 필요
            df.ta.sma(length=20, append=True)
            df.ta.rsi(length=14, append=True)
            df.ta.macd(fast=12, slow=26, signal=9, append=True)
            df.ta.bbands(length=20, std=2, append=True)
        
        # 최근 N일 데이터만 선택
        df = df.tail(days)
        
        # NaN 값 처리
        df.fillna(0, inplace=True)

        # 날짜 형식 변경
        df['date'] = df['date'].dt.strftime('%Y-%m-%d')

        return df

    except Exception as e:
        print(f"Error in get_daily_data_with_indicators: {e}", file=sys.stderr)
        return pd.DataFrame()
    finally:
        if 'conn' in locals() and conn:
            cursor.close()
            conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        stock_code = sys.argv[1]
        result_df = get_daily_data_with_indicators(stock_code)
        
        if not result_df.empty:
            # 결과를 JSON으로 변환하여 출력
            print(result_df.to_json(orient='records'))
        else:
            print(json.dumps([])) # 데이터가 없을 경우 빈 JSON 배열 출력
    else:
        print(json.dumps({"error": "Stock code is required"}))
