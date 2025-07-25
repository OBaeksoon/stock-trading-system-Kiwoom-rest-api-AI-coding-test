
import asyncio
import websockets
import json
import os
import sqlite3
import logging
from datetime import datetime

# --- 경로 설정 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(CURRENT_DIR, '..')
DB_FILE = os.path.join(PROJECT_ROOT, 'stock_data.db')
LOG_DIR = os.path.join(PROJECT_ROOT, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# --- 로거 설정 ---
log_file = os.path.join(LOG_DIR, f"realtime_condition_{datetime.now().strftime('%Y%m%d')}.log")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)
# 콘솔 핸들러 추가 (터미널에서 직접 실행 시 로그 확인용)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
logger.addHandler(console_handler)


# --- 설정값 ---
# 키움증권 실시간 API URL
SOCKET_URL = 'wss://mockapi.kiwoom.com:10000/api/dostk/websocket'

def get_access_token_from_db():
    """데이터베이스에서 가장 최근의 Access Token을 가져옵니다."""
    if not os.path.exists(DB_FILE):
        logger.error(f"데이터베이스 파일이 존재하지 않습니다: {DB_FILE}")
        logger.error("먼저 kiwoom_api.py를 실행하여 토큰을 발급하고 DB에 저장해주세요.")
        return None
        
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        # api_info 테이블이 없을 경우를 대비
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='api_info'")
        if cursor.fetchone() is None:
            logger.error("DB에 'api_info' 테이블이 없습니다. kiwoom_api.py를 실행해주세요.")
            conn.close()
            return None

        cursor.execute("SELECT access_token FROM api_info ORDER BY id DESC LIMIT 1")
        token_row = cursor.fetchone()
        conn.close()
        
        if token_row and token_row[0]:
            logger.info("데이터베이스에서 Access Token을 성공적으로 불러왔습니다.")
            return token_row[0]
        else:
            logger.warning("데이터베이스에 저장된 Access Token이 없습니다.")
            return None
    except sqlite3.Error as e:
        logger.error(f"데이터베이스 접근 중 오류 발생: {e}")
        return None


class KiwoomWebSocketClient:
    def __init__(self, uri, access_token):
        self.uri = uri
        self.access_token = access_token
        self.websocket = None
        self.is_connected = False
        self.keep_running = True

    async def connect(self):
        """WebSocket 서버에 연결하고 로그인을 시도합니다."""
        try:
            self.websocket = await websockets.connect(self.uri)
            self.is_connected = True
            logger.info("WebSocket 서버에 연결되었습니다. 로그인을 시도합니다.")
            
            login_packet = {
                'trnm': 'LOGIN',
                'token': self.access_token
            }
            await self.send_packet(login_packet)
        except Exception as e:
            logger.error(f"WebSocket 연결 오류: {e}")
            self.is_connected = False

    async def send_packet(self, packet_data):
        """서버로 JSON 형식의 패킷을 전송합니다."""
        if self.is_connected:
            try:
                message = json.dumps(packet_data)
                await self.websocket.send(message)
                logger.info(f"패킷 전송 완료: {message}")
            except Exception as e:
                logger.error(f"패킷 전송 중 오류 발생: {e}")

    async def receive_messages(self):
        """서버로부터 메시지를 지속적으로 수신하고 처리합니다."""
        while self.keep_running:
            try:
                response_str = await self.websocket.recv()
                response = json.loads(response_str)

                trnm = response.get('trnm')
                
                if trnm == 'LOGIN':
                    if response.get('return_code') == 0:
                        logger.info("로그인 성공. 조건검색을 요청합니다.")
                        # 로그인 성공 시 조건검색 요청
                        # seq: 조건검색식 일련번호 (사용자 맞게 변경 필요)
                        # search_type: 1 (실시간)
                        # stex_tp: K (코스피/코스닥)
                        condition_req_packet = {
                            'trnm': 'CNSRREQ',
                            'seq': '67',  # 피봇일목거래량돌파 조건식
                            'search_type': '1',
                            'stex_tp': 'K',
                        }
                        await self.send_packet(condition_req_packet)
                    else:
                        logger.error(f"로그인 실패: {response.get('return_msg')}")
                        await self.disconnect()

                elif trnm == 'PING':
                    # PING 메시지 수신 시 그대로 응답
                    await self.send_packet(response)
                
                elif trnm == 'CNSRCON': # 조건검색 결과 수신
                     logger.info(f"조건검색 결과 수신: {response}")

                else:
                    logger.info(f"기타 응답 수신: {response}")

            except websockets.ConnectionClosed as e:
                logger.warning(f"서버와 연결이 끊어졌습니다: {e}")
                self.is_connected = False
                break # 루프 종료
            except Exception as e:
                logger.error(f"메시지 수신 중 오류 발생: {e}")
                self.keep_running = False

    async def run(self):
        """WebSocket 클라이언트를 실행합니다."""
        if not self.access_token:
            logger.error("Access Token이 없어 클라이언트를 실행할 수 없습니다.")
            return
            
        await self.connect()
        if self.is_connected:
            await self.receive_messages()
        logger.info("클라이언트 실행을 종료합니다.")

    async def disconnect(self):
        """서버와의 연결을 종료합니다."""
        self.keep_running = False
        if self.is_connected and self.websocket:
            await self.websocket.close()
            self.is_connected = False
            logger.info("WebSocket 서버와 연결을 종료했습니다.")

async def main():
    access_token = get_access_token_from_db()
    
    if not access_token:
        logger.critical("Access Token을 찾을 수 없습니다. 프로그램을 종료합니다.")
        return

    client = KiwoomWebSocketClient(SOCKET_URL, access_token)
    
    try:
        await client.run()
    except KeyboardInterrupt:
        logger.info("사용자에 의해 프로그램이 중단되었습니다.")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
