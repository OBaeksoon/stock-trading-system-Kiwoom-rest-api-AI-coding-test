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
    """키움증권 API(ka10027)를 사용하여 실시간 상승률 상위 30위 종목을 조회합니다."""
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    try:
        base_url = config.get('API', 'BASE_URL')
    except (configparser.NoSectionError, configparser.NoOptionError):
        logger.error("config.ini 파일에서 BASE_URL을 찾을 수 없습니다.")
        return [{"error": "config.ini 파일에서 BASE_URL을 찾을 수 없습니다."}]

    url = f"{base_url}/api/dostk/rkinfo"  # 순위정보 API 엔드포인트
    headers = {
        'Content-Type': 'application/json; charset=utf-8',
        'authorization': f'Bearer {token}',
        'api-id': 'ka10027'  # 전일대비등락률상위요청 TR ID
    }
    
    data = {
        "mrkt_tp": "000",       # 000: 전체, 001: 코스피, 101: 코스닥
        "prc_tp": "0",          # 0: 전체 가격
        "pric_cnd": "0",        # 0: 전체조회
        "trde_prica_cnd": "0",  # 0: 전체조회
        "updown_tp": "2",       # 1: 상한, 2: 상승, 4: 하한, 5: 하락
        "sort_tp": "1",         # 1: 등락률순, 2: 등락액순
        "updown_incls": "0",    # 필수 파라미터 (0: 보합 미포함)
        "stk_cnd": "0",         # 0: 전체조회
        "trde_qty_cnd": "00000", # 00000: 전체조회
        "crd_cnd": "0",         # 0: 전체조회
        "trde_gold_tp": "0",    # 0: 전체조회
        "stex_tp": "3"          # 1: KRX, 2: NXT, 3: 통합
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        logger.info(f"API 응답 코드: {response.status_code}")
        
        if result.get('return_code') == 0 and 'pred_pre_flu_rt_upper' in result:
            stocks_data = result['pred_pre_flu_rt_upper']
            logger.info(f"API에서 {len(stocks_data)}개 상승률 상위 종목 데이터를 가져왔습니다.")
            return stocks_data[:30]
        else:
            error_msg = result.get('return_msg', 'Unknown error')
            logger.error(f"API 오류: {error_msg}, 응답: {result}")
            return [{"error": error_msg, "return_msg": result.get('return_msg', '')}]
            
    except requests.exceptions.RequestException as e:
        logger.error(f"API 호출 중 오류 발생: {e}")
        return [{"error": f"API 호출 오류: {str(e)}"}]
    except json.JSONDecodeError as e:
        logger.error(f"JSON 파싱 오류: {e}")
        return [{"error": f"JSON 파싱 오류: {str(e)}"}]

def save_stocks_to_db(stocks):
    """조회된 종목 데이터를 데이터베이스에 저장합니다."""
    conn = None
    try:
        conn = get_db_connection()
        if conn is None:
            logger.error("DB 연결을 가져올 수 없어 저장을 중단합니다.")
            return

        cursor = conn.cursor()

        # 기존 데이터 삭제
        cursor.execute("DELETE FROM top_30_rising_stocks")
        logger.info("기존 상승률 상위 종목 데이터를 삭제했습니다.")

        # 데이터 삽입
        sql = """
            INSERT INTO top_30_rising_stocks (
                rank, stock_code, stock_name, current_price, change_rate, volume
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        for i, stock in enumerate(stocks):
            # API 응답에서 필요한 데이터 추출 및 타입 변환
            rank = i + 1
            stock_code = stock.get('stk_cd', '').strip()
            stock_name = stock.get('stk_nm', '').strip()
            current_price = int(stock.get('cur_prc', '0').replace('+', '').replace('-', ''))
            change_rate = float(stock.get('flu_rt', '0.0'))
            volume = int(stock.get('now_trde_qty', '0'))

            if not stock_code or not stock_name:
                logger.warning(f"유효하지 않은 데이터 건너뛰기: {stock}")
                continue

            cursor.execute(sql, (rank, stock_code, stock_name, current_price, change_rate, volume))

        conn.commit()
        logger.info(f"{cursor.rowcount}개의 새로운 상승률 상위 종목을 데이터베이스에 저장했습니다.")

    except mysql.connector.Error as err:
        logger.error(f"데이터베이스 작업 중 오류 발생: {err}")
        if conn:
            conn.rollback()
    except Exception as e:
        logger.error(f"데이터 저장 중 예기치 않은 오류 발생: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
            logger.info("데이터베이스 연결을 닫았습니다.")

def main():
    """메인 함수 - 상승률 상위 30위 종목을 조회하고 DB에 저장합니다."""
    try:
        logger.info("상승률 상위 30위 종목 조회를 시작합니다.")
        
        access_token = get_access_token()
        if not access_token:
            logger.error("접근 토큰을 가져오지 못했습니다.")
            sys.exit(1)
        
        stocks = get_top_30_rising_stocks(access_token)
        
        if stocks and not (len(stocks) == 1 and 'error' in stocks[0]):
            save_stocks_to_db(stocks)
            # 다른 스크립트에서 재사용할 수 있도록 상태 메시지 대신 실제 데이터를 출력합니다.
            print(json.dumps(stocks, ensure_ascii=False))
        else:
            error_msg = "상승률 상위 종목 데이터를 가져오지 못했습니다."
            if stocks and 'error' in stocks[0]:
                error_msg = stocks[0]['error']
            logger.error(error_msg)
            # 오류 발생 시에도 일관된 JSON 형식으로 출력합니다.
            print(json.dumps({"status": "error", "message": error_msg, "data": []}, ensure_ascii=False))
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"스크립트 실행 중 오류 발생: {e}", exc_info=True)
        print(json.dumps({"status": "error", "message": f"스크립트 실행 오류: {str(e)}", "data": []}, ensure_ascii=False))
        sys.exit(1)

if __name__ == '__main__':
    main()