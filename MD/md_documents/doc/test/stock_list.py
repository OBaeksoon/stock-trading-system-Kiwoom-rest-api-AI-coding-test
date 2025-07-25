import requests
import json
import configparser
import os
import time
import sqlite3 # 데이터베이스 저장을 위해 sqlite3 직접 사용
import logging

# --- 로깅 설정 ---
# 로그 포맷터 생성
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# 스트림 핸들러 (콘솔 출력용)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)

# 파일 핸들러 (파일 저장용)
log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'stock_collector.log')
file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
file_handler.setFormatter(formatter)

# 로거 설정
logger = logging.getLogger('stock_collector')
logger.setLevel(logging.INFO) # 로그 레벨 설정 (INFO, DEBUG 등)
if not logger.handlers:
    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)

# --- 파일 경로 및 설정 로드 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(CURRENT_DIR) # 경로를 현재 파일 위치로 조정

config = configparser.ConfigParser()
config_path = os.path.join(PROJECT_ROOT, 'config.ini')

if not os.path.exists(config_path):
    logger.error(f"오류: 설정 파일({config_path})을 찾을 수 없습니다.")
    exit()
config.read(config_path)

try:
    APP_KEY = config['API']['APP_KEY']
    APP_SECRET = config['API']['APP_SECRET']
    BASE_URL = config['API']['BASE_URL']
except (configparser.NoSectionError, configparser.NoOptionError) as e:
    logger.error(f"오류: config.ini 파일에 [API] 섹션 또는 필요한 키가 누락되었습니다. ({e})")
    logger.error("[API] 섹션 안에 APP_KEY, APP_SECRET, BASE_URL 키가 있는지 확인해주세요.")
    exit()

# --- 데이터베이스 관련 함수 ---
DB_PATH = os.path.join(PROJECT_ROOT, 'stock_data.db')

def initialize_db():
    """데이터베이스와 테이블을 생성하고 초기화합니다."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS all_stocks")
        cursor.execute('''
        CREATE TABLE all_stocks (
            code TEXT PRIMARY KEY,
            name TEXT,
            marketCode TEXT,
            marketName TEXT
        )
        ''')
        conn.commit()
        conn.close()
        logger.info("데이터베이스 테이블 'all_stocks'가 성공적으로 초기화되었습니다.")
    except Exception as e:
        logger.error(f"데이터베이스 초기화 중 오류 발생: {e}")

def save_all_stocks_to_db(stocks_list):
    """수집된 모든 종목 정보를 데이터베이스에 저장합니다."""
    if not stocks_list:
        logger.warning("저장할 종목 데이터가 없습니다.")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 'marketCode'와 'marketName' 필드가 없는 경우를 대비하여 None으로 기본값 처리
        formatted_data = [
            (
                stock.get('code'), 
                stock.get('name'),
                stock.get('marketCode'),
                stock.get('marketName')
            ) 
            for stock in stocks_list
        ]
        
        cursor.executemany("INSERT OR REPLACE INTO all_stocks (code, name, marketCode, marketName) VALUES (?, ?, ?, ?)", formatted_data)
        conn.commit()
        conn.close()
        logger.info(f"총 {len(stocks_list)}개의 종목 정보가 데이터베이스에 저장되었습니다.")
    except Exception as e:
        logger.error(f"데이터베이스에 종목 정보 저장 중 오류 발생: {e}")


# --- 키움 API 관련 함수 ---
def issue_access_token(base_url, data):
    """API 접근 토큰을 발급받습니다."""
    host = base_url
    endpoint = '/oauth2/token'
    url = host + endpoint
    headers = {'Content-Type': 'application/json;charset=UTF-8'}
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        res_json = response.json()
        
        if res_json.get('token'):
            logger.info("접근 토큰 발급 성공.")
            return res_json
        else:
            logger.error(f"토큰 발급 실패: 응답에 access_token이 없습니다. 응답: {res_json}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"토큰 발급 API 요청 중 오류 발생: {e}")
        if e.response is not None:
            logger.error(f"응답 내용: {e.response.text}")
        return None

def get_all_stocks_list_by_market(token, base_url, market_type):
    """특정 시장의 모든 종목 정보를 페이지네이션을 통해 가져옵니다."""
    host = base_url
    endpoint = '/api/dostk/stkinfo'
    url = host + endpoint

    market_stocks = []
    cont_yn = 'N'
    next_key = ''
    market_name = "코스피" if market_type == '0' else "코스닥"
    
    logger.info(f"--- {market_name} 종목 정보 수집 시작 ---")

    while True:
        headers = {
            'Content-Type': 'application/json;charset=UTF-8',
            'authorization': f'Bearer {token}',
            'cont-yn': cont_yn,
            'next-key': next_key,
            'api-id': 'ka10099',
        }
        params = {'mrkt_tp': market_type}

        try:
            response = requests.post(url, headers=headers, json=params)
            response.raise_for_status()
            res_json = response.json()

            if res_json.get('list') and isinstance(res_json['list'], list):
                new_stocks = res_json['list']
                if new_stocks:
                    market_stocks.extend(new_stocks)
                    logger.info(f"({market_name}) {len(new_stocks)}개 종목 추가. (현재까지 총 {len(market_stocks)}개)")
                else:
                    logger.info(f"({market_name}) 더 이상 수집할 종목이 없어 수집을 중단합니다.")
                    break
            else:
                logger.warning(f"({market_name}) API 응답에 'list' 필드가 없거나 유효하지 않습니다: {res_json}")
                break

            cont_yn = response.headers.get('cont-yn', 'N')
            next_key = response.headers.get('next-key', '')

            if cont_yn != 'Y' or not next_key:
                break
            
            # API 호출 제한(rate limit)을 피하기 위한 지연 시간 (0.5초)
            # 60초는 너무 길어서 단축했습니다. 필요 시 조정하세요.
            time.sleep(0.5)

        except requests.exceptions.RequestException as e:
            logger.error(f"({market_name}) API 요청 중 오류: {e}")
            if e.response:
                logger.error(f"응답 상태 코드: {e.response.status_code}, 내용: {e.response.text}")
            return []
        except json.JSONDecodeError:
            logger.error(f"({market_name}) JSON 파싱 오류. 응답: {response.text}")
            return []

    logger.info(f"--- 총 {len(market_stocks)}개의 {market_name} 종목 정보 수집 완료 ---")
    return market_stocks

# --- 메인 실행 로직 ---
if __name__ == '__main__':
    logger.info("--- 코스피/코스닥 전종목 정보 업데이트 시작 ---")
    initialize_db()

    token_params = {
        'grant_type': 'client_credentials',
        'appkey': APP_KEY,
        'secretkey': APP_SECRET,
    }
    
    token_response = issue_access_token(base_url=BASE_URL, data=token_params)
    access_token = token_response.get('token') if token_response else None

    if access_token:
        all_stocks = []
        
        # 코스피 종목 조회 (mrkt_tp='0')
        kospi_stocks = get_all_stocks_list_by_market(access_token, BASE_URL, '0')
        all_stocks.extend(kospi_stocks)

        # API 요청 속도 제한을 피하기 위해 1초 대기
        time.sleep(1) 

        # 코스닥 종목 조회 (mrkt_tp='10')
        kosdaq_stocks = get_all_stocks_list_by_market(access_token, BASE_URL, '10')
        all_stocks.extend(kosdaq_stocks)

        if all_stocks:
            logger.info(f"\n--- 최종 수집된 전체 종목 수: {len(all_stocks)}개 ---")
            save_all_stocks_to_db(all_stocks)
        else:
            logger.info("수집된 종목이 없어 DB 저장을 건너뜁니다.")
    else:
        logger.error("토큰 발급 실패로 종목 정보 업데이트를 중단합니다.")

    logger.info("--- 전종목 정보 업데이트 완료 ---")