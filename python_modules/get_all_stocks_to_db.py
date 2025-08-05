import requests
import json
import configparser
import os
import datetime
import logging
import mysql.connector
import time
from kiwoom_api import get_access_token, get_db_connection, logger, CONFIG_FILE, PROJECT_ROOT

# --- 키움증권 API 함수 (전종목 조회) ---
def fn_ka10099(token, mrkt_tp, cont_yn='N', next_key=''):
    """
    모의투자 환경에서 코스피 및 코스닥의 모든 종목 정보를 조회합니다. (TR: ka10099)
    """
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    try:
        base_url = config.get('API', 'BASE_URL')
    except (configparser.NoSectionError, configparser.NoOptionError):
        logger.error(f"config.ini 파일에서 BASE_URL을 찾을 수 없습니다.")
        return None

    url = f"{base_url}/api/dostk/stkinfo"
    headers = {
        'Content-Type': 'application/json;charset=UTF-8',
        'authorization': f'Bearer {token}',
        'cont-yn': cont_yn,
        'next-key': next_key,
        'api-id': 'ka10099',
    }
    data = {
        'mrkt_tp': mrkt_tp,
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"전종목 조회 API 요청 중 오류 발생: {e}")
        return None
    except json.JSONDecodeError:
        logger.error(f"전종목 조회 응답 JSON 파싱 오류. 응답: {response.text}")
        return None

# --- 키움증권 API 함수 (주식기본정보요청) ---
def fn_ka10001(token, stk_cd):
    """
    단일 종목의 기본 정보를 조회합니다. (TR: ka10001)
    """
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    try:
        base_url = config.get('API', 'BASE_URL')
    except (configparser.NoSectionError, configparser.NoOptionError):
        logger.error(f"config.ini 파일에서 BASE_URL을 찾을 수 없습니다.")
        return None

    url = f"{base_url}/api/dostk/stkinfo"
    headers = {
        'Content-Type': 'application/json;charset=UTF-8',
        'authorization': f'Bearer {token}',
        'api-id': 'ka10001',
    }
    data = {
        'stk_cd': stk_cd,
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"주식기본정보요청 API 요청 중 오류 발생 (종목코드: {stk_cd}): {e}")
        return None
    except json.JSONDecodeError:
        logger.error(f"주식기본정보요청 응답 JSON 파싱 오류 (종목코드: {stk_cd}). 응답: {response.text}")
        return None

# --- 키움증권 API 함수 (일별거래상세요청) ---
def fn_ka10015(token, stk_cd, strt_dt):
    """
    단일 종목의 일별 거래 상세 정보를 조회합니다. (TR: ka10015)
    """
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    try:
        base_url = config.get('API', 'BASE_URL')
    except (configparser.NoSectionError, configparser.NoOptionError):
        logger.error(f"config.ini 파일에서 BASE_URL을 찾을 수 없습니다.")
        return None

    url = f"{base_url}/api/dostk/stkinfo"
    headers = {
        'Content-Type': 'application/json;charset=UTF-8',
        'authorization': f'Bearer {token}',
        'api-id': 'ka10015',
    }
    data = {
        'stk_cd': stk_cd,
        'strt_dt': strt_dt,
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"일별거래상세요청 API 요청 중 오류 발생 (종목코드: {stk_cd}, 일자: {strt_dt}): {e}")
        return None
    except json.JSONDecodeError:
        logger.error(f"일별거래상세요청 응답 JSON 파싱 오류 (종목코드: {stk_cd}, 일자: {strt_dt}). 응답: {response.text}")
        return None

def get_all_stocks(token, market_type_code, market_name):
    """
    지정된 시장의 모든 종목 코드를 조회하고 리스트로 반환합니다.
    """
    all_stocks = []
    cont_yn = 'N'
    next_key = ''
    logger.info(f"{market_name} 종목 정보 조회를 시작합니다.")

    while True:
        response_data = fn_ka10099(token, market_type_code, cont_yn, next_key)
        logger.debug(f"API Response for {market_name}: {response_data}")
        time.sleep(1) # API 호출 간 1초 대기
        if response_data is None:
            logger.error(f"{market_name} 종목 정보 조회에 실패했습니다.")
            break

        stocks = response_data.get('output1', [])
        if not isinstance(stocks, list):
            stocks = response_data.get('list', [])
            if not isinstance(stocks, list):
                logger.warning(f"API 응답에 'output1' 또는 'list' 필드가 없거나 유효한 리스트가 아닙니다. 응답: {response_data}")
                break

        for s in stocks:
            stock_code = s.get('code') or s.get('stk_cd')
            stock_name = s.get('name') or s.get('stk_nm')
            
            if stock_code and stock_name:  # 둘 다 존재할 때만 추가
                all_stocks.append({
                    'stock_code': stock_code,
                    'stock_name': stock_name,
                    'market': market_name
                })
            else:
                logger.warning(f"종목 정보 누락: code={s.get('code')}, stk_cd={s.get('stk_cd')}, name={s.get('name')}, stk_nm={s.get('stk_nm')}")

        cont_yn = response_data.get('cont_yn', 'N')
        next_key = response_data.get('next_key', '')

        if cont_yn != 'Y' or not next_key:
            break
    
    logger.info(f"{market_name} 종목 정보 {len(all_stocks)}개 조회 완료.")
    return all_stocks

def save_stocks_to_db(stocks):
    """
    조회된 종목 기본 정보를 all_stocks 테이블에 저장합니다.
    """
    conn = get_db_connection()
    if conn is None: return

    try:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS all_stocks (
            stock_code VARCHAR(10) PRIMARY KEY,
            stock_name VARCHAR(100) NOT NULL,
            market VARCHAR(20) NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
        """)
        
        insert_query = """
        INSERT INTO all_stocks (stock_code, stock_name, market)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
            stock_name = VALUES(stock_name),
            market = VALUES(market),
            updated_at = CURRENT_TIMESTAMP
        """
        data_to_insert = [
            (s['stock_code'], s['stock_name'], s['market']) 
            for s in stocks 
            if s.get('stock_code') and s.get('stock_name') and s.get('market')
        ]
        
        if data_to_insert:
            cursor.executemany(insert_query, data_to_insert)
            conn.commit()
            logger.info(f"{cursor.rowcount}개의 종목 정보가 all_stocks 테이블에 저장/업데이트되었습니다.")
    except mysql.connector.Error as err:
        logger.error(f"all_stocks 테이블 저장 중 오류: {err}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def save_stock_details_to_db(stocks_details):
    """
    조회된 종목 상세 정보를 stock_details 테이블에 저장합니다.
    """
    conn = get_db_connection()
    if conn is None: return

    try:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_details (
            stock_code VARCHAR(10) PRIMARY KEY,
            current_price VARCHAR(20),
            previous_day_closing_price VARCHAR(20),
            circulating_shares VARCHAR(20),
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
        """)
        
        insert_query = """
        INSERT INTO stock_details (stock_code, current_price, previous_day_closing_price, circulating_shares)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            current_price = VALUES(current_price),
            previous_day_closing_price = VALUES(previous_day_closing_price),
            circulating_shares = VALUES(circulating_shares),
            updated_at = CURRENT_TIMESTAMP
        """
        
        data_to_insert = [
            (s['stock_code'], s.get('current_price'), s.get('previous_day_closing_price'), s.get('circulating_shares'))
            for s in stocks_details
            if s.get('stock_code')  # stock_code가 있을 때만 추가
        ]
        
        if data_to_insert:
            cursor.executemany(insert_query, data_to_insert)
            conn.commit()
            logger.info(f"{cursor.rowcount}개의 종목 상세 정보가 stock_details 테이블에 저장/업데이트되었습니다.")
    except mysql.connector.Error as err:
        logger.error(f"stock_details 테이블 저장 중 오류: {err}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def get_and_save_details(token, all_stocks):
    """
    각 종목의 상세 정보를 조회하고 DB에 저장합니다.
    """
    detailed_stocks = []
    today = datetime.date.today()
    offset = 1 if today.weekday() < 5 else (today.weekday() - 4) # Fri, Sat, Sun -> prev is Thu
    if today.weekday() == 0: offset = 3 # Monday -> prev is Friday
    
    previous_trading_day_str = (today - datetime.timedelta(days=offset)).strftime('%Y%m%d')
    
    for i, stock_info in enumerate(all_stocks):
        stock_code = stock_info['stock_code']
        logger.info(f"({i+1}/{len(all_stocks)}) {stock_info['stock_name']}({stock_code}) 상세 정보 조회 중...")
        
        current_price = None
        circulating_shares = None
        previous_day_closing_price = None

        # 1. 주식기본정보요청 (ka10001)
        ka10001_data = fn_ka10001(token, stock_code)
        if ka10001_data and ka10001_data.get('return_code') == 0:
            output = ka10001_data.get('output', [{}])[0]
            current_price = output.get('cur_prc')
            circulating_shares = output.get('dstr_stk')
        time.sleep(1)

        # 2. 일별거래상세요청 (ka10015) - 전일 종가 확인
        ka10015_data = fn_ka10015(token, stock_code, previous_trading_day_str)
        if ka10015_data and ka10015_data.get('return_code') == 0:
            daily_detail = ka10015_data.get('daly_trde_dtl', [{}])[0]
            previous_day_closing_price = daily_detail.get('close_pric')
        time.sleep(1)

        detailed_stocks.append({
            'stock_code': stock_code,
            'current_price': current_price,
            'previous_day_closing_price': previous_day_closing_price,
            'circulating_shares': circulating_shares
        })

    if detailed_stocks:
        save_stock_details_to_db(detailed_stocks)
    else:
        logger.warning("수집된 종목 상세 정보가 없습니다.")

if __name__ == "__main__":
    # 잠금 파일 경로 설정
    LOCK_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'get_all_stocks.lock')

    # 잠금 파일이 이미 존재하면 스크립트가 실행 중인 것으로 간주하고 종료
    if os.path.exists(LOCK_FILE):
        logger.info(f"잠금 파일({LOCK_FILE})이 존재하여 스크립트를 시작하지 않습니다. 이미 다른 프로세스가 실행 중일 수 있습니다.")
        exit()

    try:
        # 잠금 파일 생성
        with open(LOCK_FILE, 'w') as f:
            f.write(str(os.getpid()))
        
        logger.info("코스피/코스닥 전종목 및 상세 정보 DB 저장 스크립트를 시작합니다.")
        
        token = get_access_token()
        if token:
            kospi_stocks = get_all_stocks(token, '0', 'KOSPI')
            time.sleep(1)
            kosdaq_stocks = get_all_stocks(token, '10', 'KOSDAQ')
            all_combined_stocks = kospi_stocks + kosdaq_stocks

            if all_combined_stocks:
                save_stocks_to_db(all_combined_stocks)
                get_and_save_details(token, all_combined_stocks)
            else:
                logger.warning("수집된 종목 정보가 없어 상세 정보 조회를 진행할 수 없습니다.")
        else:
            logger.error("접근 토큰을 얻지 못하여 전종목 조회를 시작할 수 없습니다.")
        
        logger.info("스크립트 실행이 완료되었습니다.")

    except Exception as e:
        logger.error(f"스크립트 실행 중 오류 발생: {e}", exc_info=True)
    finally:
        # 스크립트 종료 시 잠금 파일 삭제
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
        logger.info("스크립트를 종료합니다.")
