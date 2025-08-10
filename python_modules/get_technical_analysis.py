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

def save_technical_analysis_to_db(stock_code, analysis_data):
    """
    기술적 분석 결과를 데이터베이스에 저장합니다.
    """
    try:
        conn = get_db_connection()
        if conn is None:
            return False
        
        cursor = conn.cursor()
        
        # 테이블이 없으면 생성
        create_table_query = """
        CREATE TABLE IF NOT EXISTS technical_analysis (
            id INT AUTO_INCREMENT PRIMARY KEY,
            stock_code VARCHAR(10) NOT NULL,
            analysis_date DATE NOT NULL,
            close_price DECIMAL(10,2),
            sma_20 DECIMAL(10,2),
            rsi_14 DECIMAL(10,2),
            bbl_20 DECIMAL(10,2),
            bbm_20 DECIMAL(10,2),
            bbu_20 DECIMAL(10,2),
            macd DECIMAL(10,4),
            macd_histogram DECIMAL(10,4),
            macd_signal DECIMAL(10,4),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY unique_stock_date (stock_code, analysis_date)
        )
        """
        cursor.execute(create_table_query)
        
        # ON DUPLICATE KEY UPDATE를 사용하여 데이터 삽입 또는 업데이트
        insert_query = """
        INSERT INTO technical_analysis 
        (stock_code, analysis_date, close_price, sma_20, rsi_14, bbl_20, bbm_20, bbu_20, macd, macd_histogram, macd_signal)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            close_price=VALUES(close_price), sma_20=VALUES(sma_20), rsi_14=VALUES(rsi_14), bbl_20=VALUES(bbl_20),
            bbm_20=VALUES(bbm_20), bbu_20=VALUES(bbu_20), macd=VALUES(macd), macd_histogram=VALUES(macd_histogram),
            macd_signal=VALUES(macd_signal)
        """
        
        for _, row in analysis_data.iterrows():
            cursor.execute(insert_query, (
                stock_code,
                row['date'],
                float(row['close']) if row['close'] != 0 else None,
                float(row['SMA_20_20']) if 'SMA_20_20' in row and row['SMA_20_20'] != 0 else None,
                float(row['RSI_14']) if 'RSI_14' in row and row['RSI_14'] != 0 else None,
                float(row['BBL_20_2.0']) if 'BBL_20_2.0' in row and row['BBL_20_2.0'] != 0 else None,
                float(row['BBM_20_2.0']) if 'BBM_20_2.0' in row and row['BBM_20_2.0'] != 0 else None,
                float(row['BBU_20_2.0']) if 'BBU_20_2.0' in row and row['BBU_20_2.0'] != 0 else None,
                float(row['MACD_12_26_9']) if 'MACD_12_26_9' in row and row['MACD_12_26_9'] != 0 else None,
                float(row['MACDh_12_26_9']) if 'MACDh_12_26_9' in row and row['MACDh_12_26_9'] != 0 else None,
                float(row['MACDs_12_26_9']) if 'MACDs_12_26_9' in row and row['MACDs_12_26_9'] != 0 else None
            ))
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"Error saving technical analysis to DB: {e}", file=sys.stderr)
        return False
    finally:
        if 'conn' in locals() and conn:
            cursor.close()
            conn.close()

def get_all_stocks_technical_analysis():
    """
    전체 종목의 기술적 분석 데이터를 계산하고 DB에 저장합니다.
    """
    try:
        conn = get_db_connection()
        if conn is None:
            return []
        
        cursor = conn.cursor(dictionary=True)
        # 일봉 차트 데이터가 있는 종목들 조회
        cursor.execute(
            "SELECT DISTINCT stock_code FROM stock_chart_data WHERE chart_type = 'daily' LIMIT 100"
        )
        stocks = cursor.fetchall()
        
        all_results = []
        for stock in stocks:
            stock_code = stock['stock_code']
            try:
                df = get_daily_data_with_indicators(stock_code, days=30)  # 30일 데이터
                if not df.empty:
                    # DB에 저장
                    save_technical_analysis_to_db(stock_code, df)
                    
                    # 최신 데이터만 결과에 추가
                    latest_data = df.iloc[-1].to_dict()
                    latest_data['stock_code'] = stock_code
                    all_results.append(latest_data)
                    print(f"Processed {stock_code}", file=sys.stderr)
            except Exception as e:
                print(f"Error processing {stock_code}: {e}", file=sys.stderr)
                continue
        
        return all_results
        
    except Exception as e:
        print(f"Error in get_all_stocks_technical_analysis: {e}", file=sys.stderr)
        return []
    finally:
        if 'conn' in locals() and conn:
            cursor.close()
            conn.close()

def get_daily_data_with_indicators(stock_code, days=100):
    """
    지정된 종목의 일봉 데이터와 기술적 분석 지표를 반환합니다.
    """
    try:
        conn = get_db_connection()
        if conn is None:
            return pd.DataFrame()
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT chart_data FROM stock_chart_data WHERE stock_code = %s AND chart_type = 'daily'",
            (stock_code,)
        )
        result = cursor.fetchone()
        
        if not result or not result['chart_data']:
            return pd.DataFrame()
        
        # JSON 데이터를 파싱
        chart_data = json.loads(result['chart_data'])
        
        # DataFrame으로 변환
        df = pd.DataFrame(chart_data)
        
        if df.empty:
            return pd.DataFrame()
        
        # 날짜 컬럼 처리 (키움증권 API 필드명에 맞게 수정)
        date_field = 'dt' if 'dt' in df.columns else 'date'
        df['date'] = pd.to_datetime(df[date_field], format='%Y%m%d')
        df = df.sort_values(by='date', ascending=True).reset_index(drop=True)
        
        # 데이터 타입 변환 (키움증권 API 필드명에 맞게 수정)
        field_mapping = {
            'open_prc': 'open',
            'high_prc': 'high', 
            'low_prc': 'low',
            'cur_prc': 'close',
            'trde_qty': 'volume'
        }
        
        for api_field, ta_field in field_mapping.items():
            if api_field in df.columns:
                df[ta_field] = pd.to_numeric(df[api_field].astype(str).str.replace('+', '').str.replace('-', ''), errors='coerce')
        
        # 기술적 지표 계산
        if len(df) >= 20:  # 최소 20일 데이터 필요
            df.ta.sma(length=20, append=True)
            df.ta.rsi(length=14, append=True)
            df.ta.macd(fast=12, slow=26, signal=9, append=True)
            df.ta.bbands(length=20, std=2, append=True)
        
        # 최근 N일 데이터만 선택
        df = df.tail(days).copy()
        
        # NaN 값 처리
        df = df.fillna(0)

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
        if sys.argv[1] == "--all":
            # 전체 종목 기술적 분석 및 DB 저장
            all_results = get_all_stocks_technical_analysis()
            print(json.dumps(all_results))
        else:
            # 개별 종목 기술적 분석 및 DB 저장
            stock_code = sys.argv[1]
            result_df = get_daily_data_with_indicators(stock_code, days=30)
            
            if not result_df.empty:
                # DB에 저장
                save_technical_analysis_to_db(stock_code, result_df)
                print(result_df.to_json(orient='records'))
            else:
                print(json.dumps([]))
    else:
        # 전체 종목 기술적 분석 (기본 동작)
        all_results = get_all_stocks_technical_analysis()
        print(json.dumps(all_results))
