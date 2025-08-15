import os
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup

# --- 로컬 모듈 임포트 ---
from utils.db_utils import get_db_connection
from kiwoom_api import KiwoomAPI

# --- 로그 설정 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- 키워드 정의 ---
# 1. 기본 키워드 (API 조회 실패 시 사용될 최소한의 키워드)
DEFAULT_THEMES_KEYWORDS = {
    "AI & 반도체": {"AI": 3, "인공지능": 3, "HBM": 3, "반도체": 1},
    "2차전지 & 전기차": {"2차전지": 3, "전고체": 3, "전기차": 1, "배터리": 1},
    "헬스케어 & 바이오": {"비만 치료제": 3, "ADC": 3, "신약": 2, "바이오": 1},
    # ... 기타 기본 테마 ...
}

# 2. 부정 키워드 (이 키워드가 포함된 뉴스는 매매 판단에서 제외)
NEGATIVE_KEYWORDS = [
    "급락", "하한가", "소송", "압수수색", "횡령", "배임", "화재", "리콜", 
    "영업정지", "실적 악화", "주가 조작", "혐의", "논란", "피소", "손실"
]

class ThemeEngine:
    def __init__(self):
        self.api = KiwoomAPI()
        self.themes_keywords = self._initialize_keywords()

    def _get_themes_from_judal(self):
        """주달 웹사이트에서 테마 정보를 스크래핑합니다."""
        url = "https://www.judal.co.kr/"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        themes_data = {}
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # 주달 웹사이트의 테마 섹션 찾기 (예시: 실제 HTML 구조에 따라 변경 필요)
            # 웹페이지 내용을 기반으로 추측: '테마 보기' 또는 '테마별 종목'과 관련된 링크나 섹션
            # 예를 들어, <div class="theme_list"> 또는 <ul class="theme_category">
            
            # 임시로, 'a' 태그 중 'href' 속성에 'theme'이 포함된 것을 찾습니다.
            theme_links = soup.find_all('a', href=lambda href: href and 'theme' in href)
            for link in theme_links:
                theme_name = link.get_text(strip=True)
                if theme_name and len(theme_name) > 1: # 너무 짧은 텍스트는 제외
                    # 테마명만 추출하고, 종목은 나중에 추가하거나,
                    # 테마 상세 페이지로 이동하여 종목을 추출해야 할 수 있습니다.
                    themes_data[theme_name] = {theme_name: 3} # 테마명 자체를 키워드로 높은 가중치 부여
                    logger.info(f"스크래핑된 테마: {theme_name}")
            
            if not themes_data:
                logger.warning("주달에서 테마 섹션을 찾을 수 없습니다. 다른 셀렉터를 시도하거나 수동 확인이 필요합니다.")

        except requests.exceptions.RequestException as e:
            logger.error(f"주달 웹 스크래핑 중 오류 발생: {e}")
        except Exception as e:
            logger.error(f"주달 HTML 파싱 중 오류 발생: {e}")
        
        return themes_data if themes_data else DEFAULT_THEMES_KEYWORDS

    def _initialize_keywords(self):
        """API 또는 웹 스크래핑을 통해 최신 테마와 종목명을 가져와 키워드를 구성합니다."""
        logger.info("주달 웹 스크래핑을 통해 테마 목록을 조회합니다.")
        judal_themes = self._get_themes_from_judal()
        if judal_themes and judal_themes != DEFAULT_THEMES_KEYWORDS:
            logger.info(f"주달에서 {len(judal_themes)}개의 테마와 관련 키워드를 구성했습니다.")
            return judal_themes
        else:
            logger.warning("주달에서 테마 목록을 가져오지 못했습니다. 기본 테마 키워드만 사용합니다.")
            return DEFAULT_THEMES_KEYWORDS

    def classify_news_item(self, news_item):
        """가중치와 부정 키워드를 고려하여 단일 뉴스 아이템의 테마를 분류합니다."""
        news_id, title, description = news_item
        text_to_check = (title + ' ' + (description or '')).lower()

        # 1. 부정 키워드 필터링
        for neg_keyword in NEGATIVE_KEYWORDS:
            if neg_keyword.lower() in text_to_check:
                return news_id, "부정" 

        # 2. 가중치 기반 테마 분류
        best_theme = None
        max_score = 0
        for theme, keywords_with_weights in self.themes_keywords.items():
            score = 0
            for keyword, weight in keywords_with_weights.items():
                if keyword.lower() in text_to_check:
                    score += weight
            
            if score > max_score:
                max_score = score
                best_theme = theme
        
        # 점수가 0보다 클 때만 테마 할당
        return news_id, best_theme if max_score > 0 else None

    def update_themes_in_db(self, news_to_classify):
        """분류된 테마를 데이터베이스에 업데이트합니다."""
        if not news_to_classify:
            logger.info("분류할 뉴스가 없습니다.")
            return

        logger.info(f"총 {len(news_to_classify)}개의 뉴스를 재분류하고 업데이트합니다.")
        
        update_count = 0
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            # 각 뉴스 아이템에 대한 분류 작업을 제출
            future_to_news = {executor.submit(self.classify_news_item, news): news for news in news_to_classify}
            
            conn = get_db_connection()
            if not conn:
                logger.error("DB 연결 실패로 업데이트를 중단합니다.")
                return
            
            try:
                cursor = conn.cursor()
                for future in as_completed(future_to_news):
                    news_id, theme = future.result()
                    
                    if theme: # 분류된 테마가 있을 경우에만 업데이트
                        update_query = "UPDATE stock_news SET theme = %s WHERE id = %s"
                        cursor.execute(update_query, (theme, news_id))
                        update_count += 1
                
                if update_count > 0: 
                    conn.commit()
                    logger.info(f"총 {update_count}개의 뉴스 테마를 성공적으로 업데이트했습니다.")
                else:
                    logger.info("업데이트할 뉴스가 없습니다.")

            except Exception as e:
                conn.rollback()
                logger.error(f"테마 업데이트 중 오류가 발생하여 롤백합니다: {e}", exc_info=True)
            finally:
                cursor.close()
                conn.close()

def run_theme_classification(target='unclassified'):
    """
    뉴스 테마 분류를 실행합니다.
    :param target: 'unclassified' (테마가 없는 뉴스만) 또는 'all' (전체 뉴스 재분류)
    """
    conn = get_db_connection()
    if not conn:
        logger.error("데이터베이스 연결 실패.")
        return

    try:
        cursor = conn.cursor()
        if target == 'all':
            logger.info("모든 뉴스의 테마를 재분류합니다.")
            cursor.execute("SELECT id, title, description FROM stock_news")
        else:
            logger.info("테마가 없는 뉴스를 분류합니다.")
            cursor.execute("SELECT id, title, description FROM stock_news WHERE theme IS NULL")
        
        news_to_classify = cursor.fetchall()
    finally:
        conn.close()

    if news_to_classify:
        engine = ThemeEngine()
        engine.update_themes_in_db(news_to_classify)
    else:
        logger.info("분류할 대상 뉴스가 없습니다.")

if __name__ == '__main__':
    import sys
    # 실행 시 인자로 'all'을 주면 전체 재분류
    target_mode = 'unclassified'
    if len(sys.argv) > 1 and sys.argv[1] == 'all':
        target_mode = 'all'
        
    run_theme_classification(target=target_mode)