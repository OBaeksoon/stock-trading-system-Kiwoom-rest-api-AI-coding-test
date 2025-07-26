import configparser
import os
import logging
import mysql.connector

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

def add_theme_column():
    """stock_news 테이블에 theme 컬럼을 추가합니다."""
    conn = None
    try:
        conn = get_db_connection()
        if conn is None:
            logger.error("데이터베이스 연결에 실패하여 컬럼을 추가할 수 없습니다.")
            return

        cursor = conn.cursor()
        
        # 컬럼 존재 여부 확인
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
              AND TABLE_NAME = 'stock_news' 
              AND COLUMN_NAME = 'theme'
        """, (conn.database,))
        
        if cursor.fetchone()[0] == 0:
            # 컬럼이 존재하지 않으면 추가
            cursor.execute("ALTER TABLE stock_news ADD COLUMN theme VARCHAR(255) DEFAULT NULL COMMENT '분류된 테마'")
            logger.info("'stock_news' 테이블에 'theme' 컬럼을 성공적으로 추가했습니다.")
        else:
            logger.info("'theme' 컬럼은 'stock_news' 테이블에 이미 존재합니다.")
            
        conn.commit()
        cursor.close()

    except mysql.connector.Error as err:
        logger.error(f"컬럼 추가 중 오류 발생: {err}")
    finally:
        if conn:
            conn.close()
            logger.info("데이터베이스 연결을 닫습니다.")

if __name__ == "__main__":
    add_theme_column()
