import yfinance as yf
import pandas as pd
import json
import warnings
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import logging

# --- 로그 설정 ---
# 웹페이지에서 호출될 때는 파일에 로깅하는 것이 디버깅에 유리합니다.
log_file_path = os.path.join(os.path.dirname(__file__), '..', 'logs', 'get_us_top_30_stocks.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        # logging.StreamHandler() # 필요 시 콘솔 출력 활성화
    ]
)
logger = logging.getLogger(__name__)

warnings.simplefilter(action='ignore', category=FutureWarning)

def get_sp500_tickers():
    """위키피디아에서 S&P 500 티커 목록을 가져옵니다."""
    try:
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        sp500_df = pd.read_html(url)[0]
        tickers = sp500_df['Symbol'].tolist()
        # 일부 티커가 yfinance에서 인식되지 않는 문제를 해결하기 위해 '.'을 '-'로 변경
        tickers = [ticker.replace('.', '-') for ticker in tickers]
        logger.info(f"S&P 500 목록에서 {len(tickers)}개 티커를 가져왔습니다.")
        return tickers
    except Exception as e:
        logger.error(f"S&P 500 목록을 가져오는 데 실패했습니다: {e}")
        return None

def get_korean_name_from_naver(ticker):
    """네이버 금융에서 티커로 한글 종목명을 조회합니다."""
    try:
        # yfinance 티커 형식(BRK-B)을 네이버 형식(BRK.B)으로 변환
        search_ticker = ticker.replace('-', '.')
        url = f"https://finance.naver.com/search/search.naver?query={quote(search_ticker)}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        first_result = soup.select_one('.section_stock .tbl_search a')
        return first_result.get_text(strip=True) if first_result else None
    except requests.exceptions.RequestException as e:
        logger.warning(f"네이버 금융에서 한글 종목명 조회 실패 ({ticker}): {e}")
        return None

def get_top_gainers(tickers, count=30):
    """S&P 500 종목 중 상승률 상위 종목 데이터를 반환합니다."""
    logger.info(f"상승률 상위 {count}개 종목 데이터 조회 시작.")
    try:
        data = yf.download(tickers, period="2d", progress=False, threads=True)
        if data.empty or len(data['Close']) < 2:
            logger.warning("상승률 계산에 필요한 충분한 데이터를 다운로드하지 못했습니다.")
            return []

        close_prices = data['Close']
        prev_close = close_prices.iloc[-2]
        last_price = close_prices.iloc[-1]
        
        percent_change = ((last_price - prev_close) / prev_close) * 100
        
        results_df = pd.DataFrame({
            'ticker': last_price.index,
            'last_price': last_price.values,
            'percent_change': percent_change.values
        })
        
        results_df.dropna(inplace=True)
        top_gainers = results_df.sort_values(by='percent_change', ascending=False).head(count)

        # 상세 정보 추가
        detailed_gainers = []
        for index, row in top_gainers.iterrows():
            try:
                ticker_info = yf.Ticker(row['ticker']).info
                korean_name = get_korean_name_from_naver(row['ticker'])
                detailed_gainers.append({
                    "ticker": row['ticker'],
                    "company_name": korean_name or ticker_info.get('shortName', 'N/A'),
                    "theme": ticker_info.get('sector', 'N/A'),
                    "last_price": row['last_price'],
                    "percent_change": row['percent_change']
                })
            except Exception as e:
                logger.warning(f"상승률 상위 종목 {row['ticker']}의 상세 정보 조회 실패: {e}")
                continue
        
        logger.info(f"상승률 상위 {len(detailed_gainers)}개 종목 데이터 조회 완료.")
        return detailed_gainers

    except Exception as e:
        logger.error(f"상승률 상위 종목 데이터 처리 중 오류 발생: {e}")
        return []

def get_top_market_cap(tickers, count=10):
    """S&P 500 종목 중 시가총액 상위 종목 데이터를 반환합니다."""
    logger.info(f"시가총액 상위 {count}개 종목 데이터 조회 시작.")
    market_cap_data = []
    
    try:
        # yfinance의 Tickers 객체를 사용하여 여러 티커의 정보를 효율적으로 가져옵니다.
        yf_tickers = yf.Tickers(tickers)
        
        for ticker_symbol in yf_tickers.tickers:
            try:
                info = yf_tickers.tickers[ticker_symbol].info
                market_cap = info.get('marketCap')
                
                if market_cap:
                    market_cap_data.append({
                        'ticker': ticker_symbol,
                        'info': info,
                        'market_cap': market_cap
                    })
            except Exception:
                logger.debug(f"티커 {ticker_symbol}의 기본 정보 조회 실패. 건너뜁니다.")
                continue
        
        # 시가총액 기준으로 정렬하고 상위 10개 선택
        top_stocks = sorted(market_cap_data, key=lambda x: x['market_cap'], reverse=True)[:count]
        
        # 가격 정보 추가
        top_tickers = [stock['ticker'] for stock in top_stocks]
        price_data = yf.download(top_tickers, period="2d", progress=False)
        
        detailed_market_cap = []
        for stock in top_stocks:
            try:
                ticker = stock['ticker']
                info = stock['info']
                
                prev_close = price_data['Close'][ticker].iloc[-2]
                last_price = price_data['Close'][ticker].iloc[-1]
                percent_change = ((last_price - prev_close) / prev_close) * 100
                
                korean_name = get_korean_name_from_naver(ticker)
                
                detailed_market_cap.append({
                    "ticker": ticker,
                    "company_name": korean_name or info.get('shortName', 'N/A'),
                    "market_cap": stock['market_cap'],
                    "last_price": last_price,
                    "percent_change": percent_change
                })
            except Exception as e:
                logger.warning(f"시가총액 상위 종목 {stock['ticker']}의 가격 정보 추가 실패: {e}")
                continue

        logger.info(f"시가총액 상위 {len(detailed_market_cap)}개 종목 데이터 조회 완료.")
        return detailed_market_cap

    except Exception as e:
        logger.error(f"시가총액 상위 종목 데이터 처리 중 오류 발생: {e}")
        return []

def main():
    """
    미국 주식 시장의 상승률 상위 30개 종목과 시가총액 상위 10개 종목 정보를 조회하여
    JSON 형식으로 출력합니다.
    """
    logger.info("미국 주식 데이터 조회를 시작합니다.")
    
    sp500_tickers = get_sp500_tickers()
    if not sp500_tickers:
        print(json.dumps({"error": "S&P 500 티커 목록을 가져올 수 없습니다."}))
        return

    top_gainers_data = get_top_gainers(sp500_tickers, 30)
    top_market_cap_data = get_top_market_cap(sp500_tickers, 10)
    
    final_output = {
        "top_gainers": top_gainers_data,
        "top_market_cap": top_market_cap_data
    }
    
    # PHP에서 쉽게 사용할 수 있도록 JSON으로 출력
    print(json.dumps(final_output, indent=4))
    logger.info("미국 주식 데이터 조회를 완료하고 결과를 출력했습니다.")

if __name__ == "__main__":
    # 웹페이지에서 직접 호출될 것을 대비하여, 불필요한 os, configparser 등의 모듈 임포트 제거
    import os
    main()