import configparser
import requests
import json
import os
import time
import logging
import asyncio
import websockets
from datetime import datetime, timedelta

# 로거 설정
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

def get_api_config():
    """config.ini 파일에서 API 설정을 읽어옵니다."""
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini')
    if not os.path.exists(config_path):
        logger.error(f"설정 파일을 찾을 수 없습니다: {config_path}")
        raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {config_path}")
    
    config.read(config_path)

    try:
        app_key = config.get('API', 'APP_KEY')
        app_secret = config.get('API', 'APP_SECRET')
        base_url = config.get('API', 'BASE_URL')
    except configparser.NoOptionError as e:
        logger.error(f"설정 파일(config.ini)에서 필수 API 옵션을 찾을 수 없습니다: {e}")
        logger.error("config.ini 파일의 [API] 섹션에 'APP_KEY', 'APP_SECRET', 'BASE_URL'이 올바르게 설정되어 있는지 확인해주세요.")
        raise # 오류 발생 시 상위 함수로 예외를 다시 발생시켜 적절히 처리되도록 함
    except configparser.NoSectionError as e:
        logger.error(f"설정 파일(config.ini)에서 필수 [API] 섹션을 찾을 수 없습니다: {e}")
        logger.error("config.ini 파일에 '[API]' 섹션이 존재하는지 확인해주세요.")
        raise

    return app_key, app_secret, base_url

def _send_request(method, url, headers, params=None, json_data=None, max_retries=3, delay=2):
    """지정된 HTTP 요청을 재시도 로직과 함께 보냅니다."""
    for attempt in range(max_retries):
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=10)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, json=json_data, timeout=10)
            else:
                logger.error(f"지원하지 않는 HTTP 메소드: {method}")
                return None

            response.raise_for_status()
            
            res_data = response.json()
            rt_cd = res_data.get('rt_cd')
            if rt_cd is not None and rt_cd != '0':
                msg = res_data.get('msg1', '알 수 없는 API 오류')
                logger.warning(f"API 오류 수신 (rt_cd: {rt_cd}): {msg}. URL: {url}")
            
            return res_data

        except requests.exceptions.HTTPError as e:
            logger.warning(f"HTTP 오류 (시도 {attempt + 1}/{max_retries}): {e.response.status_code}. 응답: {e.response.text}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"요청 오류 (시도 {attempt + 1}/{max_retries}): {e}")
        
        if attempt < max_retries - 1:
            time.sleep(delay)
        else:
            logger.error("최대 재시도 횟수를 초과했습니다.")
            return None
    return None

def get_access_token():
    """API 접근 토큰을 발급받습니다."""
    try:
        app_key, app_secret, base_url = get_api_config()
    except (FileNotFoundError, configparser.Error): # configparser 오류도 여기서 함께 처리
        logger.error("설정 파일 문제로 토큰 발급을 시도할 수 없습니다.")
        return None
        
    url = f"{base_url}/oauth2/token"
    # 테스트를 통해 확인된 올바른 파라미터명('secretkey')과 헤더를 사용합니다.
    headers = {"content-type": "application/json;charset=UTF-8"}
    body = {"grant_type": "client_credentials", "appkey": app_key, "secretkey": app_secret}
    
    # 토큰 발급은 재시도 로직을 직접 사용 (body가 json 파라미터로 전달되어야 함)
    for attempt in range(3):
        try:
            response = requests.post(url, headers=headers, json=body, timeout=10)
            response.raise_for_status()
            res_data = response.json()
            # 테스트를 통해 확인된 올바른 응답 필드명('token')을 사용합니다.
            access_token = res_data.get('token')
            if access_token:
                logger.info("접근 토큰 발급 성공.")
                return access_token
            else:
                logger.error(f"토큰 발급 실패: 'token' 필드 없음. 응답: {res_data}")
                return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"토큰 발급 요청 오류 (시도 {attempt + 1}/3): {e}")
            time.sleep(2)
    
    logger.error("최대 재시도 후에도 토큰 발급에 실패했습니다.")
    return None

def get_daily_price(token, stock_code):
    """일봉 데이터를 조회합니다."""
    try:
        app_key, app_secret, base_url = get_api_config()
    except (FileNotFoundError, configparser.Error):
        return None

    endpoint = '/uapi/domestic-stock/v1/quotations/inquire-daily-price'
    url = base_url + endpoint
    headers = {
        'Content-Type': 'application/json;charset=UTF-8',
        'authorization': f'Bearer {token}',
        'appkey': app_key,
        'appsecret': app_secret,
        'tr_id': 'FHKST01010400'
    }
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
    params = {'FID_COND_MRKT_DIV_CODE': 'J', 'FID_INPUT_ISCD': stock_code, 'FID_INPUT_DATE_1': start_date, 'FID_INPUT_DATE_2': end_date, 'FID_PERIOD_DIV_CODE': 'D', 'FID_ORG_ADJ_PRC': '1'}
    
    return _send_request('GET', url, headers=headers, params=params)

def get_minute_price(token, stock_code):
    """분봉 데이터를 조회합니다."""
    try:
        app_key, app_secret, base_url = get_api_config()
    except (FileNotFoundError, configparser.Error):
        return None

    endpoint = '/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice'
    url = base_url + endpoint
    headers = {
        'Content-Type': 'application/json;charset=UTF-8',
        'authorization': f'Bearer {token}',
        'appkey': app_key,
        'appsecret': app_secret,
        'tr_id': 'FHKST03010200' # 분봉 데이터 TR_ID
    }
    # 조회 시간 (HHMMSS)
    query_time = datetime.now().strftime('%H%M%S')
    params = {'FID_ETC_CLS_CODE': '', 'FID_COND_MRKT_DIV_CODE': 'J', 'FID_INPUT_ISCD': stock_code, 'FID_INPUT_HOUR_1': query_time, 'FID_PW_DATA_INCU_YN': 'Y'}

    return _send_request('GET', url, headers=headers, params=params)

def get_account_profit_rate(token, account_number):
    """계좌수익률을 요청합니다."""
    try:
        app_key, app_secret, base_url = get_api_config()
    except (FileNotFoundError, configparser.Error):
        return None

    endpoint = '/uapi/domestic-stock/v1/trading/inquire-balance'
    url = base_url + endpoint
    headers = {
        'Content-Type': 'application/json;charset=UTF-8',
        'authorization': f'Bearer {token}',
        'appkey': app_key,
        'appsecret': app_secret,
        'tr_id': 'VTTC8434R' if 'vts' in base_url else 'TTTC8434R',
        'custtype': 'P'
    }
    params = {'CANO': account_number, 'ACNT_PRDT_CD': '01', 'AFHR_FLPR_YN': 'N', 'OFL_YN': 'N', 'INQR_DVSN': '01', 'UNPR_DVSN': '01', 'FUND_STTL_ICLD_YN': 'N', 'FNCG_AMT_AUTO_RDPT_YN': 'N', 'PRCS_DVSN': '00'}
    
    return _send_request('GET', url, headers=headers, params=params)

def place_order(token, account_number, stock_code, order_type, quantity, price=0, order_dvsn="02"):
    """주문을 요청합니다. (시장가 기본)"""
    try:
        app_key, app_secret, base_url = get_api_config()
    except (FileNotFoundError, configparser.Error):
        return None

    endpoint = '/uapi/domestic-stock/v1/trading/order-cash'
    url = base_url + endpoint
    
    tr_id = ""
    if order_type.lower() == "buy":
        tr_id = "VTTC0802U" if 'vts' in base_url else "TTTC0802U"
    elif order_type.lower() == "sell":
        tr_id = "VTTC0801U" if 'vts' in base_url else "TTTC0801U"
    else:
        logger.error(f"잘못된 주문 유형: {order_type}")
        return None

    headers = {
        'Content-Type': 'application/json;charset=UTF-8',
        'authorization': f'Bearer {token}',
        'appkey': app_key,
        'appsecret': app_secret,
        'tr_id': tr_id,
        'custtype': 'P',
    }
    data = {"CANO": account_number, "ACNT_PRDT_CD": "01", "PDNO": stock_code, "ORD_DVSN": order_dvsn, "ORD_QTY": str(quantity), "ORD_UNPR": str(price)}

    return _send_request('POST', url, headers=headers, json_data=data)

def get_current_price(token, stock_code):
    """현재가를 조회합니다."""
    try:
        app_key, app_secret, base_url = get_api_config()
    except (FileNotFoundError, configparser.Error):
        return None
        
    endpoint = '/uapi/domestic-stock/v1/quotations/inquire-price'
    url = base_url + endpoint
    headers = {
        'Content-Type': 'application/json;charset=UTF-8',
        'authorization': f'Bearer {token}',
        'appkey': app_key,
        'appsecret': app_secret,
        'tr_id': 'FHKST01010100'
    }
    params = {'FID_COND_MRKT_DIV_CODE': 'J', 'FID_INPUT_ISCD': stock_code}
    
    return _send_request('GET', url, headers=headers, params=params)

def get_order_book(token, stock_code):
    """호가창을 조회합니다."""
    try:
        app_key, app_secret, base_url = get_api_config()
    except (FileNotFoundError, configparser.Error):
        return None

    endpoint = '/uapi/domestic-stock/v1/quotations/inquire-asking-price-exp-ccn'
    url = base_url + endpoint
    headers = {
        'Content-Type': 'application/json;charset=UTF-8',
        'authorization': f'Bearer {token}',
        'appkey': app_key,
        'appsecret': app_secret,
        'tr_id': 'FHKST01010200'
    }
    params = {'FID_COND_MRKT_DIV_CODE': 'J', 'FID_INPUT_ISCD': stock_code}

    return _send_request('GET', url, headers=headers, params=params)

if __name__ == '__main__':
    logger.info("--- kiwoom_api.py 테스트 시작 ---")
    access_token = get_access_token()
    if access_token:
        daily_data = get_daily_price(access_token, "005930")
        if daily_data and daily_data.get('output1'):
            logger.info(f"삼성전자 일봉 데이터 (첫 5개): {daily_data['output1'][:5]}")
        else:
            logger.error("일봉 데이터 조회 실패.")
    else:
        logger.error("테스트 실패: 접근 토큰을 발급받을 수 없습니다.")