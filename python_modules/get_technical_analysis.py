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
from python_modules.kiwoom_api import KiwoomAPI

def get_daily_data_with_indicators(stock_code, days=100):
    """
    지정된 종목의 일봉 데이터와 기술적 분석 지표를 반환합니다.
    """
    try:
        api = KiwoomAPI()
        
        # 오늘 날짜를 YYYYMMDD 형식으로
        end_date = datetime.now().strftime('%Y%m%d')
        
        # pyheroapi의 국내주식기간별시세 함수 호출 (가정)
        # 실제 함수명과 파라미터는 pyheroapi 문서에 따라야 합니다.
        # 여기서는 '출력구분'을 2(수정주가)로 가정합니다.
        df = api.get_price_history(stock_code, 'D', end_date, '2')

        if df.empty:
            return pd.DataFrame()

        # 데이터프레임 컬럼명 변경 (예: 'stck_clpr' -> 'close')
        # 실제 API 응답에 맞게 컬럼명을 확인하고 맞춰야 합니다.
        df.rename(columns={
            'stck_bsop_date': 'date',
            'stck_oprc': 'open',
            'stck_hgpr': 'high',
            'stck_lwpr': 'low',
            'stck_clpr': 'close',
            'acml_vol': 'volume'
        }, inplace=True)

        # 데이터 타입 변환
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col])

        # 날짜를 기준으로 정렬
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values(by='date', ascending=True).reset_index(drop=True)
        
        # 기술적 지표 계산
        df.ta.sma(length=20, append=True)
        df.ta.rsi(length=14, append=True)
        df.ta.macd(fast=12, slow=26, signal=9, append=True)
        df.ta.bbands(length=20, std=2, append=True)

        # 최근 100일 데이터만 선택
        df = df.tail(days)
        
        # NaN 값 처리
        df.fillna(0, inplace=True)

        # 날짜 형식 변경
        df['date'] = df['date'].dt.strftime('%Y-%m-%d')

        return df

    except Exception as e:
        # 오류 발생 시 빈 데이터프레임 반환
        # print(f"Error in get_daily_data_with_indicators: {e}", file=sys.stderr)
        return pd.DataFrame()

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
