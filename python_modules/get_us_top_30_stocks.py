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
import logging # logging 모듈 추가

# --- 로그 설정 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
    except requests.exceptions.RequestException as e:
        logger.warning(f"네이버 금융에서 한글 종목명 조회 실패 ({ticker}): {e}")
        return None

def get_major_indices_data():
    """주요 미국 지수 데이터를 가져옵니다."""
    logger.info("주요 미국 지수 데이터 조회 시작.")
    indices = {'^DJI': 'Dow Jones', '^GSPC': 'S&P 500', '^IXIC': 'NASDAQ', '^SOX': 'Philadelphia Semiconductor'}
    data = yf.download(list(indices.keys()), period="2d", progress=False)
    index_data = []
    for ticker, name in indices.items():
        try:
            hist = data['Close'][ticker]
            if len(hist) < 2:
                logger.warning(f"{name} ({ticker}) 지수 데이터 부족 (최소 2일 필요).")
                continue
            prev_close, last_price = hist.iloc[-2], hist.iloc[-1]
            change = last_price - prev_close
            percent_change = (change / prev_close) * 100
            index_data.append((name, ticker, last_price, change, percent_change))
        except Exception as e:
            logger.error(f"{name} ({ticker}) 지수 데이터 처리 중 오류 발생: {e}")
            continue
    logger.info(f"주요 미국 지수 데이터 조회 완료. 총 {len(index_data)}개 지수.")
    return index_data

def get_top_30_us_stocks_data():
    """S&P 500 종목의 등락률을 직접 계산하여 상승률 상위 30개 데이터를 반환합니다."""
    logger.info("S&P 500 상승률 상위 30개 종목 데이터 조회 시작.")
    try:
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        sp500_df = pd.read_html(url)[0]
        tickers = sp500_df['Symbol'].tolist()
        logger.info(f"S&P 500 목록에서 {len(tickers)}개 티커를 가져왔습니다.")
    except Exception as e:
        logger.error(f"S&P 500 목록을 가져오는 데 실패했습니다: {e}")
        return []

    try:
        data = yf.download(tickers, period="2d", progress=False, threads=True)
        if data.empty:
            logger.warning("yfinance에서 데이터를 다운로드하지 못했습니다.")
            return []

        close_prices = data['Close']
        if len(close_prices) < 2:
            logger.warning("계산에 필요한 충분한 데이터가 없습니다 (최소 2일 필요).")
            return []
            
        prev_close = close_prices.iloc[-2]
        last_price = close_prices.iloc[-1]
        
        percent_change = ((last_price - prev_close) / prev_close) * 100
        change = last_price - prev_close

        results_df = pd.DataFrame({
            'ticker': last_price.index,
            'last_price': last_price.values,
            'change': change.values,
            'percent_change': percent_change.values
        })
        
        results_df.dropna(inplace=True)
        top_30_gainers = results_df.sort_values(by='percent_change', ascending=False).head(30)

        top_30_tickers = top_30_gainers['ticker'].tolist()
        yf_tickers = yf.Tickers(top_30_tickers)
        
        company_names = []
        themes = []
        for ticker in top_30_tickers:
            try:
                info = yf_tickers.tickers[ticker].info
                korean_name = get_korean_name_from_naver(ticker)
                company_names.append(korean_name or info.get('shortName', 'N/A'))
                themes.append(info.get('sector', 'N/A'))
            except Exception as e:
                logger.warning(f"티커 {ticker}의 회사명/테마 정보 조회 실패: {e}")
                company_names.append('N/A')
                themes.append('N/A')

        top_30_gainers['company_name'] = company_names
        top_30_gainers['theme'] = themes

        final_data = [
            tuple(x) for x in top_30_gainers[[ 
                'ticker', 'company_name', 'theme', 'last_price', 'change', 'percent_change'
            ]].to_numpy()
        ]
        logger.info(f"S&P 500 상승률 상위 30개 종목 데이터 조회 완료. 총 {len(final_data)}개 종목.")
        return final_data

    except Exception as e:
        logger.error(f"상승률 상위 종목 데이터 처리 중 오류 발생: {e}")
        return []

def get_top_10_market_cap_stocks():
    """
    미국 주식 시장에서 시가총액 상위 10개 종목을 조회합니다.
    (S&P 500 목록을 기반으로 하거나, 더 넓은 범위의 티커를 사용해야 할 수 있습니다.)
    여기서는 S&P 500 목록을 재활용하여 시가총액 정보를 가져옵니다.
    """
    logger.info("시가총액 상위 10개 종목 조회 시작.")
    try:
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P%20500_companies'
        sp500_df = pd.read_html(url)[0]
        tickers = sp500_df['Symbol'].tolist()
        logger.info(f"S&P 500 목록에서 {len(tickers)}개 티커를 가져와 시가총액 조회.")
    except Exception as e:
        logger.error(f"S&P 500 목록을 가져오는 데 실패했습니다: {e}")
        return []

    market_cap_data = []
    # yfinance의 Tickers 객체를 사용하여 여러 티커의 정보를 한 번에 가져옵니다.
    yf_tickers = yf.Tickers(tickers)

    for ticker_symbol in tickers:
        try:
            ticker_info = yf_tickers.tickers[ticker_symbol].info
            market_cap = ticker_info.get('marketCap')
            short_name = ticker_info.get('shortName')
            
            if market_cap and short_name:
                market_cap_data.append({
                    'ticker': ticker_symbol,
                    'company_name': short_name,
                    'market_cap': market_cap
                })
        except Exception as e:
            logger.debug(f"티커 {ticker_symbol}의 시가총액 정보 조회 실패: {e}")
            continue
    
    # 시가총액 기준으로 정렬하고 상위 10개 선택
    top_10_market_cap = sorted(market_cap_data, key=lambda x: x['market_cap'], reverse=True)[:10]
    
    logger.info(f"시가총액 상위 10개 종목 조회 완료. 총 {len(top_10_market_cap)}개 종목.")
    return top_10_market_cap


# --- 데이터베이스 저장 함수 ---
def save_data_to_db(indices_data, top_stocks_data):
    conn = get_db_connection()
    if not conn:
        logger.error("DB 연결을 가져올 수 없습니다. 데이터베이스 저장을 건너뜁니다.")
        return
    
    cursor = conn.cursor()
    try:
        if indices_data:
            logger.info("Updating US indices...")
            cursor.execute("TRUNCATE TABLE us_indices")
            sql = "INSERT INTO us_indices (name, ticker, last_price, change_val, percent_change) VALUES (%s, %s, %s, %s, %s)"
            cursor.executemany(sql, indices_data)
            logger.info(f"{cursor.rowcount} rows inserted into us_indices.")

        if top_stocks_data:
            logger.info("Updating US top stocks with Korean names and themes...")
            cursor.execute("TRUNCATE TABLE us_top_stocks")
            sql = "INSERT INTO us_top_stocks (ticker, company_name, theme, last_price, change_val, percent_change) VALUES (%s, %s, %s, %s, %s, %s)"
            cursor.executemany(sql, top_stocks_data)
            logger.info(f"{cursor.rowcount} rows inserted into us_top_stocks.")
            
        conn.commit()
        logger.info("Database update complete.")
    except mysql.connector.Error as err:
        logger.error(f"Database error during save: {err}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def save_top_market_cap_stocks_to_db(market_cap_data):
    """시가총액 상위 종목 데이터를 데이터베이스에 저장합니다."""
    conn = get_db_connection()
    if not conn:
        logger.error("DB 연결을 가져올 수 없습니다. 시가총액 데이터 저장을 건너뜁니다.")
        return

    cursor = conn.cursor()
    try:
        logger.info("Updating US top market cap stocks...")
        cursor.execute("TRUNCATE TABLE us_top_market_cap_stocks")
        sql = "INSERT INTO us_top_market_cap_stocks (ticker, company_name, market_cap) VALUES (%s, %s, %s)"
        
        # 데이터를 튜플 리스트로 변환
        data_to_insert = [(d['ticker'], d['company_name'], d['market_cap']) for d in market_cap_data]
        
        cursor.executemany(sql, data_to_insert)
        conn.commit()
        logger.info(f"{cursor.rowcount} rows inserted into us_top_market_cap_stocks.")
    except mysql.connector.Error as err:
        logger.error(f"Database error during market cap save: {err}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()


def main():
    logger.info("Fetching US stock data...")
    
    # 시가총액 상위 10개 종목 조회 및 출력
    top_10_market_cap = get_top_10_market_cap_stocks()
    if top_10_market_cap:
        logger.info("\n--- 시가총액 상위 10개 종목 ---")
        for i, stock in enumerate(top_10_market_cap):
            logger.info(f"{i+1}. {stock['company_name']} ({stock['ticker']}): 시가총액 {stock['market_cap']:,}")
        save_top_market_cap_stocks_to_db(top_10_market_cap) # DB에 저장
    else:
        logger.warning("시가총액 상위 10개 종목을 가져오지 못했습니다.")

    indices_data = get_major_indices_data()
    top_stocks_data = get_top_30_us_stocks_data()
    
    if not indices_data and not top_stocks_data:
        logger.warning("Failed to fetch any data. Exiting.")
        return

    save_data_to_db(indices_data, top_stocks_data)
    logger.info("US stock data fetching and saving process completed.")

if __name__ == "__main__":
    main()