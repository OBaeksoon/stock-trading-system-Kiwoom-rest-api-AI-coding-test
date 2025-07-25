import requests
import json
import asyncio
import websockets
import configparser
import os

# Load API keys from config.ini
config = configparser.ConfigParser()
config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config.ini')
config.read(config_path)

APP_KEY = config['API']['APP_KEY']
APP_SECRET = config['API']['APP_SECRET']
BASE_URL = config['API']['BASE_URL']

# 접근토큰 발급
def fn_au10001(data):
    host = BASE_URL  # 모의투자
    endpoint = '/oauth2/token'
    url = host + endpoint

    headers = {
        'Content-Type': 'application/json;charset=UTF-8',
    }

    response = requests.post(url, headers=headers, json=data)
    return response.json()

# 조건검색식 목록 조회
async def fetch_condition_list(access_token):
    # 모의투자 WebSocket URL (하드코딩된 주소 사용)
    SOCKET_URL = 'wss://mockapi.kiwoom.com:10000/api/dostk/websocket'

    try:
        async with websockets.connect(SOCKET_URL) as websocket:
            # 1. 로그인 요청
            login_param = {
                'trnm': 'LOGIN',
                'token': access_token
            }
            await websocket.send(json.dumps(login_param))
            
            # 2. 로그인 성공 응답 대기
            login_success = False
            while True:
                response_str = await websocket.recv()
                response = json.loads(response_str)
                
                if response.get('trnm') == 'LOGIN':
                    if response.get('return_code') == 0:
                        login_success = True
                    else:
                        # 로그인 실패 시 에러 출력 후 종료
                        error_msg = {"error": "Login failed", "response": response}
                        print(json.dumps(error_msg))
                    break # 로그인 응답을 받았으므로 루프 탈출
            
            # 3. 로그인이 성공했을 경우에만 다음 요청 전송
            if login_success:
                list_param = {
                    'trnm': 'CNSRLST'
                }
                await websocket.send(json.dumps(list_param))

                # 4. 조건검색 목록 응답 대기
                while True:
                    response_str = await websocket.recv()
                    response = json.loads(response_str)
                    if response.get('trnm') == 'CNSRLST':
                        # PHP가 파싱할 수 있도록 데이터만 JSON으로 출력
                        print(json.dumps(response.get('data')))
                        break # 원하는 응답을 받았으므로 루프 탈출
    except websockets.exceptions.ConnectionClosed as e:
        error_msg = {"error": "WebSocket connection closed", "details": str(e)}
        print(json.dumps(error_msg))
    except Exception as e:
        error_msg = {"error": "An unexpected error occurred", "details": str(e)}
        print(json.dumps(error_msg))

if __name__ == '__main__':
    # 접근 데이터
    params = {
        'grant_type': 'client_credentials',
        'appkey': APP_KEY,
        'secretkey': APP_SECRET,
    }

    access_token = None
    try:
        # 접근 토큰 발급
        token_response = fn_au10001(data=params)
        access_token = token_response.get('access_token') # 'token'이 아니라 'access_token'
    except requests.exceptions.RequestException as e:
        print(json.dumps({"error": "Failed to get access token", "details": str(e)}))
    
    # 조건검색식 목록 조회
    if access_token:
        asyncio.run(fetch_condition_list(access_token))
    else:
        # token_response가 없을 경우를 대비
        if 'token_response' not in locals():
            token_response = "No response from token endpoint."
        print(json.dumps({"error": "Access token is missing", "response": token_response}))
