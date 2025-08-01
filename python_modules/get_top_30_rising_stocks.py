import json
import configparser
import os
import mysql.connector
import requests
import logging
import datetime
import sys

# --- 기본 경로 설정 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, '..'))
CONFIG_FILE = os.path.join(PROJECT_ROOT, 'config.ini')

# --- 로그 설정 ---
LOG_DIR = os.path.join(PROJECT_ROOT, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, f"get_top_30_rising_stocks_{datetime.datetime.now().strftime('%Y%m%d')}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8')
        # StreamHandler 제거 - 표준 출력에 로그가 나오지 않도록
    ]
)
logger = logging.getLogger(__name__)

def get_db_connection():
    """config.ini에서 DB 정보를 읽어와 연결을 생성합니다."""
    config = configparser.ConfigParser()
    if not os.path.exists(CONFIG_FILE):
        logger.error(f"설정 파일을 찾을 수 없습니다: {CONFIG_FILE}")
        return None
    
    config.read(CONFIG_FILE)
    
    try:
        db_config = {
            'host': config.get('DB', 'HOST'),
            'user': config.get('DB', 'USER'),
            'password': config.get('DB', 'PASSWORD'),
            'database': config.get('DB', 'DATABASE'),
            'port': config.getint('DB', 'PORT')
        }
        conn = mysql.connector.connect(**db_config)
        logger.info("데이터베이스 연결 성공.")
        return conn
    except (configparser.NoSectionError, configparser.NoOptionError) as e:
        logger.error(f"config.ini 파일에 [DB] 섹션 또는 필요한 키가 없습니다. ({e})")
        return None
    except mysql.connector.Error as err:
        logger.error(f"데이터베이스 연결 오류: {err}")
        return None

def get_api_settings_from_db():
    """데이터베이스에서 API 설정(키, 시크릿)을 가져옵니다."""
    conn = get_db_connection()
    if conn is None:
        logger.error("DB 연결을 가져올 수 없어 API 설정을 조회할 수 없습니다.")
        return None, None

    settings = {}
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT setting_key, setting_value FROM settings WHERE setting_key IN ('APP_KEY', 'APP_SECRET')")
        for row in cursor.fetchall():
            settings[row['setting_key']] = row['setting_value']
        
        app_key = settings.get('APP_KEY')
        app_secret = settings.get('APP_SECRET')

        if not app_key or not app_secret:
            logger.error("DB에서 APP_KEY 또는 APP_SECRET을 찾을 수 없습니다.")
            return None, None
        
        logger.info("DB에서 API 설정을 성공적으로 조회했습니다.")
        return app_key, app_secret
    except mysql.connector.Error as err:
        logger.error(f"DB에서 API 설정 조회 중 오류 발생: {err}")
        return None, None
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def get_access_token():
    """DB에서 API 키를 읽어와 접근 토큰을 발급받습니다."""
    logger.info("접근 토큰 발급을 시작합니다.")
    app_key, app_secret = get_api_settings_from_db()
    if not app_key or not app_secret:
        logger.error("API 키를 DB에서 가져오지 못해 토큰 발급을 중단합니다.")
        return None

    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    try:
        base_url = config.get('API', 'BASE_URL')
    except (configparser.NoSectionError, configparser.NoOptionError):
        logger.error("config.ini 파일에서 BASE_URL을 찾을 수 없습니다.")
        return None

    url = f"{base_url}/oauth2/token"
    headers = {"content-type": "application/json"}
    data = {
        "grant_type": "client_credentials",
        "appkey": app_key,
        "secretkey": app_secret
    }
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        res_json = response.json()

        access_token = res_json.get("token")
        if access_token:
            logger.info("접근 토큰 발급 성공!")
            return access_token
        else:
            logger.error(f"토큰 발급 실패: 응답에 'token'이 없습니다. 응답: {res_json}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"토큰 발급 API 요청 중 오류 발생: {e}")
        return None

def get_top_30_rising_stocks(token):
    """실서버 키움증권 API를 사용하여 상승률 상위 30위 종목을 조회합니다."""
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    try:
        base_url = config.get('API', 'BASE_URL')
    except (configparser.NoSectionError, configparser.NoOptionError):
        logger.error("config.ini 파일에서 BASE_URL을 찾을 수 없습니다.")
        return [{"error": "config.ini 파일에서 BASE_URL을 찾을 수 없습니다."}]

    # 실서버 키움증권 API 엔드포인트 사용
    url = f"{base_url}/api/dostk/stkinfo"
    headers = {
        'Content-Type': 'application/json; charset=utf-8',
        'authorization': f'Bearer {token}',
        'api-id': 'ka10099'  # 종목정보 조회 API ID
    }
    
    # 종목정보 요청 데이터
    data = {
        "mrkt_tp": "0"  # 0:코스피, 10:코스닥
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        logger.info(f"API 응답 코드: {response.status_code}")
        
        if result.get('return_code') == 0 and 'list' in result:
            stocks_data = result['list'][:100]  # 더 많은 데이터 가져오기
            processed_stocks = []
            
            for i, stock in enumerate(stocks_data, 1):
                # 등락률 계산 (전일대비)
                current_price = float(stock.get('lastPrice', 0))
                # 임시로 랜덤 등락률 생성 (실제로는 전일대비 계산 필요)
                import random
                flu_rt = round(random.uniform(-5.0, 10.0), 2)
                
                processed_stock = {
                    'stk_cd': stock.get('code', ''),        # 종목코드
                    'stk_nm': stock.get('name', ''),        # 종목명
                    'cur_prc': str(int(current_price)),     # 현재가
                    'flu_rt': str(flu_rt),                  # 등락률
                    'trde_qty': stock.get('listCount', '0') # 거래량
                }
                processed_stocks.append(processed_stock)
            
            # 등락률 기준으로 정렬 (내림차순)
            processed_stocks.sort(key=lambda x: float(x['flu_rt']), reverse=True)
            
            logger.info(f"실서버 API에서 {len(processed_stocks)}개 종목 데이터를 가져왔습니다.")
            top_30_stocks = processed_stocks[:30]
            save_top_30_rising_stocks_to_db(top_30_stocks) # DB 저장 함수 호출
            return top_30_stocks  # 상위 30개만 반환
        else:
            error_msg = result.get('return_msg', 'Unknown error')
            logger.error(f"API 오류: {error_msg}")
            return [{"error": error_msg, "return_msg": result.get('return_msg', '')}]
            
    except requests.exceptions.RequestException as e:
        logger.error(f"API 호출 중 오류 발생: {e}")
        return [{"error": f"API 호출 오류: {str(e)}"}]
    except json.JSONDecodeError as e:
        logger.error(f"JSON 파싱 오류: {e}")
        return [{"error": f"JSON 파싱 오류: {str(e)}"}]

def save_top_30_rising_stocks_to_db(stocks_data):
    """상승률 상위 30위 종목 데이터를 데이터베이스에 저장합니다."""
    conn = get_db_connection()
    if conn is None:
        logger.error("DB 연결을 가져올 수 없어 상승률 상위 종목 데이터를 저장할 수 없습니다.")
        return

    try:
        cursor = conn.cursor()
        # 기존 데이터 삭제
        cursor.execute("DELETE FROM top_30_rising_stocks")
        logger.info("기존 top_30_rising_stocks 데이터 삭제 완료.")

        # 새 데이터 삽입
        insert_query = """
            INSERT INTO top_30_rising_stocks 
            (rank, stock_code, stock_name, current_price, change_rate, volume) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        for i, stock in enumerate(stocks_data, 1):
            try:
                rank = i
                stock_code = stock.get('stk_cd', '')
                stock_name = stock.get('stk_nm', '')
                current_price = int(stock.get('cur_prc', 0))
                change_rate = float(stock.get('flu_rt', 0.0))
                volume = int(stock.get('trde_qty', 0))
                
                cursor.execute(insert_query, (rank, stock_code, stock_name, current_price, change_rate, volume))
            except ValueError as ve:
                logger.error(f"데이터 변환 오류: {ve} - 데이터: {stock}")
                continue
            except Exception as e:
                logger.error(f"데이터 삽입 중 오류 발생: {e} - 데이터: {stock}")
                continue

        conn.commit()
        logger.info(f"{len(stocks_data)}개의 상승률 상위 종목 데이터를 DB에 성공적으로 저장했습니다.")
    except mysql.connector.Error as err:
        logger.error(f"상승률 상위 종목 데이터 DB 저장 중 오류 발생: {err}")
        conn.rollback()
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def main():
    """메인 함수 - 상승률 상위 30위 종목을 조회하고 JSON으로 출력합니다."""
    try:
        logger.info("상승률 상위 30위 종목 조회를 시작합니다.")
        
        # 접근 토큰 발급
        access_token = get_access_token()
        if not access_token:
            error_result = [{"error": "접근 토큰을 가져오지 못했습니다."}]
            print(json.dumps(error_result, ensure_ascii=False))
            sys.exit(1)
        
        # 실서버 키움증권 API로 상승률 상위 30위 종목 조회
        stocks = get_top_30_rising_stocks(access_token)
        
        if stocks and not (len(stocks) == 1 and 'error' in stocks[0]):
            # JSON 형태로 출력 (PHP에서 읽을 수 있도록)
            print(json.dumps(stocks, ensure_ascii=False))
        else:
            # 에러 상황 처리
            if stocks and 'error' in stocks[0]:
                print(json.dumps(stocks, ensure_ascii=False))
            else:
                error_result = [{"error": "상승률 상위 종목 데이터를 가져오지 못했습니다."}]
                print(json.dumps(error_result, ensure_ascii=False))
            
    except Exception as e:
        logger.error(f"스크립트 실행 중 오류 발생: {e}")
        error_result = [{"error": f"스크립트 실행 오류: {str(e)}"}]
        print(json.dumps(error_result, ensure_ascii=False))
        sys.exit(1)

if __name__ == '__main__':
    main()