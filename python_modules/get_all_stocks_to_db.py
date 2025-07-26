import requests
import json
import configparser
import os
import datetime
import logging
import mysql.connector
import time # Added for time.sleep
from kiwoom_api import get_access_token, get_db_connection, logger, CONFIG_FILE, PROJECT_ROOT

# --- 로그 설정 (kiwoom_api와 동일한 로거 사용) ---
# logger는 kiwoom_api에서 이미 설정되어 있으므로 재설정 불필요

# --- 키움증권 API 함수 (전종목 조회) ---
def fn_ka10099(token, mrkt_tp, cont_yn='N', next_key=''):
    """
    모의투자 환경에서 코스피 및 코스닥의 모든 종목 정보를 조회합니다.
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

def get_all_stocks(token, market_type_code, market_name):
    """
    지정된 시장의 모든 종목을 조회하고 리스트로 반환합니다.
    연속 조회를 지원합니다.
    """
    all_stocks = []
    cont_yn = 'N'
    next_key = ''

    logger.info(f"{market_name} 종목 정보 조회를 시작합니다.")

    while True:
        response_data = fn_ka10099(token, market_type_code, cont_yn, next_key)
        time.sleep(0.5) # Add a delay after each fn_ka10099 request
        if response_data is None:
            logger.error(f"{market_name} 종목 정보 조회에 실패했습니다.")
            break

        # API 응답 전체를 로그 파일에 기록 (자세한 디버깅용)
        logger.debug(f"Raw API 응답 for {market_name} (Page cont-yn={cont_yn}, next-key={next_key}): {json.dumps(response_data, indent=4, ensure_ascii=False)}")

        # 'output1' 필드를 먼저 확인하고, 없으면 'list' 필드를 확인
        stocks = response_data.get('output1')
        if stocks is None or not isinstance(stocks, list):
            stocks = response_data.get('list', [])
            if not isinstance(stocks, list):
                logger.warning(f"API 응답에 'output1' 또는 'list' 필드가 없거나 유효한 리스트가 아닙니다. 응답: {json.dumps(response_data, indent=4, ensure_ascii=False)}")
                break # 유효한 데이터가 없으므로 루프 종료

        # stocks 리스트의 내용도 로깅하여 개별 종목 객체 구조 확인
        logger.debug(f"Processed stocks list for {market_name}: {json.dumps(stocks, indent=4, ensure_ascii=False)}")

        all_stocks.extend([
            {'stock_code': s.get('code') or s.get('stk_cd') or s.get('종목코드'), 'stock_name': s.get('name') or s.get('stk_nm') or s.get('종목명'), 'market': market_name}
            for s in stocks
        ])

        cont_yn = response_data.get('cont_yn', 'N')
        next_key = response_data.get('next_key', '')

        if cont_yn == 'Y' and next_key:
            logger.info(f"{market_name} 연속 조회: 다음 키 {next_key}")
        else:
            break
    
    logger.info(f"{market_name} 종목 정보 {len(all_stocks)}개 조회 완료.")
    return all_stocks

def save_stocks_to_db(stocks):
    """
    조회된 종목 정보를 데이터베이스에 저장합니다.
    """
    conn = get_db_connection()
    if conn is None:
        logger.error("DB 연결 실패: 종목 정보를 저장할 수 없습니다.")
        return

    try:
        cursor = conn.cursor()
        # 테이블 생성 (IF NOT EXISTS)
        create_table_query = """
        CREATE TABLE IF NOT EXISTS all_stocks (
            stock_code VARCHAR(10) PRIMARY KEY,
            stock_name VARCHAR(100) NOT NULL,
            market VARCHAR(20) NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
        """
        cursor.execute(create_table_query)
        conn.commit()
        logger.info("all_stocks 테이블이 준비되었습니다.")

        # 데이터 삽입 또는 업데이트
        insert_query = """
        INSERT INTO all_stocks (stock_code, stock_name, market)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
            stock_name = VALUES(stock_name),
            market = VALUES(market),
            updated_at = CURRENT_TIMESTAMP
        """
        
        data_to_insert = [(s['stock_code'], s['stock_name'], s['market']) for s in stocks]
        
        if data_to_insert:
            cursor.executemany(insert_query, data_to_insert)
            conn.commit()
            logger.info(f"{len(data_to_insert)}개의 종목 정보가 DB에 저장/업데이트되었습니다.")
        else:
            logger.info("저장할 종목 정보가 없습니다.")

    except mysql.connector.Error as err:
        logger.error(f"DB에 종목 정보 저장 중 오류 발생: {err}")
        conn.rollback()
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    logger.info("코스피/코스닥 전종목 조회 및 DB 저장 스크립트를 시작합니다.")
    
    token = get_access_token()
    if token:
        kospi_stocks = get_all_stocks(token, '0', 'KOSPI')
        kosdaq_stocks = get_all_stocks(token, '10', 'KOSDAQ')

        all_combined_stocks = kospi_stocks + kosdaq_stocks
        logger.info(f"총 {len(all_combined_stocks)}개의 종목 정보가 수집되었습니다.")

        if all_combined_stocks:
            save_stocks_to_db(all_combined_stocks)
        else:
            logger.warning("수집된 종목 정보가 없어 DB에 저장할 내용이 없습니다.")
    else:
        logger.error("접근 토큰을 얻지 못하여 전종목 조회를 시작할 수 없습니다.")
    
    logger.info("코스피/코스닥 전종목 조회 및 DB 저장 스크립트를 종료합니다.")
