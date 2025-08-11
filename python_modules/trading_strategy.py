import logging
import pandas as pd
import json
from datetime import datetime, timedelta

# --- 로컬 모듈 임포트 ---
from utils.db_utils import get_db_connection
from kiwoom_api import KiwoomAPI

# --- 로그 설정 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TradingStrategy:
    def __init__(self):
        self.api = KiwoomAPI()
        self.chart_data_cache = {} # 종목별 차트 데이터 캐시

    def get_daily_data(self, stock_code):
        """API 또는 캐시에서 일봉 데이터를 가져와 DataFrame으로 반환하고 이동평균선을 계산합니다."""
        if stock_code in self.chart_data_cache:
            return self.chart_data_cache[stock_code]

        logger.info(f"[{stock_code}] 일봉 데이터를 API로부터 조회합니다.")
        response_json = self.api.get_chart_data(stock_code, 'daily')
        if not response_json:
            return pd.DataFrame()
        
        try:
            chart_data = json.loads(response_json)
            if not chart_data or "error" in chart_data:
                logger.error(f"[{stock_code}] 차트 데이터 조회 실패: {chart_data.get('error', '알 수 없는 오류')}")
                return pd.DataFrame()

            df = pd.DataFrame(chart_data)
            # 데이터 타입 변환 및 정렬
            numeric_cols = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)

            # 이동평균선 계산
            for period in [5, 10, 20, 60]:
                df[f'ma{period}'] = df['close'].rolling(window=period).mean()
            
            self.chart_data_cache[stock_code] = df # 캐시에 저장
            return df
        except Exception as e:
            logger.error(f"[{stock_code}] 차트 데이터 처리 중 오류 발생: {e}")
            return pd.DataFrame()

    def check_moving_average_support(self, df):
        """5일 또는 10일 이동평균선을 4거래일 이상 이탈하지 않았는지 확인합니다."""
        if len(df) < 4: return False
        last_4_days = df.tail(4)
        condition_met = all(
            (last_4_days['close'] >= last_4_days['ma5']) | 
            (last_4_days['close'] >= last_4_days['ma10'])
        )
        return condition_met

    def check_volume_surge(self, df):
        """전일 거래량 대비 당일 거래량이 50% 이상 상승했는지 확인합니다."""
        if len(df) < 2: return False
        today = df.iloc[-1]
        yesterday = df.iloc[-2]
        if yesterday['volume'] > 0 and today['volume'] >= yesterday['volume'] * 1.5:
            return True
        return False

    def check_volume_law(self, df):
        """거래량 법칙: 대량 거래 후 첫 5일선 지지 시점을 확인합니다."""
        if len(df) < 20: return False
        
        avg_volume_20 = df['volume'].rolling(window=20).mean()
        today = df.iloc[-1]
        
        # 최근 5일 내에 20일 평균 거래량의 5배 이상 터진 날이 있는지 확인
        recent_days = df.tail(5)
        surge_day_exists = any(recent_days['volume'] > avg_volume_20.loc[recent_days.index] * 5)

        # 오늘 종가가 5일선 위에서 지지받는지 확인
        ma5_support = today['close'] > today['ma5'] and today['low'] < today['ma5']

        if surge_day_exists and ma5_support:
            return True
        return False

    def check_5_day_ma_tactic(self, df):
        """5일선 타법: 5일선 이탈 후 재돌파 시점을 확인합니다."""
        if len(df) < 3: return False
        
        today = df.iloc[-1]
        yesterday = df.iloc[-2]
        
        # 어제는 5일선 아래에 있었고, 오늘은 5일선 위로 종가가 마감되었는지 확인
        if yesterday['close'] < yesterday['ma5'] and today['close'] > today['ma5']:
            return True
        return False

    def generate_buy_signal(self, stock_code):
        """종합적인 매수 신호를 생성합니다."""
        df = self.get_daily_data(stock_code)
        if df.empty:
            return None

        buy_reasons = []
        
        if self.check_moving_average_support(df):
            buy_reasons.append("이동평균선 지지")
        if self.check_volume_surge(df):
            buy_reasons.append("거래량 급증")
        if self.check_volume_law(df):
            buy_reasons.append("거래량 법칙 충족")
        if self.check_5_day_ma_tactic(df):
            buy_reasons.append("5일선 타법 충족")

        # TODO: 뉴스/테마 긍정 여부 확인 로직 추가

        if buy_reasons:
            buy_signal = {
                'stock_code': stock_code,
                'signal_type': 'BUY',
                'reason': ', '.join(buy_reasons)
            }
            logger.info(f"매수 신호 생성: {buy_signal}")
            return buy_signal
        
        return None

    def generate_sell_signal(self, owned_stock, current_price):
        """손절 및 익절 규칙에 따라 매도 신호를 생성합니다."""
        purchase_price = owned_stock['purchase_price']
        highest_price = owned_stock.get('highest_price', purchase_price)

        # -2% 손절 규칙
        if current_price <= purchase_price * 0.98:
            return {'signal_type': 'SELL', 'reason': f'-2% 손절'}

        # 3% 이상 상승 후, 고점 대비 -2% 하락 시 익절 규칙
        if highest_price >= purchase_price * 1.03 and current_price <= highest_price * 0.98:
            return {'signal_type': 'SELL', 'reason': f'익절 (고점 대비 하락)'}
        
        return None

if __name__ == '__main__':
    strategy = TradingStrategy()
    # 테스트: 특정 종목에 대한 매수 신호 분석 실행
    test_code = "005930" # 삼성전자
    print(f"--- [{test_code}] 매수 신호 분석 결과 ---")
    signal = strategy.generate_buy_signal(test_code)
    if not signal:
        print("매수 신호 없음.")
