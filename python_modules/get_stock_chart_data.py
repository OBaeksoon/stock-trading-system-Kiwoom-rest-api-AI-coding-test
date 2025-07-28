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

if __name__ == "__main__":
    try:
        import pandas
    except ImportError:
        print(json.dumps({"error": "서버에 'pandas' 라이브러리가 설치되지 않았습니다. 'pip install pandas'로 설치해주세요."}))
        sys.exit(1)

    if len(sys.argv) != 3:
        print(json.dumps({"error": "종목코드와 차트 종류(daily, weekly, minute)를 인자로 전달해야 합니다."}))
        sys.exit(1)

    stock_code_arg = sys.argv[1]
    chart_type_arg = sys.argv[2]

    if chart_type_arg not in ['daily', 'weekly', 'minute']:
        print(json.dumps({"error": "차트 종류는 'daily', 'weekly', 'minute' 중 하나여야 합니다."}))
        sys.exit(1)

    chart_data_json = get_chart_data_from_db(stock_code_arg, chart_type_arg)
    print(chart_data_json)