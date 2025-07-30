import json
import sys
import logging
import mysql.connector
import os
import configparser
import pandas as pd

# --- 로그 설정 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_db_connection():
    """데이터베이스 연결을 가져옵니다."""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(current_dir, '..', 'config.ini')
        if not os.path.exists(config_path):
            logger.error(f"설정 파일을 찾을 수 없습니다: {config_path}")
            return None
        config = configparser.ConfigParser()
        config.read(config_path)
        db_config = config['DB']
        return mysql.connector.connect(
            host=db_config.get('HOST'),
            user=db_config.get('USER'),
            password=db_config.get('PASSWORD'),
            database=db_config.get('DATABASE'),
            port=db_config.getint('PORT', 3306)
        )
    except Exception as e:
        logger.error(f"DB 설정 또는 연결 오류: {e}")
        return None

def calculate_moving_averages(data):
    """
    Pandas를 사용하여 요청된 모든 이동평균선을 계산합니다.
    """
    if not data:
        return data
    
    df = pd.DataFrame(data)
    df['close'] = pd.to_numeric(df['close'], errors='coerce')
    
    # 이동평균선 기간 목록
    ma_periods = [3, 5, 10, 20, 60, 240, 480]
    for period in ma_periods:
        df[f'ma{period}'] = df['close'].rolling(window=period).mean()
    
    # NaN 값을 JSON 호환 가능한 None으로 변경
    df = df.astype(object).where(pd.notnull(df), None)
    
    return df.to_dict('records')

def get_chart_data_from_db(stock_code, chart_type):
    """
    DB에서 차트 데이터를 조회하고 이동평균선을 계산하여 반환합니다.
    """
    conn = get_db_connection()
    if conn is None:
        return json.dumps({"error": "데이터베이스 연결 실패"})

    cursor = conn.cursor(dictionary=True)
    try:
        query = "SELECT chart_data FROM stock_chart_data WHERE stock_code = %s AND chart_type = %s"
        cursor.execute(query, (stock_code, chart_type))
        result = cursor.fetchone()
        
        if result and result['chart_data']:
            chart_data = json.loads(result['chart_data'])
            
            if chart_type in ['daily', 'weekly']:
                chart_data_with_ma = calculate_moving_averages(chart_data)
                return json.dumps(chart_data_with_ma)
            else:
                return json.dumps(chart_data)
        else:
            return json.dumps({"error": f"데이터를 찾을 수 없습니다: {stock_code}, {chart_type}"})
            
    except Exception as e:
        logger.error(f"데이터 처리 중 오류 발생: {e}")
        return json.dumps({"error": f"데이터 처리 오류: {e}"})
    finally:
        cursor.close()
        conn.close()

def collect_all_chart_data():
    """전체 종목의 차트 데이터를 수집합니다."""
    try:
        import requests
        from kiwoom_api import get_access_token
    except ImportError as e:
        logger.error(f"필요한 라이브러리를 찾을 수 없습니다: {e}")
        return
    
    conn = get_db_connection()
    if conn is None:
        logger.error("데이터베이스 연결 실패")
        return
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 전체 종목 목록 조회
        cursor.execute("SELECT code, name FROM all_stocks LIMIT 10")  # 테스트용 10개만
        stocks = cursor.fetchall()
        
        logger.info(f"{len(stocks)}개 종목의 차트 데이터를 수집합니다.")
        
        # API 토큰 발급
        token = get_access_token()
        if not token:
            logger.error("API 토큰 발급 실패")
            return
        
        success_count = 0
        
        for stock in stocks:
            stock_code = stock['code']
            stock_name = stock['name']
            
            logger.info(f"처리 중: {stock_code} ({stock_name})")
            
            # 일봉, 주봉, 분봉 데이터 수집
            for chart_type in ['daily', 'weekly', 'minute']:
                try:
                    chart_data = fetch_chart_data_from_api(token, stock_code, chart_type)
                    if chart_data:
                        save_chart_data_to_db(cursor, stock_code, chart_type, chart_data)
                        success_count += 1
                except Exception as e:
                    logger.error(f"{stock_code} {chart_type} 차트 데이터 수집 실패: {e}")
        
        conn.commit()
        logger.info(f"차트 데이터 수집 완료: {success_count}개 성공")
        
    except Exception as e:
        logger.error(f"차트 데이터 수집 중 오류: {e}")
    finally:
        cursor.close()
        conn.close()

def fetch_chart_data_from_api(token, stock_code, chart_type):
    """키움증권 API에서 차트 데이터를 가져옵니다."""
    import requests
    
    # config.ini에서 BASE_URL 읽기
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, '..', 'config.ini')
    config = configparser.ConfigParser()
    config.read(config_path)
    base_url = config.get('API', 'BASE_URL')
    
    url = f"{base_url}/api/dostk/chart"
    headers = {
        'authorization': f'Bearer {token}',
        'api-id': 'ka10001',
        'Content-Type': 'application/json;charset=UTF-8'
    }
    
    # 차트 종류에 따른 데이터 설정
    if chart_type == 'daily':
        data = {
            "stk_cd": stock_code,
            "prd_tp": "D",  # 일봉
            "prd_cnt": "100"  # 100일
        }
    elif chart_type == 'weekly':
        data = {
            "stk_cd": stock_code,
            "prd_tp": "W",  # 주봉
            "prd_cnt": "50"  # 50주
        }
    else:  # minute
        data = {
            "stk_cd": stock_code,
            "prd_tp": "M",  # 분봉
            "prd_cnt": "100"  # 100분
        }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get('return_code') == 0:
                return result.get('chart_data', [])
        return None
    except Exception as e:
        logger.error(f"API 호출 오류: {e}")
        return None

def save_chart_data_to_db(cursor, stock_code, chart_type, chart_data):
    """차트 데이터를 데이터베이스에 저장합니다."""
    try:
        # 기존 데이터 삭제 후 삽입
        cursor.execute(
            "DELETE FROM stock_chart_data WHERE stock_code = %s AND chart_type = %s",
            (stock_code, chart_type)
        )
        
        # 새 데이터 삽입
        cursor.execute(
            "INSERT INTO stock_chart_data (stock_code, chart_type, chart_data, updated_at) VALUES (%s, %s, %s, NOW())",
            (stock_code, chart_type, json.dumps(chart_data))
        )
        
    except Exception as e:
        logger.error(f"데이터 저장 오류: {e}")
        raise

if __name__ == "__main__":
    try:
        import pandas
    except ImportError:
        print(json.dumps({"error": "서버에 'pandas' 라이브러리가 설치되지 않았습니다. 'pip install pandas'로 설치해주세요."}))
        sys.exit(1)
    
    # 인자가 있으면 개별 조회, 없으면 전체 수집
    if len(sys.argv) == 3:
        # 개별 종목 조회
        stock_code_arg = sys.argv[1]
        chart_type_arg = sys.argv[2]
        
        if chart_type_arg not in ['daily', 'weekly', 'minute']:
            print(json.dumps({"error": "차트 종류는 'daily', 'weekly', 'minute' 중 하나여야 합니다."}))
            sys.exit(1)
        
        chart_data_json = get_chart_data_from_db(stock_code_arg, chart_type_arg)
        print(chart_data_json)
    else:
        # 전체 종목 차트 데이터 수집
        collect_all_chart_data()