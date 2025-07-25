import websocket
import json
import sqlite3
import configparser
import os
import time
import threading
import logging
import requests

# --- 로깅 설정 ---
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)

log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'realtime_collector.log')
file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
file_handler.setFormatter(formatter)

logger = logging.getLogger('realtime_collector')
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)

# --- 파일 경로 및 설정 로드 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = CURRENT_DIR

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
    WEBSOCKET_URL = BASE_URL.replace("https://", "wss://").replace("http://", "ws://") + ":10000/api/dostk/websocket"
except (configparser.NoSectionError, configparser.NoOptionError) as e:
    logger.error(f"오류: config.ini 파일에 [API] 섹션 또는 필요한 키가 누락되었습니다. ({e})")
    exit()

# --- 데이터베이스 관련 설정 및 함수 ---
DB_PATH = os.path.join(PROJECT_ROOT, 'stock_data.db')

def update_db_schema():
    """데이터베이스 테이블에 실시간 데이터를 저장할 컬럼들을 추가합니다.
    SQLite의 오래된 버전을 고려하여 'IF NOT EXISTS' 대신 PRAGMA를 사용하여 컬럼 존재 여부를 확인합니다."""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(f"PRAGMA table_info(all_stocks)")
        existing_columns = [col[1] for col in cursor.fetchall()]

        columns_to_add = {
            'current_price': 'REAL DEFAULT 0',
            'fluctuation_rate': 'REAL DEFAULT 0',
            'trade_volume': 'INTEGER DEFAULT 0',
            'trade_value': 'INTEGER DEFAULT 0',
            'base_price': 'REAL DEFAULT 0'
        }

        for col_name, col_type in columns_to_add.items():
            if col_name not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE all_stocks ADD COLUMN {col_name} {col_type}")
                    logger.info(f"컬럼 '{col_name}' 추가 성공.")
                except sqlite3.OperationalError as e:
                    logger.error(f"컬럼 '{col_name}' 추가 중 오류 발생: {e}")
            else:
                logger.info(f"컬럼 '{col_name}'이(가) 이미 존재합니다. 스키마 업데이트를 건너킵니다.")

        conn.commit()
        logger.info("데이터베이스 스키마 업데이트 시도 완료.")
    except sqlite3.OperationalError as e:
        logger.error(f"데이터베이스 스키마 확인 중 오류 발생: {e}")
    except Exception as e:
        logger.error(f"예상치 못한 데이터베이스 스키마 업데이트 오류: {e}")
    finally:
        if conn:
            conn.close()


def load_all_stock_codes():
    """DB에서 모든 종목 코드와 기본 정보를 로드합니다."""
    stocks_info = {}
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(f"PRAGMA table_info(all_stocks)")
        existing_columns = [col[1] for col in cursor.fetchall()]

        if 'base_price' in existing_columns:
            cursor.execute("SELECT code, name, marketCode, marketName, base_price FROM all_stocks")
        else:
            cursor.execute("SELECT code, name, marketCode, marketName FROM all_stocks")
        
        rows = cursor.fetchall()
        for row in rows:
            if 'base_price' in existing_columns and len(row) == 5:
                code, name, market_code, market_name, base_price = row
            else:
                code, name, market_code, market_name = row
                base_price = 0
            
            stocks_info[code] = {
                'name': name,
                'marketCode': market_code,
                'marketName': market_name,
                'base_price': base_price
            }
        conn.close()
        logger.info(f"DB에서 총 {len(stocks_info)}개의 종목 정보를 로드했습니다.")
    except Exception as e:
        logger.error(f"DB에서 종목 코드 로드 중 오류 발생: {e}")
    return stocks_info

def update_stock_realtime_data(stock_code, current_price, fluctuation_rate, trade_volume, trade_value):
    """실시간 데이터를 데이터베이스에 업데이트합니다."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE all_stocks
            SET current_price = ?, fluctuation_rate = ?, trade_volume = ?, trade_value = ?
            WHERE code = ?
            """,
            (current_price, fluctuation_rate, trade_volume, trade_value, stock_code)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"종목 {stock_code} 실시간 데이터 업데이트 중 오류 발생: {e}")

# --- 키움 API 접근 토큰 발급 함수 ---
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
        
        # 실제 API 응답에서 'token' 키를 사용하므로 다시 'token'으로 변경
        if res_json.get('token'): 
            logger.info("접근 토큰 발급 성공.")
            return res_json.get('token')
        else:
            logger.error(f"토큰 발급 실패: 응답에 token이 없습니다. 응답: {res_json}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"토큰 발급 API 요청 중 오류 발생: {e}")
        if e.response is not None:
            logger.error(f"응답 내용: {e.response.text}")
        return None

# --- WebSocket 이벤트 핸들러 ---
global_access_token = None
global_stock_data = {}

def on_message(ws, message):
    data = json.loads(message)
    logger.debug(f"수신된 원본 실시간 데이터: {json.dumps(data, indent=2, ensure_ascii=False)}")

    if 'body' in data and 'items' in data['body']:
        for item in data['body']['items']:
            stock_code = item.get('9001')
            
            # --- 중요: '현재가' 필드 ID를 정확히 찾아야 합니다. ---
            # '10'은 예시이며, 실제 API 문서 또는 로그에서 '현재가'에 해당하는 키(key)를 찾아야 합니다.
            # 이 키는 숫자 문자열 (예: '10', '11', '20' 등)일 수 있습니다.
            current_price_str = item.get('10') # <-- **이 부분을 정확한 '현재가' 필드 ID로 변경하세요!**
            
            trade_volume_str = item.get('13')
            trade_value_str = item.get('14')

            if stock_code and current_price_str and trade_volume_str and trade_value_str:
                try:
                    current_price = float(current_price_str.replace(',', '').replace('+', '').replace('-', ''))
                    trade_volume = int(trade_volume_str.replace(',', ''))
                    trade_value = int(trade_value_str.replace(',', ''))

                    fluctuation_rate = 0.0
                    base_price = global_stock_data.get(stock_code, {}).get('base_price')
                    
                    if base_price is not None and base_price != 0:
                        fluctuation_rate = ((current_price - base_price) / base_price) * 100
                    
                    update_stock_realtime_data(stock_code, current_price, fluctuation_rate, trade_volume, trade_value)
                    
                    logger.info(f"[{stock_code}] 현재가: {current_price}, 등락률: {fluctuation_rate:.2f}%, 거래량: {trade_volume}, 거래대금: {trade_value}")

                except ValueError as ve:
                    logger.error(f"실시간 데이터 변환 오류 for {stock_code}: {ve}, Data: {item}")
                except Exception as e:
                    logger.error(f"실시간 데이터 처리 중 오류 발생 for {stock_code}: {e}, Data: {item}")
            else:
                logger.debug(f"필수 실시간 데이터 필드 누락: stock_code={stock_code}, current_price_str={current_price_str}, trade_volume_str={trade_volume_str}, trade_value_str={trade_value_str}")


def on_error(ws, error):
    logger.error(f"WebSocket 오류: {error}")

def on_close(ws, close_status_code, close_msg):
    logger.warning(f"WebSocket 연결 종료: {close_status_code}, {close_msg}. 5초 후 재연결 시도...")
    time.sleep(5)
    start_realtime_collection()

def on_open(ws):
    logger.info("WebSocket 연결 성공. 실시간 시세 등록 요청을 보냅니다.")
    
    def subscribe_all_stocks():
        if not global_stock_data:
            logger.warning("등록할 종목이 DB에 없습니다. 'stock_collector.py'를 먼저 실행하여 종목 정보를 수집해주세요.")
            return

        all_codes = list(global_stock_data.keys())
        BATCH_SIZE = 100

        for i in range(0, len(all_codes), BATCH_SIZE):
            batch_codes = all_codes[i:i + BATCH_SIZE]
            items_to_subscribe = []
            for code in batch_codes:
                items_to_subscribe.append({
                    "item": f"KRX:{code}",
                    "type": "0g" # 0g는 실시간 데이터의 '종류'를 의미합니다.
                })
            
            # --- 중요: 실시간 시세 구독 요청의 'api-id'를 정확히 지정해야 합니다. ---
            # '0g'는 실시간 항목의 타입이며, 구독 요청 자체의 api-id가 아닙니다.
            # 키움증권 REST API 문서에서 '실시간 시세 구독' 또는 '실시간 데이터 등록'과 관련된
            # 정확한 'API ID'를 찾아 아래 "YOUR_REALTIME_SUBSCRIBE_API_ID"를 변경해야 합니다.
            subscribe_message = {
                "header": {
                    "api-id": "YOUR_REALTIME_SUBSCRIBE_API_ID", # <-- **이 부분을 정확한 API ID로 변경!**
                    "authorization": f"Bearer {global_access_token}"
                },
                "body": {
                    "trnm": "REG", # 'REG'가 맞다면 유지, 아니라면 API 문서에 따라 변경
                    "grp_no": "0001",
                    "refresh": "0", # 0: 기존 등록 해지 후 등록, 1: 추가 등록
                    "data": items_to_subscribe
                }
            }
            
            try:
                ws.send(json.dumps(subscribe_message))
                logger.info(f"[{i+BATCH_SIZE}/{len(all_codes)}] {len(items_to_subscribe)}개 종목의 실시간 시세 등록 요청 완료.")
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"실시간 시세 등록 요청 중 오류 발생: {e}")

    threading.Thread(target=subscribe_all_stocks).start()

def start_realtime_collection():
    """실시간 시세 수집을 시작합니다."""
    global global_access_token, global_stock_data

    logger.info("--- 실시간 시세 수집 시작 ---")

    token_params = {
        'grant_type': 'client_credentials',
        'appkey': APP_KEY,
        'secretkey': APP_SECRET,
    }
    
    global_access_token = issue_access_token(base_url=BASE_URL, data=token_params)

    if not global_access_token:
        logger.error("접근 토큰 발급 실패. 실시간 수집을 시작할 수 없습니다.")
        return

    update_db_schema()

    global_stock_data = load_all_stock_codes()
    if not global_stock_data:
        logger.error("DB에 종목 정보가 없습니다. 'stock_collector.py'를 먼저 실행하여 초기 종목 정보를 수집해주세요.")
        return

    logger.info(f"WebSocket URL: {WEBSOCKET_URL}")
    ws = websocket.WebSocketApp(WEBSOCKET_URL,
                                 on_open=on_open,
                                 on_message=on_message,
                                 on_error=on_error,
                                 on_close=on_close)
    
    wst = threading.Thread(target=ws.run_forever, daemon=True)
    wst.start()

    logger.info("실시간 시세 수집 스크립트가 백그라운드에서 실행 중입니다. 중지하려면 Ctrl+C를 누르세요.")
    
    try:
        while wst.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Ctrl+C 감지. WebSocket 연결을 종료합니다.")
        ws.close()
        wst.join()
    logger.info("실시간 시세 수집 스크립트 종료.")


if __name__ == "__main__":
    start_realtime_collection()