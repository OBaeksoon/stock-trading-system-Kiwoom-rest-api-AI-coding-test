import configparser
import os
import logging
import mysql.connector
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- 로그 설정 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- 기본 경로 설정 ---
# 이 스크립트 파일이 있는 디렉토리 기준
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__)) 
# public_html/ 디렉토리로 이동
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, '..')) 
CONFIG_FILE = os.path.join(PROJECT_ROOT, 'config.ini')

# --- [1단계 개선] 테마 및 키워드 정의 (가중치 적용) ---
# 핵심 키워드에는 높은 가중치를, 보조 키워드에는 낮은 가중치를 부여하여 정확도 향상
THEMES_KEYWORDS = {
    "AI & 반도체": {
        "AI": 3, "인공지능": 3, "HBM": 3, "고대역폭 메모리": 3, "뉴로모픽": 2, "온디바이스": 2, "CXL": 2, "NPU": 2,
        "반도체": 1, "팹리스": 1, "파운드리": 1, "SK하이닉스": 1, "삼성전자": 1, "한미반도체": 1, 
        "가온칩스": 1, "텔레칩스": 1, "네패스": 1, "리노공업": 1, "제주반도체": 1, "칩스앤미디어": 1, "오픈엣지테크놀로지": 1
    },
    "2차전지 & 전기차": {
        "2차전지": 3, "전고체": 3, "폐배터리": 2, "리튬": 2, "LFP": 2, "전기차": 1, "배터리": 1, 
        "양극재": 1, "음극재": 1, "충전": 1, "자율주행": 1, "LG에너지솔루션": 1, "삼성SDI": 1, 
        "에코프로비엠": 1, "포스코퓨처엠": 1, "엘앤에프": 1, "SKC": 1, "현대차": 1, "기아": 1
    },
    "헬스케어 & 바이오": {
        "비만 치료제": 3, "ADC": 3, "신약": 2, "세포 치료": 2, "유전자": 2, "임상": 2, "헬스케어": 1, 
        "바이오": 1, "항암": 1, "디지털 헬스케어": 1, "삼성바이오로직스": 1, "셀트리온": 1, 
        "SK바이오팜": 1, "유한양행": 1, "한미약품": 1, "루닛": 1, "뷰노": 1
    },
    "친환경 & 원자력": {
        "원자력": 3, "SMR": 3, "신재생": 2, "에너지": 1, "친환경": 1, "태양광": 1, "풍력": 1, "수소": 1, 
        "탄소중립": 1, "RE100": 1, "ESG": 1, "한화솔루션": 1, "OCI": 1, "씨에스윈드": 1, 
        "두산에너빌리티": 1, "SNT에너지": 1
    },
    "우주 & 항공 & 방산": {
        "방산": 3, "우주": 2, "항공": 2, "위성": 2, "발사체": 2, "UAM": 2, "드론": 1, "누리호": 1,
        "한화에어로스페이스": 1, "한국항공우주": 1, "KAI": 1, "쎄트렉아이": 1, "AP위성": 1, 
        "인텔리안테크": 1, "LIG넥스원": 1, "현대로템": 1
    },
    "조선 & 전력 인프라": {
        "전력": 3, "변압기": 3, "전선": 2, "케이블": 2, "조선": 1, "해운": 1, "스마트그리드": 1,
        "HD현대중공업": 1, "삼성중공업": 1, "한화오션": 1, "HD한국조선해양": 1, "HMM": 1,
        "LS마린솔루션": 1, "가온전선": 1
    },
    "가상자산 & 게임 & NFT": {
        "가상자산": 3, "비트코인": 3, "이더리움": 3, "블록체인": 2, "NFT": 1, "게임": 1, "메타버스": 1,
        "위메이드": 1, "컴투스": 1, "크래프톤": 1, "엔씨소프트": 1, "카카오게임즈": 1
    },
    "로봇": {
        "로봇": 3, "자동화": 2, "물류로봇": 2, "협동로봇": 2, "레인보우로보틱스": 1, 
        "두산로보틱스": 1, "에브리봇": 1, "유진로봇": 1, "티로보틱스": 1
    }
}

# --- [1단계 개선] 부정 키워드 정의 ---
# 아래 키워드가 포함된 뉴스는 매매 판단에서 제외하기 위해 "부정"으로 분류
NEGATIVE_KEYWORDS = [
    "급락", "하한가", "소송", "압수수색", "횡령", "배임", "화재", "리콜", 
    "영업정지", "실적 악화", "주가 조작", "혐의", "논란", "피소"
]


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
    """[1단계 개선] 가중치와 부정 키워드를 고려하여 단일 뉴스 아이템의 테마를 분류합니다."""
    news_id, title, description = news_item
    text_to_check = (title + ' ' + (description or '')).lower()

    # 1. 부정 키워드가 있는지 먼저 확인
    for neg_keyword in NEGATIVE_KEYWORDS:
        if neg_keyword.lower() in text_to_check:
            # 부정 키워드 발견 시, "부정" 테마로 즉시 분류하고 종료
            return news_id, "부정" 

    # 2. 가중치 기반으로 가장 관련성 높은 테마를 찾기
    best_theme = None
    max_score = 0
    
    for theme, keywords_with_weights in THEMES_KEYWORDS.items():
        score = 0
        for keyword, weight in keywords_with_weights.items():
            if keyword.lower() in text_to_check:
                score += weight  # 키워드의 가중치를 점수에 더함
        
        # 가장 높은 점수를 가진 테마를 best_theme으로 선정
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
        # 모든 뉴스를 대상으로 재분류
        cursor.execute("SELECT id, title, description FROM stock_news")
        news_to_classify = cursor.fetchall()
        cursor.close()

        if not news_to_classify:
            logger.info("분류할 뉴스가 없습니다.")
            return

        logger.info(f"총 {len(news_to_classify)}개의 뉴스를 전체 재분류합니다.")
        
        update_count = 0
        
        # ThreadPoolExecutor를 사용하여 병렬 처리
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_news = {executor.submit(classify_news_item, news): news for news in news_to_classify}
            
            # DB 커밋을 위한 단일 연결 사용
            db_conn_writer = get_db_connection()
            if db_conn_writer is None:
                logger.error("DB Writer 연결 실패.")
                return

            try:
                for future in as_completed(future_to_news):
                    news_id, theme = future.result()
                    
                    if update_theme_in_db(db_conn_writer, news_id, theme):
                        update_count += 1
                
                db_conn_writer.commit() # 모든 업데이트가 끝난 후 한 번에 커밋
                logger.info(f"총 {update_count}개의 뉴스 테마를 성공적으로 업데이트하고 커밋했습니다.")

            except Exception as e:
                db_conn_writer.rollback()
                logger.error(f"업데이트 중 오류가 발생하여 롤백합니다: {e}")
            finally:
                if db_conn_writer and db_conn_writer.is_connected():
                    db_conn_writer.close()

    except mysql.connector.Error as err:
        logger.error(f"스크립트 실행 중 DB 오류 발생: {err}")
    except Exception as e:
        logger.error(f"스크립트 실행 중 알 수 없는 오류 발생: {e}")
    finally:
        if conn and conn.is_connected():
            conn.close()
            logger.info("메인 데이터베이스 연결을 닫습니다.")

if __name__ == "__main__":
    main()