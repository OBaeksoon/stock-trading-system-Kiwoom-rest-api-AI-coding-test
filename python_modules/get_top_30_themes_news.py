
import configparser
import os
import logging
import mysql.connector
import requests
from datetime import datetime
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- 로그 설정 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- 기본 경로 설정 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, '..'))
CONFIG_FILE = os.path.join(PROJECT_ROOT, 'config.ini')

# --- 기본 테마 키워드 ---
BASIC_THEMES_KEYWORDS = {
    "AI & 반도체": ["AI", "인공지능", "반도체", "HBM", "메모리", "팹리스", "파운드리"],
    "2차전지 & 전기차": ["2차전지", "전기차", "배터리", "양극재", "음극재", "전고체"],
    "헬스케어 & 바이오": ["헬스케어", "바이오", "신약", "항암", "세포치료", "임상"],
    "친환경 & 원자력": ["친환경", "태양광", "풍력", "수소", "원자력", "SMR"],
    "우주 & 항공 & 방산": ["우주", "항공", "위성", "드론", "방산"],
    "조선 & 전력 인프라": ["조선", "해운", "전력", "전선", "케이블"],
    "가상자산 & 게임 & NFT": ["가상화폐", "블록체인", "NFT", "게임", "메타버스"],
    "로봇": ["로봇", "자동화", "물류로봇", "협동로봇"]
}

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

def get_top_30_stocks():
    """DB에서 실시간 상승률 30위 종목을 가져옵니다."""
    conn = get_db_connection()
    if conn is None:
        return []
    
    stock_list = []
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT stock_code, stock_name FROM top_30_rising_stocks ORDER BY rank LIMIT 30")
        results = cursor.fetchall()
        for row in results:
            stock_list.append({
                'stock_code': row['stock_code'],
                'stock_name': row['stock_name']
            })
        logger.info(f"DB에서 상승률 상위 {len(stock_list)}개 종목을 가져왔습니다.")
    except mysql.connector.Error as err:
        logger.error(f"DB에서 상승률 상위 종목 조회 중 오류 발생: {err}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
    return stock_list

def search_naver_news(query, client_id, client_secret, display=3):
    """네이버 뉴스 API를 사용하여 뉴스를 검색합니다."""
    naver_api_url = "https://openapi.naver.com/v1/search/news.json"
    headers = {"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}
    params = {"query": query, "display": display, "sort": "date"}
    try:
        response = requests.get(naver_api_url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"네이버 뉴스 API 호출 중 오류 발생 (쿼리: {query}): {e}")
        return None

def save_news_to_db(conn, stock_code, news_items):
    """검색된 뉴스 데이터를 데이터베이스에 저장하고 새로 삽입된 뉴스의 ID를 반환합니다."""
    cursor = conn.cursor()
    new_news_ids = []
    for item in news_items:
        title = item.get('title', '').replace('<b>', '').replace('</b>', '')
        link = item.get('link', '')
        description = item.get('description', '').replace('<b>', '').replace('</b>', '')
        try:
            pub_date_str = item.get('pubDate', '')
            pub_date = datetime.strptime(pub_date_str, '%a, %d %b %Y %H:%M:%S %z')
            pub_date_formatted = pub_date.strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            pub_date_formatted = None
        
        try:
            # ON DUPLICATE KEY UPDATE 대신 INSERT IGNORE 사용
            insert_query = "INSERT IGNORE INTO stock_news (stock_code, title, link, description, pub_date) VALUES (%s, %s, %s, %s, %s)"
            cursor.execute(insert_query, (stock_code, title, link, description, pub_date_formatted))
            if cursor.lastrowid:
                new_news_ids.append(cursor.lastrowid)
        except mysql.connector.Error as err:
            logger.error(f"뉴스 데이터 저장 중 오류 발생: {err}")
    
    conn.commit()
    cursor.close()
    logger.info(f"{stock_code} 관련 뉴스 {len(new_news_ids)}건 신규 저장 완료.")
    return new_news_ids

def classify_and_update_theme(conn, news_id):
    """단일 뉴스의 테마를 분류하고 DB에 업데이트합니다."""
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT title, description FROM stock_news WHERE id = %s", (news_id,))
        news_item = cursor.fetchone()
        if not news_item:
            return

        text_to_check = (news_item['title'] + ' ' + (news_item['description'] or '')).lower()
        best_theme = None
        max_score = 0
        
        for theme, keywords in BASIC_THEMES_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword.lower() in text_to_check)
            if score > max_score:
                max_score = score
                best_theme = theme
        
        if best_theme:
            cursor.execute("UPDATE stock_news SET theme = %s WHERE id = %s", (best_theme, news_id))
            conn.commit()
            logger.info(f"뉴스 ID {news_id}에 테마 '{best_theme}'를 할당했습니다.")

    except mysql.connector.Error as err:
        logger.error(f"뉴스 ID {news_id} 테마 분류/업데이트 중 오류: {err}")
    finally:
        cursor.close()

def process_stock(stock, client_id, client_secret):
    """단일 종목에 대한 뉴스 수집 및 테마 분류를 처리합니다."""
    conn = get_db_connection()
    if conn is None:
        return
    
    try:
        query = f"{stock['stock_name']}"
        logger.info(f"'{stock['stock_name']}' ({stock['stock_code']}) 관련 뉴스 검색 중...")
        news_data = search_naver_news(query, client_id, client_secret, display=5)
        
        if news_data and 'items' in news_data:
            new_ids = save_news_to_db(conn, stock['stock_code'], news_data['items'])
            for news_id in new_ids:
                classify_and_update_theme(conn, news_id)
        else:
            logger.info(f"'{stock['stock_name']}' 관련 뉴스를 찾지 못했습니다.")
    finally:
        if conn.is_connected():
            conn.close()

def main():
    """메인 실행 함수"""
    start_time = time.time()
    
    # DB 연결 및 API 키 가져오기
    conn = get_db_connection()
    if conn is None: return
    
    client_id, client_secret = get_naver_api_keys()
    if not all([client_id, client_secret]): return

    # 상위 30위 종목 가져오기
    top_stocks = get_top_30_stocks()
    conn.close() # 메인 연결은 여기서 닫음

    if not top_stocks:
        logger.warning("처리할 상위 종목이 없습니다.")
        return

    # 병렬 처리
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(process_stock, stock, client_id, client_secret) for stock in top_stocks]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                logger.error(f"종목 처리 중 오류 발생: {e}")

    end_time = time.time()
    logger.info(f"모든 작업 완료. 총 소요 시간: {end_time - start_time:.2f}초")

if __name__ == "__main__":
    # stock_news 테이블 구조 확인 및 생성
    db_conn = get_db_connection()
    if db_conn:
        cursor = db_conn.cursor()
        try:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS `stock_news` (
              `id` int NOT NULL AUTO_INCREMENT,
              `stock_code` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
              `title` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
              `link` varchar(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
              `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
              `pub_date` datetime DEFAULT NULL,
              `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
              `theme` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
              PRIMARY KEY (`id`),
              UNIQUE KEY `link` (`link`),
              KEY `stock_code` (`stock_code`),
              KEY `idx_theme` (`theme`),
              KEY `idx_pub_date` (`pub_date`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)
            logger.info("`stock_news` 테이블이 준비되었습니다.")
        except mysql.connector.Error as err:
            logger.error(f"테이블 생성 확인 중 오류: {err}")
        finally:
            cursor.close()
            db_conn.close()
    
    main()
