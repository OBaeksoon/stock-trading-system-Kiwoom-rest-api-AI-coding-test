import configparser
import os
import logging
import mysql.connector
import requests
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- 로그 설정 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- 기본 경로 설정 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, '..')) # public_html
CONFIG_FILE = os.path.join(PROJECT_ROOT, 'config.ini')

# --- 키움증권 API 설정 ---
KIWOOM_API_BASE_URL = "https://api.kiwoom.com"
KIWOOM_MOCK_API_BASE_URL = "https://mockapi.kiwoom.com"

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

# 키움증권 API에서 가져온 테마 데이터 저장
KIWOOM_THEMES = {}

def get_api_settings_from_db():
    """데이터베이스에서 API 설정을 가져옵니다."""
    conn = get_db_connection()
    if conn is None:
        return None, None

    settings = {}
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT setting_key, setting_value FROM settings WHERE setting_key IN ('APP_KEY', 'APP_SECRET')")
        for row in cursor.fetchall():
            settings[row['setting_key']] = row['setting_value']
        
        app_key = settings.get('APP_KEY')
        app_secret = settings.get('APP_SECRET')

        if not app_key or not app_secret:
            logger.warning("DB에서 APP_KEY 또는 APP_SECRET을 찾을 수 없습니다.")
            return None, None
            
        return app_key, app_secret
    except mysql.connector.Error as err:
        logger.error(f"DB에서 API 설정 조회 중 오류 발생: {err}")
        return None, None
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def get_kiwoom_api_token():
    """DB에서 API 키를 읽어와 접근 토큰을 발급받습니다."""
    app_key, app_secret = get_api_settings_from_db()
    if not app_key or not app_secret:
        return None

    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    try:
        base_url = config.get('API', 'BASE_URL')
    except (configparser.NoSectionError, configparser.NoOptionError):
        logger.error(f"config.ini 파일에서 BASE_URL을 찾을 수 없습니다.")
        return None

    url = f"{base_url}/oauth2/token"
    headers = {"content-type": "application/json"}
    data = {
        "grant_type": "client_credentials",
        "appkey": app_key,
        "secretkey": app_secret
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        res_json = response.json()

        access_token = res_json.get("token")
        if access_token:
            logger.info("접근 토큰 발급 성공!")
            return access_token
        else:
            logger.error(f"토큰 발급 실패: 응답에 'token'이 없습니다.")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"토큰 발급 API 요청 중 오류 발생: {e}")
        return None
    except json.JSONDecodeError:
        logger.error(f"토큰 발급 응답 JSON 파싱 오류.")
        return None

def fetch_kiwoom_themes(token=None):
    """키움증권 API에서 테마 정보를 가져옵니다."""
    if not token:
        logger.info("API 토큰이 없어 기본 테마를 사용합니다.")
        return BASIC_THEMES_KEYWORDS
    
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    try:
        base_url = config.get('API', 'BASE_URL')
    except (configparser.NoSectionError, configparser.NoOptionError):
        logger.error(f"config.ini 파일에서 BASE_URL을 찾을 수 없습니다.")
        return BASIC_THEMES_KEYWORDS
    
    url = f"{base_url}/api/dostk/thme"
    
    headers = {
        'authorization': f'Bearer {token}',
        'api-id': 'ka90001',
        'Content-Type': 'application/json;charset=UTF-8'
    }
    
    payload = {
        "qry_tp": "0",  # 전체검색
        "stk_cd": "",
        "date_tp": "10",  # 10일전
        "thema_nm": "",
        "flu_pl_amt_tp": "1",  # 상위기간수익률
        "stex_tp": "1"  # KRX
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('return_code') == 0 and 'thema_grp' in data:
                themes = {}
                for theme_info in data['thema_grp']:
                    theme_name = theme_info.get('thema_nm', '')
                    if theme_name:
                        # 테마별 구성종목 정보도 가져와서 키워드로 활용
                        theme_stocks = fetch_theme_stocks(token, theme_info.get('thema_grp_cd'))
                        themes[theme_name] = theme_stocks
                
                logger.info(f"키움증권 API에서 {len(themes)}개 테마를 가져왔습니다.")
                return {**BASIC_THEMES_KEYWORDS, **themes}
            else:
                logger.warning(f"API 응답 오류: {data.get('return_msg', 'Unknown error')}")
        else:
            logger.warning(f"API 호출 실패: {response.status_code}")
    except Exception as e:
        logger.error(f"키움증권 API 호출 중 오류: {e}")
    
    return BASIC_THEMES_KEYWORDS

def fetch_theme_stocks(token, theme_grp_cd):
    """특정 테마의 구성종목을 가져옵니다."""
    if not token or not theme_grp_cd:
        return []
    
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    try:
        base_url = config.get('API', 'BASE_URL')
    except (configparser.NoSectionError, configparser.NoOptionError):
        logger.error(f"config.ini 파일에서 BASE_URL을 찾을 수 없습니다.")
        return []
    
    url = f"{base_url}/api/dostk/thme"
    
    headers = {
        'authorization': f'Bearer {token}',
        'api-id': 'ka90002',
        'Content-Type': 'application/json;charset=UTF-8'
    }
    
    payload = {
        "date_tp": "2",
        "thema_grp_cd": theme_grp_cd,
        "stex_tp": "1"
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('return_code') == 0 and 'thema_comp_stk' in data:
                return [stock.get('stk_nm', '') for stock in data['thema_comp_stk'] if stock.get('stk_nm')]
    except Exception as e:
        logger.error(f"테마 구성종목 조회 중 오류: {e}")
    
    return []

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

def classify_news_item(news_item, themes_keywords):
    """단일 뉴스 아이템의 테마를 분류합니다."""
    news_id, title, description = news_item
    text_to_check = (title + ' ' + (description or '')).lower()

    best_theme = None
    max_score = 0
    
    for theme, keywords in themes_keywords.items():
        score = 0
        for keyword in keywords:
            if keyword.lower() in text_to_check:
                score += 1
        
        if score > max_score:
            max_score = score
            best_theme = theme
            
    return news_id, best_theme

def update_theme_in_db(conn, news_id, theme):
    """데이터베이스에 분류된 테마를 업데이트합니다."""
    try:
        cursor = conn.cursor()
        # theme이 None일 경우 NULL로 업데이트
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
        # 키움증권 API에서 테마 정보 가져오기
        logger.info("키움증권 API에서 테마 정보를 가져오는 중...")
        token = get_kiwoom_api_token()
        themes_keywords = fetch_kiwoom_themes(token)
        
        conn = get_db_connection()
        if conn is None:
            logger.error("데이터베이스 연결에 실패했습니다. 스크립트를 종료합니다.")
            return

        cursor = conn.cursor()
        cursor.execute("SELECT id, title, description FROM stock_news")
        news_to_classify = cursor.fetchall()
        cursor.close()

        if not news_to_classify:
            logger.info("분류할 뉴스가 없습니다.")
            return

        logger.info(f"총 {len(news_to_classify)}개의 뉴스를 {len(themes_keywords)}개 테마로 분류합니다.")
        
        update_count = 0
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_news = {executor.submit(classify_news_item, news, themes_keywords): news for news in news_to_classify}
            
            db_connections = [get_db_connection() for _ in range(10)]
            
            conn_idx = 0
            for future in as_completed(future_to_news):
                news_id, theme = future.result()
                
                db_conn = db_connections[conn_idx % len(db_connections)]
                if update_theme_in_db(db_conn, news_id, theme):
                    if theme is not None:
                        update_count += 1
                conn_idx += 1

            for db_conn in db_connections:
                if db_conn:
                    db_conn.commit()
                    db_conn.close()

        logger.info(f"총 {update_count}개의 뉴스에 테마를 성공적으로 업데이트했습니다.")

    except mysql.connector.Error as err:
        if 'Unknown column \'id\'' in str(err):
            logger.error("오류: 'stock_news' 테이블에 'id' 컬럼이 없습니다.")
        else:
            logger.error(f"스크립트 실행 중 오류 발생: {err}")
    finally:
        if conn and conn.is_connected():
            conn.close()
            logger.info("메인 데이터베이스 연결을 닫습니다.")

if __name__ == "__main__":
    main()

