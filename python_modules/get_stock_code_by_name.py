
import json
import sys
import logging
import mysql.connector
import os
import configparser

# --- 로그 설정 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from utils.db_utils import get_db_connection

def get_stock_code_by_name(stock_name):
    """
    stock_details 테이블에서 종목명으로 종목 코드를 조회합니다.
    """
    conn = get_db_connection()
    if conn is None:
        return {"error": "데이터베이스 연결 실패"}

    cursor = conn.cursor(dictionary=True)
    try:
        # 정확한 일치 또는 부분 일치(LIKE)로 검색할 수 있습니다. 우선 정확한 일치로 시도합니다.
        query = "SELECT stock_code FROM stock_details WHERE stock_name = %s"
        cursor.execute(query, (stock_name,))
        result = cursor.fetchone()
        
        if result:
            return {"stock_code": result['stock_code']}
        else:
            # 정확히 일치하는 이름이 없으면 LIKE 검색으로 확장
            query_like = "SELECT stock_code, stock_name FROM stock_details WHERE stock_name LIKE %s LIMIT 1"
            cursor.execute(query_like, (f"%{stock_name}%",))
            result_like = cursor.fetchone()
            if result_like:
                return {"stock_code": result_like['stock_code'], "found_name": result_like['stock_name']}
            else:
                return {"error": f"'{stock_name}'에 해당하는 종목을 찾을 수 없습니다."}
            
    except mysql.connector.Error as err:
        logger.error(f"DB 조회 중 오류 발생: {err}")
        return {"error": f"DB 조회 오류: {err}"}
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(json.dumps({"error": "종목명을 인자로 전달해야 합니다."}))
        sys.exit(1)

    stock_name_arg = sys.argv[1]
    result_json = get_stock_code_by_name(stock_name_arg)
    print(json.dumps(result_json, ensure_ascii=False))
