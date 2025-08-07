import configparser
import os
import datetime
import logging
import mysql.connector
import time
import json
from kiwoom_api import KiwoomAPI, logger

# --- 기본 경로 및 설정 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, '..'))
CONFIG_FILE = os.path.join(PROJECT_ROOT, 'config.ini')

def get_db_connection():
    """config.ini에서 DB 정보를 읽어와 연결을 생성합니다."""
    config = configparser.ConfigParser()
    if not os.path.exists(CONFIG_FILE):
        logger.error(f"설정 파일을 찾을 수 없습니다: {CONFIG_FILE}")
        return None
    
    config.read(CONFIG_FILE)
    
    try:
        db_config = {
            'host': config.get('DB', 'HOST'),
            'user': config.get('DB', 'USER'),
            'password': config.get('DB', 'PASSWORD'),
            'database': config.get('DB', 'DATABASE'),
            'port': config.getint('DB', 'PORT')
        }
        return mysql.connector.connect(**db_config)
    except (configparser.NoSectionError, configparser.NoOptionError) as e:
        logger.error(f"config.ini 파일에 [DB] 섹션 또는 필요한 키가 없습니다. ({e})")
        return None
    except mysql.connector.Error as err:
        logger.error(f"데이터베이스 연결 오류: {err}")
        return None

def get_all_stocks_with_details(api, market_type_code, market_name):
    """
    지정된 시장의 모든 종목을 조회하고 상세 정보를 포함하여 리스트로 반환합니다.
    """
    all_stocks_basic = []
    cont_yn = 'N'
    next_key = ''

    logger.info(f"{market_name} 종목 코드 및 이름 조회를 시작합니다.")

    while True:
        response_data = api.get_all_stock_codes(market_type_code, cont_yn, next_key)
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
            time.sleep(1)
        else:
            break
    
    logger.info(f"{market_name} 종목 코드 {len(all_stocks_basic)}개 조회 완료. 상세 정보 수집 시작.")

    detailed_stocks = []
    today = datetime.date.today()
    previous_trading_day = today - datetime.timedelta(days=1)
    previous_trading_day_str = previous_trading_day.strftime('%Y%m%d')

    for stock_info in all_stocks_basic:
        stock_code = stock_info['stock_code']
        stock_name = stock_info['stock_name']
        market = stock_info['market']

        current_price = None
        circulating_shares = None
        closing_price = None
        previous_day_closing_price = None

        ka10001_data = api.get_stock_basic_info(stock_code)
        if ka10001_data:
            output = ka10001_data.get('output') or ka10001_data
            if isinstance(output, list) and len(output) > 0:
                output = output[0]
            
            current_price = output.get('cur_prc')
            circulating_shares = output.get('dstr_stk')
            
            pred_pre = output.get('pred_pre')
            if current_price and pred_pre:
                try:
                    current_price_val = float(current_price.replace('+', '').replace('-', ''))
                    pred_pre_val = float(pred_pre.replace('+', '').replace('-', ''))
                    if '+' in pred_pre:
                        previous_day_closing_price = current_price_val - pred_pre_val
                    elif '-' in pred_pre:
                        previous_day_closing_price = current_price_val + pred_pre_val
                    else:
                        previous_day_closing_price = current_price_val
                except (ValueError, TypeError):
                    logger.warning(f"Failed to parse price/pred_pre for {stock_code}: cur_prc={current_price}, pred_pre={pred_pre}")
        time.sleep(0.5)

        ka10015_data = api.get_stock_daily_history(stock_code, previous_trading_day_str)
        if ka10015_data:
            daly_trde_dtl = ka10015_data.get('daly_trde_dtl')
            if daly_trde_dtl and isinstance(daly_trde_dtl, list) and len(daly_trde_dtl) > 0:
                closing_price_from_prev_day = daly_trde_dtl[0].get('close_pric')
                if closing_price_from_prev_day:
                    previous_day_closing_price = closing_price_from_prev_day
        time.sleep(0.2)

        closing_price = current_price

        detailed_stocks.append({
            'stock_code': stock_code,
            'stock_name': stock_name,
            'market': market,
            'current_price': current_price,
            'closing_price': closing_price,
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
        
        data_to_insert = [
            (
                s.get('stock_code'), s.get('stock_name'), s.get('market'),
                s.get('current_price'), s.get('closing_price'),
                s.get('previous_day_closing_price'), s.get('circulating_shares')
            ) for s in stocks
        ]
        
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
    
    api = KiwoomAPI()
    if api.token:
        kospi_detailed_stocks = get_all_stocks_with_details(api, '0', 'KOSPI')
        kosdaq_detailed_stocks = get_all_stocks_with_details(api, '10', 'KOSDAQ')

        all_combined_detailed_stocks = kospi_detailed_stocks + kosdaq_detailed_stocks
        logger.info(f"총 {len(all_combined_detailed_stocks)}개의 종목 상세 정보가 수집되었습니다.")

        if all_combined_detailed_stocks:
            save_stock_details_to_db(all_combined_detailed_stocks)
        else:
            logger.warning("수집된 종목 상세 정보가 없어 DB에 저장할 내용이 없습니다.")
    else:
        logger.error("접근 토큰을 얻지 못하여 전종목 상세 정보 조회를 시작할 수 없습니다.")
    
    logger.info("코스피/코스닥 전종목 상세 정보 조회 및 DB 저장 스크립트를 종료합니다.")