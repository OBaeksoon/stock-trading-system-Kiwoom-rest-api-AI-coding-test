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
from utils.db_utils import get_db_connection

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
    """S&P 500 종목의 등락률을 직접 계산하여 상승률 상위 30개 데이터를 반환합니다."""
    try:
        # 위키피디아에서 S&P 500 종목 목록을 안정적으로 가져옵니다.
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        sp500_df = pd.read_html(url)[0]
        tickers = sp500_df['Symbol'].tolist()
        print(f"S&P 500 목록에서 {len(tickers)}개 티커를 가져왔습니다.")
    except Exception as e:
        print(f"S&P 500 목록을 가져오는 데 실패했습니다: {e}")
        return []

    try:
        # 모든 티커의 최근 2일치 데이터를 한 번에 다운로드합니다.
        data = yf.download(tickers, period="2d", progress=False, threads=True)
        if data.empty:
            print("yfinance에서 데이터를 다운로드하지 못했습니다.")
            return []

        # 각 티커별로 등락률 계산
        close_prices = data['Close']
        if len(close_prices) < 2:
            print("계산에 필요한 충분한 데이터가 없습니다 (최소 2일 필요).")
            return []
            
        prev_close = close_prices.iloc[-2]
        last_price = close_prices.iloc[-1]
        
        percent_change = ((last_price - prev_close) / prev_close) * 100
        change = last_price - prev_close

        # 결과를 DataFrame으로 합치기
        results_df = pd.DataFrame({
            'ticker': last_price.index,
            'last_price': last_price.values,
            'change': change.values,
            'percent_change': percent_change.values
        })
        
        # 유효하지 않은 데이터(NaN) 제거 및 등락률 순으로 정렬
        results_df.dropna(inplace=True)
        top_30_gainers = results_df.sort_values(by='percent_change', ascending=False).head(30)

        # 회사명 및 테마(섹터) 정보 추가
        top_30_tickers = top_30_gainers['ticker'].tolist()
        yf_tickers = yf.Tickers(top_30_tickers)
        
        company_names = []
        themes = []
        for ticker in top_30_tickers:
            try:
                info = yf_tickers.tickers[ticker].info
                # 네이버 금융에서 한글 이름 조회 시도, 실패 시 yfinance의 영문 이름 사용
                korean_name = get_korean_name_from_naver(ticker)
                company_names.append(korean_name or info.get('shortName', 'N/A'))
                themes.append(info.get('sector', 'N/A'))
            except Exception:
                company_names.append('N/A')
                themes.append('N/A')

        top_30_gainers['company_name'] = company_names
        top_30_gainers['theme'] = themes

        # 최종 데이터 포맷으로 변환
        final_data = [
            tuple(x) for x in top_30_gainers[[
                'ticker', 'company_name', 'theme', 'last_price', 'change', 'percent_change'
            ]].to_numpy()
        ]
        return final_data

    except Exception as e:
        print(f"상승률 상위 종목 데이터 처리 중 오류 발생: {e}")
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