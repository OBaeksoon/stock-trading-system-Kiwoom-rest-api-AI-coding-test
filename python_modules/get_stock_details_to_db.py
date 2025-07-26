import requests
import json
import configparser
import os
import datetime
import logging
import mysql.connector
import time # Added for time.sleep
from kiwoom_api import get_access_token, get_db_connection, logger, CONFIG_FILE, PROJECT_ROOT

# --- 키움증권 API 함수 (전종목 조회) ---
def fn_ka10099(token, mrkt_tp, cont_yn='N', next_key=''):
    """
    모의투자 환경에서 코스피 및 코스닥의 모든 종목 정보를 조회합니다. (TR: ka10099)
    :param token: 접근 토큰
    :param mrkt_tp: 시장구분 (0:코스피, 10:코스닥)
    :param cont_yn: 연속조회여부 (Y/N)
    :param next_key: 연속조회키
    :return: API 응답 JSON
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
        res_json = response.json()
        return res_json
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
    :param token: 접근 토큰
    :param stk_cd: 종목코드
    :return: API 응답 JSON
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
        res_json = response.json()
        return res_json
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
    :param token: 접근 토큰
    :param stk_cd: 종목코드
    :param strt_dt: 시작일자 (YYYYMMDD)
    :return: API 응답 JSON
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
        res_json = response.json()
        return res_json
    except requests.exceptions.RequestException as e:
        logger.error(f"일별거래상세요청 API 요청 중 오류 발생 (종목코드: {stk_cd}, 일자: {strt_dt}): {e}")
        return None
    except json.JSONDecodeError:
        logger.error(f"일별거래상세요청 응답 JSON 파싱 오류 (종목코드: {stk_cd}, 일자: {strt_dt}). 응답: {response.text}")
        return None

def get_all_stocks_with_details(token, market_type_code, market_name):
    """
    지정된 시장의 모든 종목을 조회하고 상세 정보를 포함하여 리스트로 반환합니다.
    """
    all_stocks_basic = []
    cont_yn = 'N'
    next_key = ''

    logger.info(f"{market_name} 종목 코드 및 이름 조회를 시작합니다.")

    while True:
        response_data = fn_ka10099(token, market_type_code, cont_yn, next_key)
        if response_data is None:
            logger.error(f"{market_name} 종목 코드 조회에 실패했습니다.")
            break

        stocks_list = response_data.get('output1')
        if stocks_list is None or not isinstance(stocks_list, list):
            stocks_list = response_data.get('list', [])
            if not isinstance(stocks_list, list):
                logger.warning(f"API 응답에 'output1' 또는 'list' 필드가 없거나 유효한 리스트가 아닙니다. 응답: {json.dumps(response_data, indent=4, ensure_ascii=False)}")
                break

        for s in stocks_list:
            stock_code = s.get('code') or s.get('stk_cd') or s.get('종목코드')
            stock_name = s.get('name') or s.get('stk_nm') or s.get('종목명')
            if stock_code and stock_name:
                all_stocks_basic.append({'stock_code': stock_code, 'stock_name': stock_name, 'market': market_name})
        
        cont_yn = response_data.get('cont_yn', 'N')
        next_key = response_data.get('next_key', '')

        if cont_yn == 'Y' and next_key:
            logger.info(f"{market_name} 연속 조회: 다음 키 {next_key}")
        else:
            break
    
    logger.info(f"{market_name} 종목 코드 {len(all_stocks_basic)}개 조회 완료. 상세 정보 수집 시작.")

    detailed_stocks = []
    today = datetime.date.today()
    previous_trading_day = today - datetime.timedelta(days=1) # 간단하게 전일로 설정, 실제로는 휴장일 고려 필요
    previous_trading_day_str = previous_trading_day.strftime('%Y%m%d')

    for stock_info in all_stocks_basic:
        stock_code = stock_info['stock_code']
        stock_name = stock_info['stock_name']
        market = stock_info['market']

        current_price = None
        circulating_shares = None
        closing_price = None # This will be the current day's closing price if available, or previous day's if fetched from ka10015
        previous_day_closing_price = None

        # 1. 주식기본정보요청 (ka10001)
        ka10001_data = fn_ka10001(token, stock_code)
        if ka10001_data and ka10001_data.get('return_code') == 0:
            output = ka10001_data.get('output') or ka10001_data # Some APIs return directly, some wrap in 'output'
            if isinstance(output, list) and len(output) > 0:
                output = output[0] # Take the first item if it's a list
            
            current_price = output.get('cur_prc')
            circulating_shares = output.get('dstr_stk')
            
            # Calculate previous day's closing price from current price and pred_pre if available
            pred_pre = output.get('pred_pre')
            if current_price and pred_pre:
                try:
                    current_price_val = float(current_price.replace('+', '').replace('-', ''))
                    pred_pre_val = float(pred_pre.replace('+', '').replace('-', ''))
                    if '+' in pred_pre:
                        previous_day_closing_price = current_price_val - pred_pre_val
                    elif '-' in pred_pre:
                        previous_day_closing_price = current_price_val + pred_pre_val
                    else: # No change
                        previous_day_closing_price = current_price_val
                except ValueError:
                    logger.warning(f"Failed to parse price/pred_pre for {stock_code}: cur_prc={current_price}, pred_pre={pred_pre}")
        time.sleep(0.5) # Add a delay after each ka10001 request

        # 2. 일별거래상세요청 (ka10015) - 전일 종가 확인
        ka10015_data = fn_ka10015(token, stock_code, previous_trading_day_str)
        if ka10015_data and ka10015_data.get('return_code') == 0:
            daly_trde_dtl = ka10015_data.get('daly_trde_dtl')
            if daly_trde_dtl and isinstance(daly_trde_dtl, list) and len(daly_trde_dtl) > 0:
                # Get the closing price for the requested previous day
                closing_price_from_prev_day = daly_trde_dtl[0].get('close_pric')
                if closing_price_from_prev_day:
                    previous_day_closing_price = closing_price_from_prev_day # Use this as the definitive previous day's close
        time.sleep(0.5) # Add a delay after each ka10015 request

        # For 'closing_price', we'll use the 'current_price' from ka10001 if it's the end of the day,
        # or if we need a 'last known price' for the current day.
        # If the request is for "종가" (closing price) for the *current* day, it's usually the `cur_prc` at market close.
        # For simplicity, we'll use `current_price` as `closing_price` for the current day's data.
        closing_price = current_price

        detailed_stocks.append({
            'stock_code': stock_code,
            'stock_name': stock_name,
            'market': market,
            'current_price': current_price,
            'closing_price': closing_price, # Current day's closing price (or last known price)
            'previous_day_closing_price': previous_day_closing_price,
            'circulating_shares': circulating_shares
        })
        logger.debug(f"Collected details for {stock_name} ({stock_code}): {detailed_stocks[-1]}")
    
    logger.info(f"총 {len(detailed_stocks)}개의 종목 상세 정보 수집 완료.")
    return detailed_stocks

def save_stock_details_to_db(stocks):
    """
    조회된 종목 상세 정보를 데이터베이스에 저장합니다.
    """
    conn = get_db_connection()
    if conn is None:
        logger.error("DB 연결 실패: 종목 상세 정보를 저장할 수 없습니다.")
        return

    try:
        cursor = conn.cursor()
        # 테이블 생성 (IF NOT EXISTS) - 스키마 변경
        create_table_query = """
        CREATE TABLE IF NOT EXISTS stock_details (
            stock_code VARCHAR(10) PRIMARY KEY,
            stock_name VARCHAR(100) NOT NULL,
            market VARCHAR(20) NOT NULL,
            current_price VARCHAR(20),
            closing_price VARCHAR(20),
            previous_day_closing_price VARCHAR(20),
            circulating_shares VARCHAR(20),
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
        """
        cursor.execute(create_table_query)
        conn.commit()
        logger.info("stock_details 테이블이 준비되었습니다.")

        # 데이터 삽입 또는 업데이트
        insert_query = """
        INSERT INTO stock_details (stock_code, stock_name, market, current_price, closing_price, previous_day_closing_price, circulating_shares)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            stock_name = VALUES(stock_name),
            market = VALUES(market),
            current_price = VALUES(current_price),
            closing_price = VALUES(closing_price),
            previous_day_closing_price = VALUES(previous_day_closing_price),
            circulating_shares = VALUES(circulating_shares),
            updated_at = CURRENT_TIMESTAMP
        """
        
        data_to_insert = []
        for s in stocks:
            data_to_insert.append((
                s.get('stock_code'),
                s.get('stock_name'),
                s.get('market'),
                s.get('current_price'),
                s.get('closing_price'),
                s.get('previous_day_closing_price'),
                s.get('circulating_shares')
            ))
        
        if data_to_insert:
            cursor.executemany(insert_query, data_to_insert)
            conn.commit()
            logger.info(f"{len(data_to_insert)}개의 종목 상세 정보가 DB에 저장/업데이트되었습니다.")
        else:
            logger.info("저장할 종목 상세 정보가 없습니다.")

    except mysql.connector.Error as err:
        logger.error(f"DB에 종목 상세 정보 저장 중 오류 발생: {err}")
        conn.rollback()
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    logger.info("코스피/코스닥 전종목 상세 정보 조회 및 DB 저장 스크립트를 시작합니다.")
    
    token = get_access_token()
    if token:
        kospi_detailed_stocks = get_all_stocks_with_details(token, '0', 'KOSPI')
        kosdaq_detailed_stocks = get_all_stocks_with_details(token, '10', 'KOSDAQ')

        all_combined_detailed_stocks = kospi_detailed_stocks + kosdaq_detailed_stocks
        logger.info(f"총 {len(all_combined_detailed_stocks)}개의 종목 상세 정보가 수집되었습니다.")

        if all_combined_detailed_stocks:
            save_stock_details_to_db(all_combined_detailed_stocks)
        else:
            logger.warning("수집된 종목 상세 정보가 없어 DB에 저장할 내용이 없습니다.")
    else:
        logger.error("접근 토큰을 얻지 못하여 전종목 상세 정보 조회를 시작할 수 없습니다.")
    
    logger.info("코스피/코스닥 전종목 상세 정보 조회 및 DB 저장 스크립트를 종료합니다.")
