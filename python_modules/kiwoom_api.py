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

class KiwoomAPI:
    def __init__(self):
        self.app_key, self.app_secret = self._get_api_settings_from_db()
        self.base_url = self._get_base_url()
        self.token = self._get_access_token()

    def _get_db_connection(self):
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

    def _get_api_settings_from_db(self):
        """데이터베이스에서 API 설정(키, 시크릿)을 가져옵니다."""
        conn = self._get_db_connection()
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

    def _get_base_url(self):
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE)
        try:
            return config.get('API', 'BASE_URL')
        except (configparser.NoSectionError, configparser.NoOptionError):
            logger.error(f"config.ini 파일에서 BASE_URL을 찾을 수 없습니다.")
            return None

    def _get_access_token(self):
        """DB에서 API 키를 읽어와 접근 토큰을 발급받습니다."""
        if not self.app_key or not self.app_secret or not self.base_url:
            return None

        url = f"{self.base_url}/oauth2/token"
        headers = {"content-type": "application/json"}
        data = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "secretkey": self.app_secret
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

    def get_top_30_rising_stocks(self):
        """
        전일대비등락률상위요청 API(ka10027)를 사용하여 상승률 상위 종목을 가져옵니다.
        """
        if not self.token:
            logger.error("토큰이 없어 순위 조회를 할 수 없습니다.")
            return None

        url = f"{self.base_url}/api/dostk/rkinfo"
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {self.token}",
            "api-id": "ka10027"
        }
        data = {
            "mrkt_tp": "000",
            "sort_tp": "1",
            "trde_qty_cnd": "00000",
            "stk_cnd": "0",
            "crd_cnd": "0",
            "updown_incls": "1",
            "pric_cnd": "0",
            "trde_prica_cnd": "0",
            "stex_tp": "3"
        }

        try:
            response = requests.post(url, headers=headers, data=json.dumps(data))
            response.raise_for_status()
            res_json = response.json()

            if res_json.get('return_code') == 0:
                logger.info("전일대비등락률상위 조회 성공!")
                return res_json.get('pred_pre_flu_rt_upper', [])
            else:
                logger.error(f"전일대비등락률상위 조회 실패: {res_json.get('return_msg')}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"전일대비등락률상위 API 요청 중 오류 발생: {e}")
            return None
        except json.JSONDecodeError:
            logger.error(f"전일대비등락률상위 응답 JSON 파싱 오류. 응답: {response.text}")
            return None

    def _send_request(self, api_id, data, cont_yn=None, next_key=None):
        """공통 API 요청 전송 함수"""
        if not self.token:
            logger.error(f"API 요청 실패: 토큰이 없습니다. (API ID: {api_id})")
            return None

        url = f"{self.base_url}/api/dostk/stkinfo"
        headers = {
            'Content-Type': 'application/json;charset=UTF-8',
            'authorization': f'Bearer {self.token}',
            'api-id': api_id,
        }
        if cont_yn is not None:
            headers['cont-yn'] = cont_yn
        if next_key is not None:
            headers['next-key'] = next_key
        
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            res_json = response.json()
            if res_json.get('return_code') != 0:
                logger.error(f"API 오류 (ID: {api_id}): {res_json.get('return_msg')}")
                return None
            return res_json
        except requests.exceptions.RequestException as e:
            logger.error(f"API 요청 중 오류 발생 (ID: {api_id}): {e}")
            return None
        except json.JSONDecodeError:
            logger.error(f"API 응답 JSON 파싱 오류 (ID: {api_id}). 응답: {response.text}")
            return None

    def get_all_stock_codes(self, market_type, cont_yn='N', next_key=''):
        """모의투자 환경에서 코스피 및 코스닥의 모든 종목 정보를 조회합니다. (TR: ka10099)"""
        return self._send_request('ka10099', {'mrkt_tp': market_type}, cont_yn, next_key)

    def get_stock_basic_info(self, stock_code):
        """단일 종목의 기본 정보를 조회합니다. (TR: ka10001)"""
        return self._send_request('ka10001', {'stk_cd': stock_code})

    def get_stock_daily_history(self, stock_code, start_date):
        """단일 종목의 일별 거래 상세 정보를 조회합니다. (TR: ka10015)"""
        return self._send_request('ka10015', {'stk_cd': stock_code, 'strt_dt': start_date})

    def get_chart_data(self, stock_code, chart_type):
        """차트 데이터를 조회합니다. (일봉: ka10081, 주봉: ka10082, 분봉: ka10080)"""
        today = datetime.datetime.now().strftime('%Y%m%d')
        use_adjusted_price = "1"
        
        api_map = {'daily': 'ka10081', 'weekly': 'ka10082', 'minute': 'ka10080'}
        data_map = {
            'daily': {"stk_cd": stock_code, "base_dt": today, "upd_stkpc_tp": use_adjusted_price},
            'weekly': {"stk_cd": stock_code, "base_dt": today, "upd_stkpc_tp": use_adjusted_price},
            'minute': {"stk_cd": stock_code, "tic_scope": "1", "upd_stkpc_tp": use_adjusted_price}
        }
        
        if chart_type not in api_map:
            logger.error(f"잘못된 차트 종류: {chart_type}")
            return None
            
        return self._send_request(api_map[chart_type], data_map[chart_type])

    def get_all_themes(self):
        """전체 테마 정보를 조회합니다. (TR: ka90001)"""
        payload = {"qry_tp": "0", "stk_cd": "", "date_tp": "10", "thema_nm": "", "flu_pl_amt_tp": "1", "stex_tp": "1"}
        return self._send_request('ka90001', payload)

    def get_stocks_by_theme(self, theme_code):
        """특정 테마의 구성종목을 가져옵니다. (TR: ka90002)"""
        payload = {"date_tp": "2", "thema_grp_cd": theme_code, "stex_tp": "1"}
        return self._send_request('ka90002', payload)

# --- 메인 실행 블록 (테스트용) ---
if __name__ == "__main__":
    logger.info("키움증권 API 모듈 테스트를 시작합니다 (클래스 방식).")
    
    api = KiwoomAPI()
    
    if api.token:
        logger.info(f"발급된 토큰 (앞 10자리): {api.token[:10]}...")
        
        # 상승률 상위 종목 조회
        top_rising_stocks = api.get_top_30_rising_stocks()
        if top_rising_stocks:
            logger.info("--- 상승률 상위 5개 종목 ---")
            for stock in top_rising_stocks[:5]:
                logger.info(f"  - {stock.get('stk_nm')}: {stock.get('flu_rt')}%")
    
    logger.info("키움증권 API 모듈 테스트를 종료합니다.")