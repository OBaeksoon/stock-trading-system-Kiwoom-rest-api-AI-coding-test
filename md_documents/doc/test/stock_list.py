'''
로그를 분석한 결과 동일한 APP_KEY로 여러 번 접속을 시도하면서 기존 연결이 끊어지는 문제가 발생하고 있습니다.

로그에 나타난 '동일한 App key로 접속이 되었습니다. 기존 세션은 종료가 됩니다' 메시지가 이 문제의 직접적인 원인입니다.

## 문제 원인
제공된 코드(get_all_stocks_list_by_market 함수)는 단순한 HTTP 요청-응답 방식으로 종목 정보를 가져오는 역할을 합니다. 하지만 함께 제공된 로그를 보면, 이 코드와는 별개로 실시간 시세(WebSocket) 서버에 접속하는 로직이 백그라운드에서 실행되고 있는 것으로 보입니다.

문제 발생 시나리오

백그라운드에서 kiwoom_api 모듈의 일부가 **실시간 시세 서버(WebSocket)**에 이미 접속해 있습니다.

사용자가 첨부한 코드를 실행하면, kiwoom_api.issue_access_token 함수를 통해 새로운 토큰을 발급받아 종목 목록을 조회합니다.

이 과정에서 kiwoom_api 모듈 내부의 다른 로직이 다시 한번 실시간 시세 서버에 접속을 시도하거나, 혹은 다른 스크립트가 동일한 APP_KEY로 실행되면서 기존의 실시간 세션을 끊어버립니다.

기존 세션이 끊기면, 백그라운드의 실시간 모듈은 자동으로 재연결을 시도합니다.

이러한 '끊김과 재연결'이 반복되면서 안정적인 통신이 불가능해집니다.

## 해결 방안
이 문제를 해결하기 위해서는 API 요청의 목적에 맞게 코드를 분리하고, 불필요한 실시간 접속을 방지해야 합니다.

해결 코드

아래 코드는 오직 종목 목록을 조회하고 DB에 저장하는 목적에만 집중하도록 수정한 버전입니다. 실시간 시세(WebSocket) 관련 로직은 별도의 파일로 분리하여 필요할 때만 실행하는 것을 권장합니다.
## 주요 변경 사항
kiwoom_api 모듈 의존성 제거: 종목 목록 조회 기능은 실시간 시세와 관련이 없으므로, 불필요한 kiwoom_api 모듈 import를 제거했습니다. 대신 토큰 발급 및 DB 저장 함수를 이 파일 내에 직접 구현하여 코드의 역할을 명확히 했습니다.

독립적인 로깅 설정: kiwoom_api 모듈의 로거를 사용하는 대신, 이 스크립트 전용의 독립적인 로거(stock_collector)를 설정했습니다. 이를 통해 다른 모듈의 로그와 섞이지 않고 문제 파악이 용이해집니다.

API 호출 지연 시간 조정: 한 페이지를 받고 다음 페이지를 요청할 때의 time.sleep(60)은 지나치게 깁니다. 키움 API의 초당 요청 제한(Rate Limit)을 피하는 목적으로 0.5초 정도로 짧게 조정하여 데이터 수집 속도를 개선했습니다.

DB 저장 로직 직접 구현: sqlite3 모듈을 직접 사용하여 DB 저장 로직을 명확하게 만들었습니다. API 응답 형식에 맞춰 marketCode, marketName 필드도 함께 저장하도록 개선했습니다.

경로 설정 수정: PROJECT_ROOT 경로가 한 단계 상위 폴더로 잘못 설정될 수 있는 부분을 현재 파일이 위치한 디렉토리로 명확하게 수정했습니다.
'''
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