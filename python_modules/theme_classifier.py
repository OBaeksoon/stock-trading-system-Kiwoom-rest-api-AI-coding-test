import configparser
import os
import logging
import mysql.connector
from concurrent.futures import ThreadPoolExecutor, as_completed
from kiwoom_api import KiwoomAPI, logger

# --- 기본 경로 설정 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, '..'))
CONFIG_FILE = os.path.join(PROJECT_ROOT, 'config.ini')

# --- 기본 테마 키워드 (API 보완용) ---
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

def fetch_all_themes_from_api(api):
    """키움증권 API에서 모든 테마와 관련 종목 정보를 가져옵니다."""
    if not api.token:
        logger.info("API 토큰이 없어 기본 테마 키워드만 사용합니다.")
        return BASIC_THEMES_KEYWORDS

    logger.info("키움증권 API에서 전체 테마 목록을 조회합니다.")
    themes_response = api.get_all_themes()
    if not themes_response or 'thema_grp' not in themes_response:
        logger.warning("API에서 테마 목록을 가져오지 못했습니다. 기본 키워드를 사용합니다.")
        return BASIC_THEMES_KEYWORDS

    themes = {}
    for theme_info in themes_response['thema_grp']:
        theme_name = theme_info.get('thema_nm')
        theme_code = theme_info.get('thema_grp_cd')
        if theme_name and theme_code:
            logger.info(f"테마 '{theme_name}'의 소속 종목을 조회합니다.")
            stocks_response = api.get_stocks_by_theme(theme_code)
            if stocks_response and 'thema_comp_stk' in stocks_response:
                stock_names = [s.get('stk_nm') for s in stocks_response['thema_comp_stk'] if s.get('stk_nm')]
                themes[theme_name] = stock_names
            else:
                logger.warning(f"'{theme_name}' 테마의 소속 종목을 가져오지 못했습니다.")
    
    logger.info(f"API에서 {len(themes)}개의 테마와 관련 종목 정보를 가져왔습니다.")
    return {**BASIC_THEMES_KEYWORDS, **themes}

def classify_news_item(news_item, themes_keywords):
    """단일 뉴스 아이템의 테마를 분류합니다."""
    news_id, title, description = news_item
    text_to_check = (title + ' ' + (description or '')).lower()

    best_theme = None
    max_score = 0
    
    for theme, keywords in themes_keywords.items():
        score = sum(1 for keyword in keywords if keyword.lower() in text_to_check)
        if score > max_score:
            max_score = score
            best_theme = theme
            
    return news_id, best_theme

def update_theme_in_db(conn, news_id, theme):
    """데이터베이스에 분류된 테마를 업데이트합니다."""
    try:
        cursor = conn.cursor()
        update_query = "UPDATE stock_news SET theme = %s WHERE id = %s"
        cursor.execute(update_query, (theme, news_id))
        conn.commit()
        cursor.close()
        return True
    except mysql.connector.Error as err:
        logger.error(f"ID {news_id} 테마 업데이트 중 오류 발생: {err}")
        return False

def main():
    """뉴스 테마를 분류하고 데이터베이스를 업데이트하는 메인 함수."""
    api = KiwoomAPI()
    themes_keywords = fetch_all_themes_from_api(api)
    
    conn = get_db_connection()
    if conn is None:
        logger.error("데이터베이스 연결에 실패했습니다. 스크립트를 종료합니다.")
        return

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, description FROM stock_news WHERE theme IS NULL")
        news_to_classify = cursor.fetchall()
        cursor.close()

        if not news_to_classify:
            logger.info("새로 분류할 뉴스가 없습니다.")
            return

        logger.info(f"총 {len(news_to_classify)}개의 뉴스를 {len(themes_keywords)}개 테마로 분류합니다.")
        
        update_count = 0
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_news = {executor.submit(classify_news_item, news, themes_keywords): news for news in news_to_classify}
            
            for future in as_completed(future_to_news):
                news_id, theme = future.result()
                if theme:
                    # DB 작업을 위한 새 연결 생성
                    thread_conn = get_db_connection()
                    if thread_conn:
                        if update_theme_in_db(thread_conn, news_id, theme):
                            update_count += 1
                        thread_conn.close()

        logger.info(f"총 {update_count}개의 뉴스에 테마를 성공적으로 업데이트했습니다.")

    except mysql.connector.Error as err:
        logger.error(f"스크립트 실행 중 DB 오류 발생: {err}")
    finally:
        if conn.is_connected():
            conn.close()
            logger.info("메인 데이터베이스 연결을 닫습니다.")

if __name__ == "__main__":
    main()