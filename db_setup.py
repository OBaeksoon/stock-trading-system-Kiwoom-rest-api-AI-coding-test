import mysql.connector
import configparser
import os
import logging

# --- 기본 경로 설정 ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(CURRENT_DIR, 'config.ini')

# --- 로그 설정 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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

def setup_database():
    """데이터베이스에 settings 테이블을 생성하고 API 키를 저장합니다."""
    conn = get_db_connection()
    if conn is None:
        return

    cursor = conn.cursor()
    
    try:
        # 1. 테이블 생성
        logger.info("`settings` 테이블을 생성합니다...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                setting_key VARCHAR(255) PRIMARY KEY,
                setting_value VARCHAR(255) NOT NULL,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        logger.info("테이블 생성 완료.")

        # 2. `stock_news` 테이블 생성
        logger.info("`stock_news` 테이블을 생성합니다...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_news (
                id INT AUTO_INCREMENT PRIMARY KEY,
                stock_code VARCHAR(20) NOT NULL,
                title VARCHAR(255) NOT NULL,
                link VARCHAR(255) NOT NULL,
                description TEXT,
                pub_date DATETIME,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_news (stock_code, link)
            )
        """)
        logger.info("stock_news 테이블 생성 완료.")

        # 3. config.ini에서 API 키 읽기
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE)
        app_key = config.get('API', 'APP_KEY')
        app_secret = config.get('API', 'APP_SECRET')

        # 3. API 키를 DB에 저장 (INSERT ... ON DUPLICATE KEY UPDATE 사용)
        logger.info("API 키를 데이터베이스에 저장합니다...")
        api_settings = [
            ('APP_KEY', app_key),
            ('APP_SECRET', app_secret)
        ]
        
        insert_query = """
            INSERT INTO settings (setting_key, setting_value) 
            VALUES (%s, %s) 
            ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value);
        """
        cursor.executemany(insert_query, api_settings)
        conn.commit()
        logger.info("API 키 저장 완료.")

    except (configparser.NoSectionError, configparser.NoOptionError) as e:
        logger.error(f"config.ini 파일에서 [API] 정보를 읽는 중 오류 발생: {e}")
    except mysql.connector.Error as err:
        logger.error(f"데이터베이스 작업 중 오류 발생: {err}")
    finally:
        cursor.close()
        conn.close()
        logger.info("데이터베이스 연결을 닫습니다.")

if __name__ == "__main__":
    setup_database()
