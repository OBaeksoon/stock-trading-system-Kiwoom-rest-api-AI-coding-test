import json
import configparser
import os
import mysql.connector
import logging
import datetime
import sys
from pyheroapi.client import KiwoomClient  # pyheroapi 임포트

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

def fetch_top_30_with_pyheroapi():
    """pyheroapi를 사용하여 실시간 상승률 상위 30위 종목을 조회합니다."""
    logger.info("pyheroapi로 상승률 상위 종목 조회를 시작합니다.")
    app_key, app_secret = get_api_settings_from_db()
    if not app_key or not app_secret:
        logger.error("API 키를 DB에서 가져오지 못해 조회를 중단합니다.")
        return [{"error": "API 키를 찾을 수 없습니다."}]

    try:
        # KiwoomClient 인스턴스 생성 (토큰 자동 발급)
        client = KiwoomClient.create_with_credentials(
            appkey=app_key,
            secretkey=app_secret,
            is_production=True  # 실서버 환경
        )
        logger.info("pyheroapi 클라이언트 생성 및 인증 성공.")

        # 상승률 상위 종목 조회
        stocks_data = client.get_change_rate_ranking(
            market_type="000",  # 000: 전체
            sort_type="1",      # 1: 상승률
            stock_condition="1", # 1: 관리종목제외
            volume_type="0000", # 거래량 조건 (0000: 전체)
            updown_incls="0",    # 보합 미포함
            pric_cnd="0",        # 가격 조건 (0: 전체)
            trde_prica_cnd="0"  # 거래대금 조건 (0: 전체)
        )
        
        logger.info(f"pyheroapi에서 {len(stocks_data)}개 종목 데이터를 가져왔습니다.")
        return stocks_data[:30]

    except Exception as e:
        logger.error(f"pyheroapi 사용 중 오류 발생: {e}", exc_info=True)
        return [{"error": f"pyheroapi 오류: {str(e)}"}]

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
        
        stocks = fetch_top_30_with_pyheroapi()
        
        if stocks and not (len(stocks) == 1 and 'error' in stocks[0]):
            save_stocks_to_db(stocks)
            print(json.dumps({"status": "success", "message": f"{len(stocks)} stocks updated successfully."}, ensure_ascii=False))
        else:
            error_msg = "상승률 상위 종목 데이터를 가져오지 못했습니다."
            if stocks and 'error' in stocks[0]:
                error_msg = stocks[0]['error']
            logger.error(error_msg)
            print(json.dumps({"status": "error", "message": error_msg}, ensure_ascii=False))
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"스크립트 실행 중 오류 발생: {e}", exc_info=True)
        print(json.dumps({"status": "error", "message": f"스크립트 실행 오류: {str(e)}"}, ensure_ascii=False))
        sys.exit(1)

if __name__ == '__main__':
    main()