import yfinance as yf
import pandas as pd
import json
import warnings
import requests
import re
import configparser
import os
import mysql.connector
from bs4 import BeautifulSoup
from urllib.parse import quote

# --- 기본 경로 및 설정 ---
warnings.simplefilter(action='ignore', category=FutureWarning)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(CURRENT_DIR, '..')
CONFIG_FILE = os.path.join(PROJECT_ROOT, 'config.ini')

# --- DB 연결 함수 ---
def get_db_connection():
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    try:
        return mysql.connector.connect(
            host=config.get('DB', 'HOST'),
            user=config.get('DB', 'USER'),
            password=config.get('DB', 'PASSWORD'),
            database=config.get('DB', 'DATABASE'),
            port=config.getint('DB', 'PORT')
        )
    except (mysql.connector.Error, configparser.Error) as e:
        print(f"Database connection failed: {e}")
        return None

# --- 데이터 가져오기 함수들 ---
def get_korean_name_from_naver(ticker):
    """네이버 금융에서 티커로 한글 종목명을 조회합니다."""
    try:
        url = f"https://finance.naver.com/search/search.naver?query={quote(ticker)}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        first_result = soup.select_one('.section_stock .tbl_search a')
        return first_result.get_text(strip=True) if first_result else None
    except requests.exceptions.RequestException:
        return None

def get_major_indices_data():
    """주요 미국 지수 데이터를 가져옵니다."""
    indices = {'^DJI': 'Dow Jones', '^GSPC': 'S&P 500', '^IXIC': 'NASDAQ', '^SOX': 'Philadelphia Semiconductor'}
    data = yf.download(list(indices.keys()), period="2d", progress=False)
    index_data = []
    for ticker, name in indices.items():
        try:
            hist = data['Close'][ticker]
            if len(hist) < 2: continue
            prev_close, last_price = hist.iloc[-2], hist.iloc[-1]
            change = last_price - prev_close
            percent_change = (change / prev_close) * 100
            index_data.append((name, ticker, last_price, change, percent_change))
        except Exception:
            continue
    return index_data

def get_top_30_us_stocks_data():
    """Yahoo Finance에서 상승률 상위 종목 데이터를 가져와 한글명과 테마를 추가합니다."""
    url = "https://finance.yahoo.com/gainers"
    headers = {'User-Agent': 'Mozilla/5.0', 'Accept-Language': 'en-US,en;q=0.9'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        tables = pd.read_html(response.text)
        if not tables: return []
        
        df = tables[0][['Symbol', 'Name', 'Price']].copy()
        price_split = df['Price'].str.split(n=1, expand=True)
        df['last_price'] = price_split[0]
        
        def extract_change(text):
            match = re.search(r'([+-]?[\d,]+\.\d+)\s+\(([+-]?[\d,]+\.\d+)%\)', str(text))
            return match.group(1).replace(',', '') if match else None
        def extract_percent_change(text):
            match = re.search(r'([+-]?[\d,]+\.\d+)\s+\(([+-]?[\d,]+\.\d+)%\)', str(text))
            return match.group(2).replace(',', '') if match else None

        df['change'] = price_split[1].apply(extract_change)
        df['percent_change'] = price_split[1].apply(extract_percent_change)
        
        df.rename(columns={'Symbol': 'ticker', 'Name': 'company_name'}, inplace=True)
        df.drop(columns=['Price'], inplace=True)

        for col in ['last_price', 'change', 'percent_change']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df.dropna(inplace=True)
        
        df['theme'] = ''
        tickers = df['ticker'].tolist()
        
        # yfinance로 여러 티커의 정보를 한 번에 가져옵니다.
        yf_tickers = yf.Tickers(tickers)
        for ticker_obj in yf_tickers.tickers.values():
            try:
                info = ticker_obj.info
                ticker = info.get('symbol')
                if not ticker: continue
                
                # 테마(섹터) 정보 추가
                theme = info.get('sector', 'N/A')
                df.loc[df['ticker'] == ticker, 'theme'] = theme
                
                # 한글 종목명 조회 및 업데이트
                korean_name = get_korean_name_from_naver(ticker)
                if korean_name:
                    df.loc[df['ticker'] == ticker, 'company_name'] = korean_name

            except Exception:
                continue # 개별 티커 오류는 무시

        return [tuple(x) for x in df[['ticker', 'company_name', 'theme', 'last_price', 'change', 'percent_change']].to_numpy()]
        
    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"Failed to fetch or parse top stocks data: {e}")
        return []

# --- 데이터베이스 저장 함수 ---
def save_data_to_db(indices_data, top_stocks_data):
    conn = get_db_connection()
    if not conn: return
    
    cursor = conn.cursor()
    try:
        if indices_data:
            print("Updating US indices...")
            cursor.execute("TRUNCATE TABLE us_indices")
            sql = "INSERT INTO us_indices (name, ticker, last_price, change_val, percent_change) VALUES (%s, %s, %s, %s, %s)"
            cursor.executemany(sql, indices_data)
            print(f"{cursor.rowcount} rows inserted into us_indices.")

        if top_stocks_data:
            print("Updating US top stocks with Korean names and themes...")
            cursor.execute("TRUNCATE TABLE us_top_stocks")
            sql = "INSERT INTO us_top_stocks (ticker, company_name, theme, last_price, change_val, percent_change) VALUES (%s, %s, %s, %s, %s, %s)"
            cursor.executemany(sql, top_stocks_data)
            print(f"{cursor.rowcount} rows inserted into us_top_stocks.")
            
        conn.commit()
        print("Database update complete.")
    except mysql.connector.Error as err:
        print(f"Database error: {err}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def main():
    print("Fetching US stock data...")
    indices_data = get_major_indices_data()
    top_stocks_data = get_top_30_us_stocks_data()
    
    if not indices_data and not top_stocks_data:
        print("Failed to fetch any data. Exiting.")
        return

    save_data_to_db(indices_data, top_stocks_data)

if __name__ == "__main__":
    main()