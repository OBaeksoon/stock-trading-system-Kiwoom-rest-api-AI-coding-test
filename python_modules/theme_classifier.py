import configparser
import os
import logging
import mysql.connector
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- 로그 설정 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- 기본 경로 설정 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, '..')) # public_html
CONFIG_FILE = os.path.join(PROJECT_ROOT, 'config.ini')

# --- 테마 및 키워드 정의 ---
THEMES_KEYWORDS = {
    "AI & 반도체": [
        "AI", "인공지능", "반도체", "HBM", "고대역폭 메모리", "뉴로모픽", "패키징", 
        "온디바이스", "팹리스", "파운드리", "SK하이닉스", "삼성전자", "한미반도체", 
        "가온칩스", "텔레칩스", "네패스", "리노공업", "제주반도체", "칩스앤미디어", "오픈엣지테크놀로지"
    ],
    "2차전지 & 전기차": [
        "2차전지", "전기차", "배터리", "양극재", "음극재", "전고체", "폐배터리", "리튬", 
        "충전", "자율주행", "LG에너지솔루션", "삼성SDI", "에코프로비엠", "포스코퓨처엠", 
        "엘앤에프", "SKC", "현대차", "기아", "현대모비스", "포스코DX"
    ],
    "헬스케어 & 바이오": [
        "헬스케어", "바이오", "신약", "비만 치료제", "ADC", "항암", "세포 치료", "유전자", 
        "오가노이드", "디지털 헬스케어", "임상", "삼성바이오로직스", "셀트리온", 
        "SK바이오팜", "유한양행", "한미약품", "루닛", "뷰노", "제이엘케이", "비트컴퓨터", "유비케어"
    ],
    "친환경 에너지": [
        "친환경", "태양광", "풍력", "수소", "신재생", "에너지", "탄소중립", "RE100", 
        "ESG", "스마트그리드", "ESS", "한화솔루션", "OCI", "씨에스윈드", "두산퓨얼셀", 
        "에스퓨얼셀", "KC코트렐", "대한전선", "신성이엔지", "유니슨"
    ],
    "우주산업": [
        "우주", "항공", "위성", "발사체", "뉴스페이스", "스타링크", "우주항공청", 
        "아르테미스", "누리호", "한화에어로스페이스", "한국항공우주", "KAI", 
        "쎄트렉아이", "AP위성", "인텔리안테크", "LIG넥스원", "현대로템", "대한항공"
    ]
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

def classify_news_item(news_item):
    """단일 뉴스 아이템의 테마를 분류합니다."""
    news_id, title, description = news_item
    text_to_check = (title + ' ' + (description or '')).lower()

    for theme, keywords in THEMES_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in text_to_check:
                return news_id, theme
    return news_id, None

def update_theme_in_db(conn, news_id, theme):
    """데이터베이스에 분류된 테마를 업데이트합니다."""
    try:
        cursor = conn.cursor()
        update_query = "UPDATE stock_news SET theme = %s WHERE id = %s"
        cursor.execute(update_query, (theme, news_id))
        cursor.close()
        return True
    except mysql.connector.Error as err:
        logger.error(f"ID {news_id} 테마 업데이트 중 오류 발생: {err}")
        return False

def main():
    """뉴스 테마를 분류하고 데이터베이스를 업데이트하는 메인 함수."""
    conn = None
    try:
        conn = get_db_connection()
        if conn is None:
            logger.error("데이터베이스 연결에 실패했습니다. 스크립트를 종료합니다.")
            return

        cursor = conn.cursor()
        # 'id' 컬럼이 있다고 가정하고, 없으면 'link' 같은 고유 키로 변경 필요
        # 'theme' 컬럼이 비어있거나 NULL인 뉴스만 선택
        cursor.execute("SELECT id, title, description FROM stock_news WHERE theme IS NULL OR theme = ''")
        news_to_classify = cursor.fetchall()
        cursor.close()

        if not news_to_classify:
            logger.info("새롭게 분류할 뉴스가 없습니다.")
            return

        logger.info(f"총 {len(news_to_classify)}개의 뉴스를 분류합니다.")
        
        update_count = 0
        
        # 여러 연결을 사용하여 병렬로 DB 업데이트
        with ThreadPoolExecutor(max_workers=10) as executor:
            # 각 뉴스 분류 작업 제출
            future_to_news = {executor.submit(classify_news_item, news): news for news in news_to_classify}
            
            # DB 연결 풀 모방
            db_connections = [get_db_connection() for _ in range(10)]
            
            conn_idx = 0
            for future in as_completed(future_to_news):
                news_id, theme = future.result()
                if theme:
                    db_conn = db_connections[conn_idx % len(db_connections)]
                    if update_theme_in_db(db_conn, news_id, theme):
                        update_count += 1
                    conn_idx += 1

            # 모든 연결에 대해 commit 및 close
            for db_conn in db_connections:
                if db_conn:
                    db_conn.commit()
                    db_conn.close()

        logger.info(f"총 {update_count}개의 뉴스에 테마를 성공적으로 업데이트했습니다.")

    except mysql.connector.Error as err:
        # 'id' 컬럼이 없는 경우 에러 처리
        if 'Unknown column \'id\'' in str(err):
            logger.error("오류: 'stock_news' 테이블에 'id' 컬럼이 없습니다. 'link' 등 고유한 값을 가진 다른 컬럼으로 스크립트를 수정해야 합니다.")
        else:
            logger.error(f"스크립트 실행 중 오류 발생: {err}")
    finally:
        if conn and conn.is_connected():
            conn.close()
            logger.info("메인 데이터베이스 연결을 닫습니다.")

if __name__ == "__main__":
    main()
