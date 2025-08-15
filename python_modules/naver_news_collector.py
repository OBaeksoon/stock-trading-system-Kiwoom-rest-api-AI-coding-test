import requests
import configparser
import os
import logging
import mysql.connector
from datetime import datetime
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- 로컬 모듈 임포트 ---
from utils.db_utils import get_db_connection
# get_top_30_rising_stocks.py에서 직접 함수를 가져오도록 변경
from get_top_30_rising_stocks import get_top_30_rising_stocks, get_access_token

# --- 로그 설정 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- 기본 경로 설정 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, '..'))
CONFIG_FILE = os.path.join(PROJECT_ROOT, 'config.ini')

def get_naver_api_keys():
    """config.ini에서 네이버 API 키를 읽어옵니다."""
    config = configparser.ConfigParser()
    if not os.path.exists(CONFIG_FILE):
        logger.error(f"설정 파일을 찾을 수 없습니다: {CONFIG_FILE}")
        return None, None
    
    config.read(CONFIG_FILE)
    
    try:
        client_id = config.get('NAVER_API', 'CLIENT_ID')
        client_secret = config.get('NAVER_API', 'CLIENT_SECRET')
        return client_id, client_secret
    except (configparser.NoSectionError, configparser.NoOptionError) as e:
        logger.error(f"config.ini 파일에 [NAVER_API] 섹션 또는 필요한 키가 없습니다. ({e})")
        return None, None

def get_all_stock_codes(conn):
    """데이터베이스에서 모든 주식 코드와 종목명을 가져옵니다."""
    cursor = conn.cursor(dictionary=True)
    stock_list = []
    try:
        cursor.execute("SELECT stock_code, stock_name FROM stock_details")
        stock_list = cursor.fetchall()
        logger.info(f"총 {len(stock_list)}개의 전체 주식 종목을 가져왔습니다.")
    except mysql.connector.Error as err:
        logger.error(f"전체 주식 종목을 가져오는 중 오류 발생: {err}")
    finally:
        cursor.close()
    return stock_list

def search_naver_news(query, client_id, client_secret, display=5):
    """네이버 뉴스 API를 사용하여 뉴스를 검색합니다."""
    naver_api_url = "https://openapi.naver.com/v1/search/news.json"
    headers = {"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}
    params = {"query": query, "display": display, "sort": "date"}
    try:
        response = requests.get(naver_api_url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"네이버 뉴스 API 호출 중 오류 발생 (쿼리: {query}): {e}")
        return None

def save_news_to_db(conn, stock_code, news_items):
    """검색된 뉴스 데이터를 데이터베이스에 저장합니다."""
    cursor = conn.cursor()
    insert_count = 0
    for item in news_items:
        title = item.get('title', '').replace('<b>', '').replace('</b>', '')
        link = item.get('link', '')
        description = item.get('description', '').replace('<b>', '').replace('</b>', '')
        
        try:
            pub_date_str = item.get('pubDate', '')
            pub_date = datetime.strptime(pub_date_str, '%a, %d %b %Y %H:%M:%S %z')
            pub_date_formatted = pub_date.strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            pub_date_formatted = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        try:
            insert_query = """
                INSERT INTO stock_news (stock_code, title, link, description, pub_date)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    title = VALUES(title),
                    description = VALUES(description),
                    pub_date = VALUES(pub_date);
            """
            cursor.execute(insert_query, (stock_code, title, link, description, pub_date_formatted))
            if cursor.rowcount > 0:
                insert_count += 1
        except mysql.connector.Error as err:
            if err.errno != 1062: # 1062: Duplicate entry
                logger.error(f"뉴스 데이터 저장 중 오류 발생: {err}")
    
    if insert_count > 0:
        conn.commit()
        logger.info(f"'{stock_code}' 관련 뉴스 {insert_count}건 저장 완료.")
    cursor.close()

def fetch_and_save_news_for_stock(stock, client_id, client_secret):
    """단일 종목에 대한 뉴스 수집 및 저장을 처리합니다."""
    time.sleep(0.1) # API 속도 제한 방지
    conn = get_db_connection()
    if conn is None: return

    try:
        stock_code = stock.get('stock_code')
        stock_name = stock.get('stock_name')
        if not stock_code or not stock_name: return

        query = f'"{stock_name}"' # 정확한 종목명으로 검색
        logger.info(f"'{stock_name}' ({stock_code}) 관련 뉴스 검색 중...")
        news_data = search_naver_news(query, client_id, client_secret)
        
        if news_data and 'items' in news_data and news_data['items']:
            save_news_to_db(conn, stock_code, news_data['items'])
        else:
            logger.info(f"'{stock_name}' 관련 신규 뉴스를 찾지 못했습니다.")
    finally:
        if conn.is_connected():
            conn.close()

def collect_news(target_stocks='top30'):
    """
    지정된 대상의 주식 뉴스를 수집합니다.
    :param target_stocks: 'top30' (상승률 상위 30) 또는 'all' (전체 종목)
    """
    start_time = time.time()
    
    client_id, client_secret = get_naver_api_keys()
    if not all([client_id, client_secret]):
        logger.error("네이버 API 키를 가져오지 못했습니다.")
        return

    stock_list = []
    if target_stocks == 'top30':
        logger.info("실시간 상승률 상위 30위 종목의 뉴스 수집을 시작합니다.")
        access_token = get_access_token()
        if not access_token:
            logger.error("접근 토큰을 가져오지 못했습니다. 상승률 상위 종목 조회를 건너뜁니다.")
            return
        # 직접 함수 호출로 변경
        top_stocks_data = get_top_30_rising_stocks(access_token)
        if top_stocks_data:
            stock_list = [{'stock_code': s['stk_cd'], 'stock_name': s['stk_nm']} for s in top_stocks_data]
    elif target_stocks == 'all':
        logger.info("전체 종목의 뉴스 수집을 시작합니다.")
        conn = get_db_connection()
        if conn:
            stock_list = get_all_stock_codes(conn)
            conn.close()
    else:
        logger.error(f"잘못된 대상입니다: {target_stocks}. 'top30' 또는 'all'을 사용하세요.")
        return

    if not stock_list:
        logger.warning("뉴스 수집 대상 종목이 없습니다.")
        return

    logger.info(f"총 {len(stock_list)}개 종목에 대한 뉴스 수집을 진행합니다.")
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_and_save_news_for_stock, stock, client_id, client_secret) for stock in stock_list]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                logger.error(f"종목 뉴스 처리 중 오류 발생: {e}", exc_info=True)

    logger.info(f"뉴스 수집 완료. 총 소요 시간: {time.time() - start_time:.2f}초")

if __name__ == "__main__":
    import sys
    # 실행 시 인자로 'top30' 또는 'all'을 받아 처리
    target = 'top30'
    if len(sys.argv) > 1 and sys.argv[1] in ['top30', 'all']:
        target = sys.argv[1]
    
    collect_news(target)