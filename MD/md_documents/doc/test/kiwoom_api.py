import requests
import json
import configparser
import sqlite3
import os
import datetime
import logging # logging 모듈 추가

# --- 파일 경로 설정 (상대 경로 사용) ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(CURRENT_DIR, '..') # python_modules의 부모 디렉토리

CONFIG_FILE = os.path.join(PROJECT_ROOT, 'config.ini')
DB_FILE = os.path.join(PROJECT_ROOT, 'stock_data.db')
WORK_CONTENT_FILE = os.path.join(PROJECT_ROOT, 'md_documents', 'doc', '20250718_작업할내용.txt')

# --- 로그 파일 설정 ---
LOG_DIR = os.path.join(PROJECT_ROOT, 'logs')
os.makedirs(LOG_DIR, exist_ok=True) # 로그 디렉토리가 없으면 생성

LOG_FILE = os.path.join(LOG_DIR, f"kiwoom_api_{datetime.datetime.now().strftime('%Y%m%d')}.log")

# 로거 설정
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 파일 핸들러 (로그 파일에만 저장)
file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# --- 콘솔 핸들러 제거 (PHP에서 실행 시 로그가 출력되지 않도록 함) ---
# console_handler = logging.StreamHandler()
# console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
# logger.addHandler(console_handler)


def initialize_db():
    """데이터베이스와 테이블을 초기화합니다."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_info (
            id INTEGER PRIMARY KEY,
            access_token TEXT,
            account_number TEXT,
            account_name TEXT,
            balance REAL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS work_in_progress (
            id INTEGER PRIMARY KEY,
            content TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS korean_stock_list (
            stk_cd TEXT PRIMARY KEY,
            stk_nm TEXT,
            cur_prc REAL,
            cmpr_yd REAL,
            flu_rt TEXT,
            trde_qty INTEGER,
            trde_amt INTEGER,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    logger.info("데이터베이스와 테이블이 초기화되었습니다.")

def save_api_info(access_token, account_number, account_name, balance):
    """API 정보를 데이터베이스에 저장합니다."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM api_info") 
    cursor.execute('''
        INSERT INTO api_info (access_token, account_number, account_name, balance)
        VALUES (?, ?, ?, ?)
    ''', (access_token, account_number, account_name, balance))
    conn.commit()
    conn.close()
    logger.info("API 정보가 데이터베이스에 저장되었습니다.")

def get_api_info_from_db():
    """데이터베이스에서 API 정보를 가져옵니다."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT access_token, account_number, account_name, balance FROM api_info LIMIT 1")
    info = cursor.fetchone()
    conn.close()
    return info

def save_work_content(content):
    """진행 중인 작업 내용을 데이터베이스에 저장합니다."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM work_in_progress")
    cursor.execute('''
        INSERT INTO work_in_progress (content)
        VALUES (?)
    ''', (content,))
    conn.commit()
    conn.close()
    logger.info("진행 중인 작업 내용이 데이터베이스에 저장되었습니다.")

def get_work_content_from_db():
    """데이터베이스에서 진행 중인 작업 내용을 가져옵니다."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT content FROM work_in_progress ORDER BY last_updated DESC LIMIT 1")
    info = cursor.fetchone()
    conn.close()
    return info[0] if info else ""

def save_all_stocks_to_db(stocks):
    """전체 종목 리스트를 데이터베이스에 저장/업데이트합니다."""
    if not stocks or (isinstance(stocks, dict) and "error" in stocks):
        logger.info("오류가 있거나 저장할 종목 데이터가 없어 DB 저장을 건너뜁니다.")
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    saved_count = 0
    for stock in stocks:
        if not isinstance(stock, dict) or 'code' not in stock: 
            logger.warning(f"유효하지 않은 종목 데이터 형식 또는 'code' 필드 누락: {stock}")
            continue

        stk_cd = stock.get('code')
        stk_nm = stock.get('name')
        cur_prc = float(stock.get('lastPrice', '0').replace(',', '')) if stock.get('lastPrice') else 0.0
        
        cmpr_yd = 0.0 
        flu_rt = '' 
        trde_qty = 0 
        trde_amt = 0 

        cursor.execute('''
            INSERT OR REPLACE INTO korean_stock_list 
            (stk_cd, stk_nm, cur_prc, cmpr_yd, flu_rt, trde_qty, trde_amt, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            stk_cd, stk_nm, cur_prc, cmpr_yd, flu_rt, trde_qty, trde_amt
        ))
        saved_count += 1

    conn.commit()
    conn.close()
    logger.info(f"총 {saved_count}개의 종목 정보를 데이터베이스에 저장/업데이트했습니다.")

# 접근토큰 발급 함수
def issue_access_token(base_url, data):
    """키움 Open API로부터 접근 토큰을 발급받습니다."""
    host = base_url
    endpoint = '/oauth2/token' 
    url = host + endpoint

    headers = {
        'Content-Type': 'application/json;charset=UTF-8',
        'api-id': 'kb00000', 
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        res_json = response.json()
        logger.info('--- 토큰 발급 응답 ---')
        logger.info(f"Code: {response.status_code}")
        logger.info(f"Body: {json.dumps(res_json, indent=4, ensure_ascii=False)}")
        
        if 'access_token' in res_json:
            return {'access_token': res_json['access_token']}
        elif 'token' in res_json: 
            return {'access_token': res_json['token']} 
        else:
            logger.error("응답에 access_token 또는 token 필드가 없습니다.")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"토큰 발급 요청 중 오류 발생: {e}")
        return None
    except json.JSONDecodeError:
        logger.error(f"토큰 발급 응답 JSON 파싱 오류. 응답: {response.text}")
        return None

# 계좌 정보 조회 요청 함수 (kt00004)
def fn_kt00004_get_account_info(base_url, token, data, cont_yn='N', next_key=''):
    """키움 Open API를 통해 계좌 정보를 조회합니다 (kt00004)."""
    host = base_url
    endpoint = '/api/dostk/acnt'
    url = host + endpoint

    headers = {
        'Content-Type': 'application/json;charset=UTF-8',
        'authorization': f'Bearer {token}',
        'cont-yn': cont_yn,
        'next-key': next_key,
        'api-id': 'kt00004',
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        res_json = response.json()
        logger.info('\n--- 계좌 정보 조회 응답 (kt00004) ---')
        logger.info(f"Code: {response.status_code}")
        logger.info(f"Header: {json.dumps({key: response.headers.get(key) for key in ['next-key', 'cont-yn', 'api-id']}, indent=4, ensure_ascii=False)}")
        logger.info(f"Body: {json.dumps(res_json, indent=4, ensure_ascii=False)}")
        
        account_info_data = res_json.get('data', [])
        if isinstance(account_info_data, list) and account_info_data:
            first_account = account_info_data[0]
            account_number = first_account.get('entr', 'N/A')
            account_name = first_account.get('acnt_nm', 'N/A')
            balance = float(first_account.get('tot_est_amt', '0').replace(',', ''))
        else: 
            account_number = res_json.get('entr', 'N/A') 
            account_name = res_json.get('acnt_nm', 'N/A')
            balance = float(res_json.get('tot_est_amt', '0').replace(',', ''))

        return account_number, account_name, balance
    except requests.exceptions.RequestException as e:
        logger.error(f"계좌 정보 조회 요청 (kt00004) 중 오류 발생: {e}")
        return None, None, None
    except json.JSONDecodeError:
        logger.error(f"계좌 정보 조회 응답 (kt00004) JSON 파싱 오류. 응답: {response.text}")
        return None, None, None


def get_kiwoom_token_and_account_info():
    """config.ini에서 API 키를 읽어 토큰을 발급받고 계좌 정보를 조회합니다."""
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)

    try:
        appkey = config.get('API', 'APP_KEY')
        appsecret_value = config.get('API', 'APP_SECRET')
        base_url = config.get('API', 'BASE_URL')
    except (configparser.NoSectionError, configparser.NoOptionError) as e:
        logger.error(f"오류: config.ini 파일의 내용이 올바르지 않습니다. ({e})")
        logger.error("Please ensure [API] section and APP_KEY, APP_SECRET, BASE_URL keys are present.")
        return None, None, None, None

    params_token = {'grant_type': 'client_credentials', 'appkey': appkey, 'secretkey': appsecret_value}
    token_response = issue_access_token(base_url=base_url, data=params_token)

    if token_response and token_response.get('access_token'): 
        access_token = token_response['access_token']
        logger.info("\n토큰 발급 성공. 발급된 토큰으로 계좌 조회를 시작합니다.")
        
        params_account = {
            'qry_tp': '0',   
            'dmst_stex_tp': 'KRX',   
        }
        account_number, account_name, balance = fn_kt00004_get_account_info(base_url=base_url, token=access_token, data=params_account)
        return access_token, account_number, account_name, balance
    else:
        logger.error("\n토큰 발급에 실패하여 계좌 조회를 진행할 수 없습니다.")
        return None, None, None, None

if __name__ == "__main__":
    initialize_db()
    token, account_num, account_name, balance = get_kiwoom_token_and_account_info()
    if token:
        save_api_info(token, account_num, account_name, balance)
        logger.info("\nDB에서 정보 확인:")
        db_info = get_api_info_from_db()
        if db_info:
            logger.info(f"토큰 (DB에서): {db_info[0][:5]}**********")
            logger.info(f"계좌 번호 (DB에서): {db_info[1]}")
            logger.info(f"계좌명 (DB에서): {db_info[2]}")
            logger.info(f"잔액 (DB에서): {db_info[3]}")
        else:
            logger.info("DB에서 데이터를 찾을 수 없습니다.")

    if os.path.exists(WORK_CONTENT_FILE):
        with open(WORK_CONTENT_FILE, 'r', encoding='utf-8') as f:
            work_content = f.read()
        save_work_content(work_content)
    else:
        logger.warning(f"경고: 작업 내용 파일이 다음 위치에 없습니다: {WORK_CONTENT_FILE}")