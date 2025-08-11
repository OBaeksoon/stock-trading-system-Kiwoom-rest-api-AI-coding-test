import configparser
import os
import logging
import mysql.connector

# --- 로그 설정 ---
logger = logging.getLogger(__name__)

def get_db_connection():
    """config.ini에서 DB 정보를 읽어와 연결을 생성합니다."""
    # 이 파일의 위치를 기준으로 프로젝트 루트 경로를 계산
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, '..', '..')) # python_modules/utils -> public_html
    config_file = os.path.join(project_root, 'config.ini')

    config = configparser.ConfigParser()
    if not os.path.exists(config_file):
        logger.error(f"설정 파일을 찾을 수 없습니다: {config_file}")
        return None
    
    config.read(config_file)
    
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
