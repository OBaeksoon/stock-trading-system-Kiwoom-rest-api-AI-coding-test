import asyncio
import websockets
import json
import configparser
import os

# Load API keys from config.ini
config = configparser.ConfigParser()
config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config.ini')
config.read(config_path)

APP_KEY = config['API']['APP_KEY']
APP_SECRET = config['API']['APP_SECRET']
BASE_URL = config['API']['BASE_URL']

# socket 정보
SOCKET_URL = f'wss://{BASE_URL.replace("https://", "")}:10000/api/dostk/websocket'  # 모의투자 접속 URL

# Access Token 발급 함수 (get_condition_list.py에서 가져옴)
import requests
def get_access_token():
    host = BASE_URL
    endpoint = '/oauth2/token'
    url = host + endpoint

    headers = {
        'Content-Type': 'application/json;charset=UTF-8',
    }

    params = {
        'grant_type': 'client_credentials',
        'appkey': APP_KEY,
        'secretkey': APP_SECRET,
    }

    response = requests.post(url, headers=headers, json=params)
    return response.json().get('token')

class WebSocketClient:
    def __init__(self, uri, access_token):
        self.uri = uri
        self.access_token = access_token
        self.websocket = None
        self.connected = False
        self.keep_running = True
        self.received_data = []

    async def connect(self):
        try:
            self.websocket = await websockets.connect(self.uri)
            self.connected = True
            # print("서버와 연결을 시도 중입니다.")

            # 로그인 패킷
            param = {
                'trnm': 'LOGIN',
                'token': self.access_token
            }

            # print('실시간 시세 서버로 로그인 패킷을 전송합니다.')
            await self.send_message(message=param)

        except Exception as e:
            # print(f'Connection error: {e}')
            self.connected = False
            self.received_data.append({"error": f"Connection error: {e}"})

    async def send_message(self, message):
        if not self.connected:
            await self.connect()  # 연결이 끊어졌다면 재연결
        if self.connected:
            if not isinstance(message, str):
                message = json.dumps(message)

            await self.websocket.send(message)
            # print(f'Message sent: {message}')

    async def receive_messages(self):
        try:
            while self.keep_running:
                response = json.loads(await self.websocket.recv())

                if response.get('trnm') == 'LOGIN':
                    if response.get('return_code') != 0:
                        # print('로그인 실패하였습니다. : ', response.get('return_msg'))
                        self.received_data.append({"error": "Login failed", "return_msg": response.get('return_msg')})
                        await self.disconnect()
                    else:
                        # print('로그인 성공하였습니다.')
                        # 상승률 30위 요청
                        param = {
                            'trnm': 'UPRATE30',  # 상승률 30위 요청
                            'top_n': '30'  # 상위 30위
                        }
                        await self.send_message(message=param)

                elif response.get('trnm') == 'UPRATE30':
                    self.received_data.append(response.get('data'))
                    # For this script, we only need one response, then disconnect
                    await self.disconnect()

                elif response.get('trnm') != 'PING':
                    # print(f'실시간 시세 서버 응답 수신: {response}')
                    pass # Do not print PING messages or other non-relevant messages

        except websockets.ConnectionClosed:
            # print('Connection closed by the server')
            self.connected = False
            self.received_data.append({"error": "Connection closed by the server"})
        except Exception as e:
            # print(f"Error receiving messages: {e}")
            self.received_data.append({"error": f"Error receiving messages: {e}"})

    async def run(self):
        await self.connect()
        await self.receive_messages()

    async def disconnect(self):
        self.keep_running = False
        if self.connected and self.websocket:
            await self.websocket.close()
            self.connected = False
            # print('Disconnected from WebSocket server')

async def main():
    access_token = get_access_token()
    if not access_token:
        print(json.dumps({"error": "Failed to get access token"}))
        return

    websocket_client = WebSocketClient(SOCKET_URL, access_token)
    await websocket_client.run()
    print(json.dumps(websocket_client.received_data, ensure_ascii=False, indent=4))

if __name__ == '__main__':
    asyncio.run(main())
