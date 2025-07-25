import asyncio
import websockets
import json
import configparser
import os
import sqlite3
import datetime
import logging
import time # For sleep in main loop

# kiwoom_api 모듈 import (가정: kiwoom_api.py 파일이 같은 디렉토리 또는 PYTHONPATH에 있음)
import kiwoom_api 

# --- 파일 경로 및 로거 설정 (kiwoom_api와 일관되게 설정) ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(CURRENT_DIR, '..') # 현재 스크립트가 public_html/python_modules 안에 있다면, 상위 public_html이 프로젝트 루트가 됨

CONFIG_FILE = os.path.join(PROJECT_ROOT, 'config.ini')
DB_FILE = os.path.join(PROJECT_ROOT, 'stock_data.db')
LOG_DIR = os.path.join(PROJECT_ROOT, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, f"realtime_updater_{datetime.datetime.now().strftime('%Y%m%d')}.log")
logger = logging.getLogger(__name__) # Use __name__ to differentiate from kiwoom_api's logger
logger.setLevel(logging.INFO)
# 기존 핸들러가 있다면 제거 (중복 로깅 방지)
if not logger.handlers:
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    # 콘솔 출력도 추가 (옵션)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(stream_handler)


# --- 설정 로드 ---
config = configparser.ConfigParser()
config.read(CONFIG_FILE)

try:
    BASE_URL = config.get('API', 'BASE_URL')
    APP_KEY = config.get('API', 'APP_KEY')
    APP_SECRET = config.get('API', 'APP_SECRET')
    SOCKET_URL = 'wss://mockapi.kiwoom.com:10000/api/dostk/websocket' # 모의투자 WebSocket URL 고정
except (configparser.NoSectionError, configparser.NoOptionError) as e:
    logger.error(f"오류: config.ini 파일의 내용이 올바르지 않습니다. ({e})")
    logger.error("Please ensure [API] section and BASE_URL, APP_KEY, APP_SECRET keys are present.")
    BASE_URL = None
    APP_KEY = None
    APP_SECRET = None
    SOCKET_URL = None

# --- DB 업데이트 유틸리티 함수 ---
def update_stock_realtime_data(stock_code, data):
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Mock API의 '0A' 타입 응답 구조에 맞춰 필드 추출
        # 실제 API 응답을 보고 정확한 키 이름을 확인하고 필요 시 수정해야 합니다.
        # 예시: {'trnm': 'REAL', 'item': '005930', '0A': {'lastPrice': '1,000', 'changeFromPrevDay': '50', ...}}
        
        current_price = float(data.get('lastPrice', '0').replace(',', '')) if data.get('lastPrice') else 0.0
        change_from_prev_day = float(data.get('changeFromPrevDay', '0').replace(',', '')) if data.get('changeFromPrevDay') else 0.0
        fluctuation_rate = str(data.get('fluctuationRate', ''))
        trade_volume = int(data.get('tradeVolume', '0').replace(',', '')) if data.get('tradeVolume') else 0
        trade_amount = int(data.get('tradeAmount', '0').replace(',', '')) if data.get('tradeAmount') else 0
        
        # 마지막 업데이트 시간 필드가 있는지 확인하고 없다면 추가
        cursor.execute("PRAGMA table_info(korean_stock_list);")
        columns = [col[1] for col in cursor.fetchall()]
        if 'last_updated' not in columns:
            cursor.execute("ALTER TABLE korean_stock_list ADD COLUMN last_updated TIMESTAMP;")

        cursor.execute('''
            UPDATE korean_stock_list
            SET cur_prc = ?, cmpr_yd = ?, flu_rt = ?, trde_qty = ?, trde_amt = ?, last_updated = CURRENT_TIMESTAMP
            WHERE stk_cd = ?
        ''', (current_price, change_from_prev_day, fluctuation_rate, trade_volume, trade_amount, stock_code))
        conn.commit()
        # logger.debug(f"DB 업데이트 완료: 종목코드={stock_code}, 현재가={current_price}, 전일대비={change_from_prev_day}, 등락률={fluctuation_rate}, 거래량={trade_volume}, 거래대금={trade_amount}")
    except Exception as e:
        logger.error(f"종목 {stock_code}의 실시간 데이터 DB 업데이트 중 오류 발생: {e}")
    finally:
        if conn:
            conn.close()

# --- WebSocket 클라이언트 클래스 ---
class WebSocketClient:
    def __init__(self, uri, access_token):
        self.uri = uri
        self.access_token = access_token
        self.websocket = None
        self.connected = False
        self.keep_running = True
        self.stock_codes_to_subscribe = []
        self.ping_task = None # PING 전송 태스크

    async def connect(self):
        try:
            self.websocket = await websockets.connect(self.uri)
            self.connected = True
            logger.info("서버와 연결을 시도 중입니다.")

            param = {
                'trnm': 'LOGIN',
                'token': self.access_token
            }

            logger.info('실시간 시세 서버로 로그인 패킷을 전송합니다.')
            await self.send_message(message=param)

            # 연결 성공 후 PING 태스크 시작 (이전 태스크가 있다면 취소)
            if self.ping_task:
                self.ping_task.cancel()
            self.ping_task = asyncio.create_task(self.send_ping_periodically())


        except Exception as e:
            logger.error(f'연결 오류 발생: {e}')
            self.connected = False
            if self.ping_task:
                self.ping_task.cancel()
                self.ping_task = None
            await asyncio.sleep(5) # 재연결 시도 전 잠시 대기

    async def send_message(self, message):
        if not self.connected:
            # 연결이 끊어졌다면 재연결을 시도하지 않고 오류 기록 후 반환
            logger.warning("연결되지 않은 상태에서 메시지 전송 시도. 메시지: %s", message)
            return
            
        if not isinstance(message, str):
            message = json.dumps(message)

        try:
            await self.websocket.send(message)
            #logger.debug(f'메시지 전송: {message}') # 너무 많은 로그 방지
        except websockets.exceptions.ConnectionClosedOK:
            logger.warning("메시지 전송 중 연결이 끊어졌습니다 (정상 종료). 재연결 시도...")
            self.connected = False
            if self.ping_task:
                self.ping_task.cancel()
                self.ping_task = None
            await self.connect() # 연결 끊김 시 재연결 시도
            if self.connected: # 재연결 성공 시 메시지 재전송
                await self.websocket.send(message)
        except Exception as e:
            logger.error(f"메시지 전송 오류: {e}")
            self.connected = False
            if self.ping_task:
                self.ping_task.cancel()
                self.ping_task = None
            # 오류 발생 시 재연결을 위해 run 루프가 connect를 호출하도록
            
    async def send_ping_periodically(self):
        """주기적으로 PING 메시지를 보내 연결을 유지합니다."""
        while self.connected and self.keep_running:
            try:
                # 서버 요구사항에 따라 PING 주기 조절 (예: 30초)
                await asyncio.sleep(30) 
                if self.connected:
                    ping_message = {'trnm': 'PING'}
                    await self.send_message(ping_message)
                    # logger.debug("PING 메시지 전송 완료.")
            except asyncio.CancelledError:
                logger.info("PING 전송 태스크가 취소되었습니다.")
                break
            except Exception as e:
                logger.error(f"주기적인 PING 전송 중 오류 발생: {e}")
                # 오류 발생 시 연결 끊고 재연결 시도하도록
                self.connected = False
                break # PING 루프 종료, run 루프가 재연결 담당

    async def receive_messages(self):
        while self.keep_running:
            try:
                response_str = await self.websocket.recv()
                response = json.loads(response_str)

                if response.get('trnm') == 'LOGIN':
                    if response.get('return_code') != 0:
                        logger.error(f'로그인 실패: {response.get("return_msg")}')
                        await self.disconnect()
                    else:
                        logger.info('로그인 성공.')
                        await self.subscribe_to_stocks() # 로그인 성공 후 종목 구독

                elif response.get('trnm') == 'PING':
                    # 서버로부터 PING 받으면 즉시 응답 (이전 코드와 동일)
                    await self.send_message(response)
                    # logger.debug("서버로부터 PING 수신 후 응답.")
                
                elif response.get('trnm') != 'PING': # PING 메시지가 아닐 경우에만 로그 출력 및 DB 업데이트
                    logger.info(f'실시간 시세 서버 응답 수신: {response}') # 너무 많은 로그 방지
                    if response.get('trnm') == 'REAL' and response.get('item'):
                        stock_code = response['item']
                        realtime_data = response.get('0A', response) # '0A' 필드 또는 전체 응답 사용
                        update_stock_realtime_data(stock_code, realtime_data)
                        logger.info(f"종목 {stock_code} 실시간 데이터 처리 완료.")


            except websockets.ConnectionClosed:
                logger.warning('서버에 의해 연결이 끊어졌습니다 (ConnectionClosed). 재연결 시도...')
                self.connected = False
                if self.ping_task:
                    self.ping_task.cancel()
                    self.ping_task = None
                # run 루프에서 재연결을 처리하도록 break
                break 
            except json.JSONDecodeError:
                logger.error(f"JSON 파싱 오류. 수신된 응답: {response_str[:200]}...")
            except asyncio.CancelledError:
                logger.info("메시지 수신 태스크가 취소되었습니다.")
                break
            except Exception as e:
                logger.error(f'메시지 수신 중 예상치 못한 오류 발생: {e}')
                # 오류 발생 시 연결 끊고 재연결 시도하도록
                self.connected = False
                if self.ping_task:
                    self.ping_task.cancel()
                    self.ping_task = None
                break # receive_messages 루프 종료, run 루프가 재연결 담당

    async def run(self):
        while self.keep_running:
            if not self.connected:
                await self.connect()
                if not self.connected: # connect 시도 후에도 연결 실패
                    logger.error("WebSocket 연결 실패. 10초 후 재시도...")
                    await asyncio.sleep(10)
                    continue # 다음 루프에서 다시 connect 시도
            
            # 연결이 되었으면 메시지 수신 시작
            await self.receive_messages()
            # receive_messages가 종료되면 (연결 끊김 등) 다시 connect 시도

    async def subscribe_to_stocks(self):
        if not self.stock_codes_to_subscribe:
            logger.info("구독할 종목 코드가 없습니다. 데이터베이스에서 종목 코드를 로드해주세요.")
            return

        # --- 종목 구독 요청 분할 처리 시작 ---
        # Mock API 허용 개수(100)에 맞춰 분할
        chunk_size = 100 
        total_stocks = len(self.stock_codes_to_subscribe)
        group_number = 1 # 그룹 번호 초기화
        
        logger.info(f"총 {total_stocks}개의 종목을 {chunk_size}개씩 분할하여 실시간 등록 요청합니다.")

        for i in range(0, total_stocks, chunk_size):
            chunk = self.stock_codes_to_subscribe[i:i + chunk_size]
            
            subscription_data_entry = {
                'item': chunk, # 분할된 종목 코드 리스트 전달
                'type': ['0A'], # 기본 실시간 시세 (체결) 데이터 타입
            }

            reg_message = {
                'trnm': 'REG',
                'grp_no': str(group_number), # 그룹 번호를 문자열로 변환하여 설정
                'refresh': '0', # 새 그룹으로 등록하므로 '0'으로 설정 (기존 등록 유지 불필요)
                'data': [subscription_data_entry]
            }

            logger.info(f"실시간 항목 등록 요청 전송 (그룹 {group_number}, {i+1} ~ {min(i + chunk_size, total_stocks)}번째 종목).")
            await self.send_message(reg_message)
            
            group_number += 1 # 다음 요청을 위해 그룹 번호 증가
            
            # 각 요청 사이에 짧은 지연 시간을 두어 서버 부하 방지
            await asyncio.sleep(0.5) # 0.5초 지연

        logger.info("모든 실시간 항목 등록 요청 전송 완료.")
        # --- 종목 구독 요청 분할 처리 끝 ---

    async def disconnect(self):
        self.keep_running = False
        if self.ping_task:
            self.ping_task.cancel()
            self.ping_task = None
        if self.connected and self.websocket:
            try:
                await self.websocket.close()
                self.connected = False
                logger.info('WebSocket 서버 연결 해제됨')
            except Exception as e:
                logger.error(f"WebSocket 연결 해제 중 오류 발생: {e}")

# --- 메인 실행 로직 ---
async def main():
    logger.info("--- 실시간 종목 시세 업데이트 스크립트 시작 ---")

    if not all([APP_KEY, APP_SECRET, BASE_URL, SOCKET_URL]):
        logger.error("config.ini에서 API 설정 또는 WebSocket URL을 로드할 수 없습니다.")
        return

    # 접근 토큰 발급 (kiwoom_api 모듈 재사용)
    # 실제 API 호출 시에는 ACCESS_TOKEN을 직접 설정하거나 별도 저장소에서 가져와야 합니다.
    # Mock API는 APP_KEY와 APP_SECRET 대신 임의의 토큰을 사용할 수 있습니다.
    # 이 부분은 실제 연동 시 Kiwoom API의 토큰 발급 프로세스에 따라 달라질 수 있습니다.
    
    # Kiwoom mockapi documentation states ACCESS_TOKEN from previous login is used
    # Let's assume access_token is obtained in kiwoom_api module or config.
    # For a real integration, you would call Kiwoom's token issuance API here.
    
    # 현재 Kiwoom mockapi.kiwoom.com은 ACCESS_TOKEN이 고정되어 있거나
    # 개발자센터에서 발급받은 것을 그대로 사용하는 경우가 많으므로
    # 여기서는 config.ini에서 ACCESS_TOKEN을 직접 로드하는 방식을 사용하는 것이 합리적입니다.
    # config.ini에 ACCESS_TOKEN = [실제 토큰 값] 을 추가했다고 가정합니다.
    try:
        ACCESS_TOKEN_FROM_CONFIG = config.get('API', 'ACCESS_TOKEN')
        logger.info("config.ini에서 Access Token을 로드했습니다.")
    except (configparser.NoSectionError, configparser.NoOptionError):
        logger.warning("config.ini에서 'API' 섹션 또는 'ACCESS_TOKEN'을 찾을 수 없습니다. 임시 토큰 발급을 시도합니다.")
        # kiwoom_api.issue_access_token을 사용한 토큰 발급은 일반 REST API이며, 
        # Mock WebSocket API와는 별개일 수 있습니다. 
        # 하지만 일단 Mock API의 토큰 발급 예시가 없다면 시도합니다.
        token_data = {'grant_type': 'client_credentials', 'appkey': APP_KEY, 'secretkey': APP_SECRET}
        token_response = kiwoom_api.issue_access_token(base_url=BASE_URL, data=token_data)
        ACCESS_TOKEN_FROM_CONFIG = token_response.get('access_token') if token_response else None
        
        if not ACCESS_TOKEN_FROM_CONFIG:
            logger.error("접근 토큰을 발급받을 수 없어 실시간 업데이트를 시작할 수 없습니다. config.ini의 ACCESS_TOKEN 확인 필요.")
            return


    # DB에서 모든 종목 코드 로드
    all_stock_codes = []
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT stk_cd FROM korean_stock_list LIMIT 100")
        all_stock_codes = [row[0] for row in cursor.fetchall()]
        logger.info(f"데이터베이스에서 총 {len(all_stock_codes)}개의 종목 코드를 로드했습니다.")
        if not all_stock_codes:
            logger.warning("데이터베이스에 종목 코드가 없습니다. get_all_stocks.py를 먼저 실행하여 종목을 로드해주세요.")
            return
    except Exception as e:
        logger.error(f"데이터베이스에서 종목 코드를 로드하는 중 오류 발생: {e}")
        return
    finally:
        if conn:
            conn.close()

    websocket_client = WebSocketClient(SOCKET_URL, ACCESS_TOKEN_FROM_CONFIG)
    websocket_client.stock_codes_to_subscribe = all_stock_codes

    # run 태스크를 생성하여 클라이언트 실행
    run_task = asyncio.create_task(websocket_client.run())

    # 스크립트가 계속 실행되도록 유지 (비동기 태스크를 백그라운드에서 실행)
    try:
        # main 함수가 바로 종료되지 않도록 무한정 대기
        await run_task 
    except asyncio.CancelledError:
        logger.info("메인 루프가 취소되었습니다.")
    finally:
        await websocket_client.disconnect()
        logger.info("--- 실시간 종목 시세 업데이트 스크립트 종료 ---")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("스크립트가 사용자 요청에 의해 종료되었습니다.")
    except Exception as e:
        logger.error(f"스크립트 실행 중 예기치 않은 오류 발생: {e}")