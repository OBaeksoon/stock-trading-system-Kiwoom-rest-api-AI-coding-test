#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import pymysql
import configparser
from datetime import datetime

# 프로젝트 루트 경로를 sys.path에 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

# kiwoom_api 모듈 임포트
from python_modules.kiwoom_api import KiwoomAPI

def get_db_connection():
    """데이터베이스 연결을 설정하고 반환합니다."""
    try:
        config = configparser.ConfigParser()
        config_path = os.path.join(project_root, 'config.ini')
        if not os.path.exists(config_path):
            print(f"Error: config.ini file not found at {config_path}")
            return None
        config.read(config_path)
        
        db_config = config['DB']
        return pymysql.connect(
            host=db_config['HOST'],
            user=db_config['USER'],
            password=db_config['PASSWORD'],
            db=db_config['DATABASE'],
            port=int(db_config['PORT']),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    except Exception as e:
        print(f"Database connection failed: {e}")
        return None

def fetch_top_30_rising_stocks(api):
    """Kiwoom REST API를 사용하여 상승률 상위 30개 종목을 가져옵니다."""
    try:
        print("Fetching top 30 rising stocks from Kiwoom API...")
        stocks = api.get_top_30_rising_stocks()
        if not stocks:
            print("No stocks data received from API.")
            return []
            
        # API 응답에서 필요한 데이터만 추출하고 상위 30개로 제한
        top_stocks = []
        for stock in stocks[:30]:
            top_stocks.append({
                'stock_code': stock.get('stk_cd'),      # 종목코드
                'stock_name': stock.get('stk_nm'),      # 종목명
                'current_price': stock.get('cur_prc'),      # 현재가
                'change_rate': stock.get('flu_rt'),        # 등락률
                'volume': stock.get('now_trde_qty')               # 거래량
            })
        print(f"Successfully fetched {len(top_stocks)} stocks.")
        return top_stocks
    except Exception as e:
        print(f"Failed to fetch stocks from API: {e}")
        return []

def update_database(stocks):
    """데이터베이스의 top_30_rising_stocks 테이블을 업데이트합니다."""
    conn = get_db_connection()
    if not conn:
        return

    try:
        with conn.cursor() as cursor:
            # 테이블 비우기
            cursor.execute("TRUNCATE TABLE top_30_rising_stocks")
            print("Truncated top_30_rising_stocks table.")
            
            # 새 데이터 삽입
            sql = """
                INSERT INTO top_30_rising_stocks 
                (rank, stock_code, stock_name, current_price, fluctuation_rate, volume, updated_at) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            now = datetime.now()
            for i, stock in enumerate(stocks):
                if not all(stock.values()):
                    print(f"Skipping stock with missing data: {stock}")
                    continue
                
                rank = i + 1
                cursor.execute(sql, (
                    rank,
                    stock['stock_code'],
                    stock['stock_name'],
                    int(stock['current_price'].replace('+', '').replace('-', '')),
                    float(stock['change_rate']),
                    int(stock['volume']),
                    now
                ))
            conn.commit()
            print(f"Successfully inserted {len(stocks)} stocks into the database.")
    except Exception as e:
        print(f"Database update failed: {e}")
        conn.rollback()
    finally:
        conn.close()

def main():
    """메인 실행 함수"""
    print("Starting script to get top 30 rising stocks...")
    
    # KiwoomAPI 인스턴스 생성
    try:
        api = KiwoomAPI()
    except Exception as e:
        print(f"Failed to initialize KiwoomAPI: {e}")
        return

    # API에서 데이터 가져오기
    stocks = fetch_top_30_rising_stocks(api)
    
    # 데이터베이스 업데이트
    if stocks:
        update_database(stocks)
    else:
        print("No stocks to update.")
        
    print("Script finished.")

if __name__ == "__main__":
    main()