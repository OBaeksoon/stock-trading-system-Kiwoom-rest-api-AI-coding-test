import requests
import json
import configparser
import os
import datetime
import logging
import mysql.connector

# --- 기본 경로 설정 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(CURRENT_DIR, '..')

# --- 설정 파일 경로 ---
CONFIG_FILE = os.path.join(PROJECT_ROOT, 'config.ini')

# --- 로그 설정 ---
LOG_DIR = os.path.join(PROJECT_ROOT, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, f"kiwoom_api_{datetime.datetime.now().strftime('%Y%m%d')}.log")

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- DB 연결 함수 ---
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
        return mysql.connector.connect(**db_config)
    except (configparser.NoSectionError, configparser.NoOptionError) as e:
        logger.error(f"config.ini 파일에 [DB] 섹션 또는 필요한 키가 없습니다. ({e})")
        return None
    except mysql.connector.Error as err:
        logger.error(f"데이터베이스 연결 오류: {err}")
        return None

# --- 키움증권 API 함수 ---
def get_api_settings_from_db():
    """데이터베이스에서 API 설정(키, 시크릿)을 가져옵니다."""
    conn = get_db_connection()
    if conn is None:
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
    app_key, app_secret = get_api_settings_from_db()
    if not app_key or not app_secret:
        return None

    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    try:
        base_url = config.get('API', 'BASE_URL')
    except (configparser.NoSectionError, configparser.NoOptionError):
        logger.error(f"config.ini 파일에서 BASE_URL을 찾을 수 없습니다.")
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
    except json.JSONDecodeError:
        logger.error(f"토큰 발급 응답 JSON 파싱 오류. 응답: {response.text}")
        return None

def get_account_info(token):
    """접근 토큰을 사용하여 계좌 정보를 조회합니다."""
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    try:
        base_url = config.get('API', 'BASE_URL')
    except (configparser.NoSectionError, configparser.NoOptionError):
        logger.error(f"config.ini 파일에서 BASE_URL을 찾을 수 없습니다.")
        return None

    url = f"{base_url}/api/dostk/acnt"
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {token}",
        "api-id": "kt00004"
    }
    data = {"qry_tp": "0", "dmst_stex_tp": "KRX"}

    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        res_json = response.json()

        if res_json.get('return_code') == 0:
            logger.info("계좌 정보 조회 성공!")
            return res_json
        else:
            logger.error(f"계좌 정보 조회 실패: {res_json.get('return_msg')}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"계좌 정보 API 요청 중 오류 발생: {e}")
        return None
    except json.JSONDecodeError:
        logger.error(f"계좌 정보 응답 JSON 파싱 오류. 응답: {response.text}")
        return None

# --- 메인 실행 블록 (테스트용) ---
if __name__ == "__main__":
    logger.info("키움증권 API 모듈 테스트를 시작합니다 (DB 연동 방식).")
    
    # 1. 접근 토큰 발급
    token = get_access_token()
    if token:
        logger.info(f"발급된 토큰 (앞 10자리): {token[:10]}...")
        
        # 2. 계좌 정보 조회
        account_data = get_account_info(token)
        if account_data:
            logger.info("--- 계좌 정보 ---")
            logger.info(json.dumps(account_data, indent=4, ensure_ascii=False))

        # 3. 주문 테스트 (예시)
        # 실제 계좌 번호, 종목 코드, 주문 유형, 수량, 가격 등을 입력해야 합니다.
        # account_num = "YOUR_ACCOUNT_NUMBER"
        # stock_code_to_order = "005930" # 삼성전자 예시
        # order_result = place_order(token, account_num, stock_code_to_order, "buy", 1, 70000) # 1주 매수 예시
        # if order_result:
        #     logger.info("--- 주문 결과 ---")
        #     logger.info(json.dumps(order_result, indent=4, ensure_ascii=False))

        # 4. 시세 조회 테스트 (예시)
        # stock_code_to_quote = "005930" # 삼성전자 예시
        # quote_data = get_stock_quote(token, stock_code_to_quote)
        # if quote_data:
        #     logger.info(f"--- {stock_code_to_quote} 시세 정보 ---")
        #     logger.info(json.dumps(quote_data, indent=4, ensure_ascii=False))

def place_order(token, account_number, stock_code, order_type, quantity, price=None):
    """
    주식 주문을 실행합니다. (매수/매도)
    API 문서에 따라 정확한 엔드포인트와 파라미터를 확인해야 합니다.
    """
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    try:
        base_url = config.get('API', 'BASE_URL')
    except (configparser.NoSectionError, configparser.NoOptionError):
        logger.error(f"config.ini 파일에서 BASE_URL을 찾을 수 없습니다.")
        return None

    # TODO: 키움증권 REST API 문서에서 주문 API 엔드포인트와 요청 바디를 정확히 확인해야 합니다.
    url = f"{base_url}/api/dostk/order" # 예시 엔드포인트
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {token}",
        "api-id": "kt00005" # 예시 API ID
    }
    data = {
        "account_number": account_number,
        "stock_code": stock_code,
        "order_type": order_type, # 예: "buy", "sell"
        "quantity": quantity,
        "price": price # 지정가 주문 시 필요
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        res_json = response.json()

        if res_json.get('return_code') == 0:
            logger.info(f"주문 성공: {res_json.get('return_msg')}")
            return res_json
        else:
            logger.error(f"주문 실패: {res_json.get('return_msg')}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"주문 API 요청 중 오류 발생: {e}")
        return None
    except json.JSONDecodeError:
        logger.error(f"주문 응답 JSON 파싱 오류. 응답: {response.text}")
        return None

def get_stock_quote(token, stock_code):
    """
    특정 종목의 현재 시세를 조회합니다.
    API 문서에 따라 정확한 엔드포인트와 파라미터를 확인해야 합니다.
    """
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    try:
        base_url = config.get('API', 'BASE_URL')
    except (configparser.NoSectionError, configparser.NoOptionError):
        logger.error(f"config.ini 파일에서 BASE_URL을 찾을 수 없습니다.")
        return None

    # TODO: 키움증권 REST API 문서에서 시세 조회 API 엔드포인트와 요청 바디를 정확히 확인해야 합니다.
    url = f"{base_url}/api/dostk/quote" # 예시 엔드포인트
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {token}",
        "api-id": "kt00006" # 예시 API ID
    }
    data = {
        "stock_code": stock_code
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        res_json = response.json()

        if res_json.get('return_code') == 0:
            logger.info(f"시세 조회 성공: {stock_code}")
            return res_json
        else:
            logger.error(f"시세 조회 실패: {res_json.get('return_msg')}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"시세 조회 API 요청 중 오류 발생: {e}")
        return None
    except json.JSONDecodeError:
        logger.error(f"시세 조회 응답 JSON 파싱 오류. 응답: {response.text}")
        return None

    logger.info("키움증권 API 모듈 테스트를 종료합니다.")