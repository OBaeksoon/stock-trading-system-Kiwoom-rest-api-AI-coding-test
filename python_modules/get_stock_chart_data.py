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
    
    # 키움증권 API 응답 필드명에 맞게 수정
    if 'cur_prc' in df.columns:
        # 현재가에서 +/- 기호 제거 후 숫자로 변환
        df['close'] = pd.to_numeric(df['cur_prc'].astype(str).str.replace('+', '').str.replace('-', ''), errors='coerce')
    else:
        logger.warning("cur_prc 필드를 찾을 수 없습니다.")
        return data
    
    # 이동평균선 기간 목록
    ma_periods = [3, 5, 10, 20, 60, 240, 480]
    for period in ma_periods:
        df[f'ma{period}'] = df['close'].rolling(window=period).mean()
    
    # NaN 값을 JSON 호환 가능한 None으로 변경
    df = df.astype(object).where(pd.notnull(df), None)
    
    return df.to_dict('records')

def calculate_moving_averages(data):
    """
    Pandas를 사용하여 요청된 모든 이동평균선을 계산합니다.
    """
    if not data:
        return data
    
    df = pd.DataFrame(data)
    
    # 'close' 필드는 fetch_chart_data_from_api에서 이미 표준화됨
    if 'close' not in df.columns:
        logger.warning("DataFrame에 'close' 필드가 없습니다.")
        return data
    
    # 이동평균선 기간 목록
    ma_periods = [3, 5, 10, 20, 60, 240, 480]
    for period in ma_periods:
        df[f'ma{period}'] = df['close'].rolling(window=period).mean()
    
    # NaN 값을 JSON 호환 가능한 None으로 변경
    df = df.astype(object).where(pd.notnull(df), None)
    
    return df.to_dict('records')

def get_chart_data(stock_code, chart_type):
    """
    API에서 직접 차트 데이터를 조회하고 이동평균선을 계산하여 반환합니다.
    """
    try:
        from kiwoom_api import get_access_token
    except ImportError:
        return json.dumps({"error": "kiwoom_api 모듈을 찾을 수 없습니다."})

    token = get_access_token()
    if not token:
        return json.dumps({"error": "API 접근 토큰을 발급받을 수 없습니다."})

    try:
        # API를 통해 최신 데이터 가져오기
        chart_data = fetch_chart_data_from_api(token, stock_code, chart_type)
        
        if chart_data:
            # 일봉/주봉의 경우 이동평균선 계산
            if chart_type in ['daily', 'weekly']:
                chart_data_with_ma = calculate_moving_averages(chart_data)
                return json.dumps(chart_data_with_ma)
            else:
                # 분봉은 그대로 반환
                return json.dumps(chart_data)
        else:
            return json.dumps({"error": f"API로부터 데이터를 가져오지 못했습니다: {stock_code}, {chart_type}"})
            
    except Exception as e:
        logger.error(f"데이터 처리 중 오류 발생: {e}")
        return json.dumps({"error": f"데이터 처리 오류: {e}"})
    finally:
        pass # DB 연결이 없으므로 finally 블록 비움

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
        # 전체 종목 목록 조회 (API 제한을 고려하여 단계적 처리)
        cursor.execute("SELECT stock_code, stock_name FROM stock_details LIMIT 500")  # 500개 종목씩 처리
        stocks = cursor.fetchall()
        
        logger.info(f"{len(stocks)}개 종목의 차트 데이터를 수집합니다.")
        
        # API 토큰 발급
        token = get_access_token()
        if not token:
            logger.error("API 토큰 발급 실패")
            return
        
        success_count = 0
        
        for stock in stocks:
            stock_code = stock['stock_code']
            stock_name = stock['stock_name']
            
            logger.info(f"처리 중: {stock_code} ({stock_name})")
            
            # 일봉, 주봉, 분봉 데이터 수집
            for chart_type in ['daily', 'weekly', 'minute']:
                try:
                    chart_data = fetch_chart_data_from_api(token, stock_code, chart_type)
                    if chart_data and len(chart_data) > 0:
                        save_chart_data_to_db(cursor, stock_code, chart_type, chart_data)
                        success_count += 1
                        # 성공 로그는 생략
                    else:
                        logger.warning(f"{stock_code} {chart_type} 데이터 없음")
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
    """키움증권 API에서 차트 데이터를 가져와서 프론트엔드 형식으로 표준화합니다."""
    import requests
    from datetime import datetime
    
    # config.ini에서 BASE_URL 읽기
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, '..', 'config.ini')
    config = configparser.ConfigParser()
    config.read(config_path)
    base_url = config.get('API', 'BASE_URL')
    
    url = f"{base_url}/api/dostk/chart"
    
    # 차트 종류에 따른 API ID와 데이터 설정
    today = datetime.now().strftime('%Y%m%d')
    use_adjusted_price = "1" # 수정주가 사용 (0: 무수정, 1: 수정)
    
    api_map = {
        'daily': 'ka10081',
        'weekly': 'ka10082',
        'minute': 'ka10080'
    }
    data_map = {
        'daily': {"stk_cd": stock_code, "base_dt": today, "upd_stkpc_tp": use_adjusted_price},
        'weekly': {"stk_cd": stock_code, "base_dt": today, "upd_stkpc_tp": use_adjusted_price},
        'minute': {"stk_cd": stock_code, "tic_scope": "1", "upd_stkpc_tp": use_adjusted_price}
    }
    
    headers = {
        'authorization': f'Bearer {token}',
        'api-id': api_map[chart_type],
        'Content-Type': 'application/json;charset=UTF-8'
    }
    
    try:
        response = requests.post(url, headers=headers, json=data_map[chart_type], timeout=10)
        response.raise_for_status() # HTTP 오류 발생 시 예외 발생
        
        result = response.json()
        if result.get('return_code') != 0:
            logger.warning(f"API 오류: {result.get('return_msg', 'Unknown error')}")
            return []

        # API 응답에서 실제 차트 데이터 추출
        chart_data_key_map = {
            'daily': 'stk_dt_pole_chart_qry',
            'weekly': 'stk_wk_pole_chart_qry',
            'minute': 'stk_min_pole_chart_qry'
        }
        raw_chart_data = result.get(chart_data_key_map[chart_type], [])
        if not raw_chart_data:
            return []

        # 프론트엔드가 사용하는 필드명으로 표준화
        standardized_data = []
        for item in raw_chart_data:
            date_key = 'stk_dttm' if chart_type == 'minute' else 'stk_dt'
            
            # +/- 부호 및 쉼표 제거 후 숫자 변환
            def clean_numeric(value):
                if isinstance(value, str):
                    # 빈 문자열이나 공백만 있는 경우 0으로 처리
                    cleaned_value = value.replace('+', '').replace('-', '').replace(',', '').strip()
                    if not cleaned_value:
                        return 0.0
                    return float(cleaned_value)
                # 숫자 타입이 아닌 경우 0으로 처리 (None 등)
                elif not isinstance(value, (int, float)):
                    return 0.0
                return float(value)

            close_price = clean_numeric(item.get('cur_prc'))
            change = clean_numeric(item.get('prdy_vrss'))
            
            # 날짜 값이 None일 경우 빈 문자열로 처리
            date_val = item.get(date_key)
            
            standardized_item = {
                'date': str(date_val) if date_val is not None else '',
                'open': clean_numeric(item.get('stk_oprc')),
                'high': clean_numeric(item.get('stk_hgprc')),
                'low': clean_numeric(item.get('stk_lwprc')),
                'close': close_price,
                'volume': int(clean_numeric(item.get('vol'))),
                'change': change,
                'prev_close': close_price - change
            }
            standardized_data.append(standardized_item)
        
        return standardized_data

    except requests.exceptions.RequestException as e:
        logger.error(f"API 호출 오류: {e}")
        return []
    except Exception as e:
        logger.error(f"데이터 표준화 중 오류: {e}")
        return []

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
        # 전체 종목 목록 조회 (API 제한을 고려하여 단계적 처리)
        cursor.execute("SELECT stock_code, stock_name FROM stock_details LIMIT 500")  # 500개 종목씩 처리
        stocks = cursor.fetchall()
        
        logger.info(f"{len(stocks)}개 종목의 차트 데이터를 수집합니다.")
        
        # API 토큰 발급
        token = get_access_token()
        if not token:
            logger.error("API 토큰 발급 실패")
            return
        
        success_count = 0
        
        for stock in stocks:
            stock_code = stock['stock_code']
            stock_name = stock['stock_name']
            
            logger.info(f"처리 중: {stock_code} ({stock_name})")
            
            # 일봉, 주봉, 분봉 데이터 수집
            for chart_type in ['daily', 'weekly', 'minute']:
                try:
                    chart_data = fetch_chart_data_from_api(token, stock_code, chart_type)
                    if chart_data and len(chart_data) > 0:
                        save_chart_data_to_db(cursor, stock_code, chart_type, chart_data)
                        success_count += 1
                        # 성공 로그는 생략
                    else:
                        logger.warning(f"{stock_code} {chart_type} 데이터 없음")
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
    from datetime import datetime
    
    # config.ini에서 BASE_URL 읽기
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, '..', 'config.ini')
    config = configparser.ConfigParser()
    config.read(config_path)
    base_url = config.get('API', 'BASE_URL')
    
    url = f"{base_url}/api/dostk/chart"
    
    # 차트 종류에 따른 API ID와 데이터 설정
    today = datetime.now().strftime('%Y%m%d')
    
    # 수정주가 사용 (0: 무수정, 1: 수정)
    use_adjusted_price = "1"
    
    if chart_type == 'daily':
        headers = {
            'authorization': f'Bearer {token}',
            'api-id': 'ka10081',  # 주식일봉차트조회요청
            'Content-Type': 'application/json;charset=UTF-8'
        }
        data = {
            "stk_cd": stock_code,
            "base_dt": today,
            "upd_stkpc_tp": use_adjusted_price
        }
    elif chart_type == 'weekly':
        headers = {
            'authorization': f'Bearer {token}',
            'api-id': 'ka10082',  # 주식주봉차트조회요청
            'Content-Type': 'application/json;charset=UTF-8'
        }
        data = {
            "stk_cd": stock_code,
            "base_dt": today,
            "upd_stkpc_tp": use_adjusted_price
        }
    else:  # minute
        headers = {
            'authorization': f'Bearer {token}',
            'api-id': 'ka10080',  # 주식분봉차트조회요청
            'Content-Type': 'application/json;charset=UTF-8'
        }
        data = {
            "stk_cd": stock_code,
            "tic_scope": "1",  # 1분봉
            "upd_stkpc_tp": use_adjusted_price
        }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get('return_code') == 0:
                # 차트 종류에 따른 데이터 추출
                if chart_type == 'daily':
                    chart_data = result.get('stk_dt_pole_chart_qry', [])
                elif chart_type == 'weekly':
                    chart_data = result.get('stk_wk_pole_chart_qry', [])
                else:  # minute
                    chart_data = result.get('stk_min_pole_chart_qry', [])
                
                return chart_data
            else:
                logger.warning(f"API 오류: {result.get('return_msg', 'Unknown error')}")
        else:
            logger.error(f"HTTP 오류: {response.status_code}, 응답: {response.text}")
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
        
        chart_data_json = get_chart_data(stock_code_arg, chart_type_arg)
        print(chart_data_json)
    else:
        # 전체 종목 차트 데이터 수집
        collect_all_chart_data()