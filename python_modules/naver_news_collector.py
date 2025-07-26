import requests
import configparser
import os
import logging
import mysql.connector
from datetime import datetime
import time

# --- 로그 설정 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- 기본 경로 설정 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, '..')) # public_html
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

def get_stock_codes(conn):
    """데이터베이스에서 주식 코드와 종목명을 가져옵니다. (stock_details 테이블이 있다고 가정)"""
    cursor = conn.cursor()
    stock_list = []
    try:
        # 'stock_details' 테이블이 존재하고 'stock_code', 'stock_name' 컬럼이 있다고 가정
        cursor.execute("SELECT stock_code, stock_name FROM stock_details WHERE circulating_shares IS NOT NULL AND circulating_shares != '' AND circulating_shares != '0'")
        for (stock_code, stock_name) in cursor:
            stock_list.append({'code': stock_code, 'name': stock_name})
        logger.info(f"총 {len(stock_list)}개의 주식 종목을 가져왔습니다. (유통주식수 있는 종목만)")
    except mysql.connector.Error as err:
        logger.error(f"주식 종목을 가져오는 중 오류 발생: {err}. 'stocks' 테이블이 존재하는지 확인하세요.")
    finally:
        cursor.close()
    return stock_list

def search_naver_news(query, client_id, client_secret, display=3):
    """네이버 뉴스 API를 사용하여 뉴스를 검색합니다."""
    naver_api_url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret
    }
    params = {
        "query": query,
        "display": display,
        "sort": "date" # 날짜순 정렬
    }
    
    try:
        response = requests.get(naver_api_url, headers=headers, params=params)
        response.raise_for_status() # HTTP 오류 발생 시 예외 발생
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"네이버 뉴스 API 호출 중 오류 발생: {e}")
        return None

def save_news_to_db(conn, stock_code, news_items):
    """검색된 뉴스 데이터를 데이터베이스에 저장합니다."""
    cursor = conn.cursor()
    insert_count = 0
    for item in news_items:
        title = item.get('title', '').replace('<b>', '').replace('</b>', '')
        link = item.get('link', '')
        description = item.get('description', '').replace('<b>', '').replace('</b>', '')
        pub_date_str = item.get('pubDate', '')
        
        # 날짜 형식 변환 (RFC 822 -> YYYY-MM-DD HH:MM:SS)
        try:
            # 예: Sat, 26 Jul 2025 09:00:00 +0900
            pub_date = datetime.strptime(pub_date_str, '%a, %d %b %Y %H:%M:%S %z')
            pub_date_formatted = pub_date.strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            pub_date_formatted = None
            logger.warning(f"날짜 형식 오류: {pub_date_str}")

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
            insert_count += 1
        except mysql.connector.Error as err:
            # UNIQUE KEY 제약 조건 위반 시 무시 (이미 존재하는 뉴스)
            if err.errno == 1062: # Duplicate entry error
                logger.debug(f"이미 존재하는 뉴스: {link}")
            else:
                logger.error(f"뉴스 데이터 저장 중 오류 발생: {err}")
    
    conn.commit()
    cursor.close()
    logger.info(f"{stock_code} 관련 뉴스 {insert_count}건 저장 완료.")

def main():
    conn = None
    try:
        conn = get_db_connection()
        if conn is None:
            logger.error("데이터베이스 연결에 실패했습니다. 스크립트를 종료합니다.")
            return

        client_id, client_secret = get_naver_api_keys()
        if client_id is None or client_secret is None:
            logger.error("네이버 API 키를 가져오는 데 실패했습니다. 스크립트를 종료합니다.")
            return

        stock_list = get_stock_codes(conn)
        if not stock_list:
            logger.warning("가져올 주식 종목이 없습니다. 'stocks' 테이블에 데이터가 있는지 확인하세요.")
            return

        for stock in stock_list:
            query = f"{stock['name']} 주식 뉴스" # 종목명으로 검색
            logger.info(f"'{stock['name']}' ({stock['code']}) 관련 뉴스 검색 중...")
            news_data = search_naver_news(query, client_id, client_secret, display=3)
            
            if news_data and 'items' in news_data:
                save_news_to_db(conn, stock['code'], news_data['items'])
            else:
                logger.info(f"'{stock['name']}' ({stock['code']}) 관련 뉴스를 찾을 수 없거나 오류가 발생했습니다.")
            
            time.sleep(0.1) # API 호출 간 지연 (과도한 호출 방지)

    finally:
        if conn:
            conn.close()
            logger.info("데이터베이스 연결을 닫습니다.")

if __name__ == "__main__":
    main()
