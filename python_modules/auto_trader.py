import logging
import time

# --- 로컬 모듈 임포트 ---
from kiwoom_api import KiwoomAPI
from trading_strategy import TradingStrategy
from theme_engine import ThemeEngine

# --- 로그 설정 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AutoTrader:
    def __init__(self):
        self.api = KiwoomAPI()
        self.strategy = TradingStrategy()
        self.theme_engine = ThemeEngine()
        
        # --- 자금 관리 설정 (GEMINI.md 기반) ---
        self.total_budget = 1000000  # 총 매수 금액
        self.max_budget_per_stock = 100000  # 한 종목당 최대 매수 금액
        self.owned_stocks = {}  # 보유 종목 정보: {'종목코드': {'purchase_price': 10000, 'qty': 10, 'highest_price': 10500}}
        self.is_running = False

    def run(self):
        """자동매매 메인 루프"""
        if not self.api.token or not self.api.account_no:
            logger.error("API 토큰 또는 계좌 정보가 없어 자동매매를 시작할 수 없습니다.")
            return

        logger.info("주식 자동매매 시스템을 시작합니다.")
        self.is_running = True
        
        # 보유 종목 초기화 (API에서 실제 잔고 조회)
        self.update_owned_stocks()

        while self.is_running:
            try:
                # 1. 매도 로직 (보유 종목 상태 확인 및 매도 신호 생성)
                self.check_and_sell_stocks()

                # 2. 매수 로직 (새로운 투자 대상 탐색 및 매수 신호 생성)
                self.find_and_buy_stocks()

                # 3. 루프 주기
                logger.info("다음 사이클까지 60초 대기...")
                time.sleep(60)

            except KeyboardInterrupt:
                self.stop()
            except Exception as e:
                logger.error(f"메인 루프에서 예외 발생: {e}", exc_info=True)
                time.sleep(60) # 오류 발생 시 잠시 대기 후 재시도

    def stop(self):
        """자동매매를 중지합니다."""
        logger.info("자동매매 시스템을 중지합니다.")
        self.is_running = False

    def update_owned_stocks(self):
        """API를 통해 실제 계좌의 보유 종목 정보를 가져와 업데이트합니다."""
        logger.info("계좌 잔고 정보를 최신 상태로 업데이트합니다.")
        balance_data = self.api.get_account_balance()
        
        # TODO: balance_data 파싱하여 self.owned_stocks 딕셔너리 구성하는 로직 필요
        # 예시: self.owned_stocks = parse_balance(balance_data)
        logger.info(f"현재 보유 종목: {list(self.owned_stocks.keys())}")

    def check_and_sell_stocks(self):
        """보유 중인 모든 종목에 대해 매도 조건을 확인하고 매도 주문을 실행합니다."""
        if not self.owned_stocks:
            return
            
        logger.info("보유 종목 매도 조건 확인 중...")
        for stock_code, stock_info in list(self.owned_stocks.items()):
            sell_signal = self.strategy.generate_sell_signal(stock_info)
            if sell_signal:
                logger.info(f"매도 신호 감지: {sell_signal}")
                # TODO: 실제 매도 주문 실행
                # self.api.send_order(stock_code, stock_info['qty'], 0, "02") # 시장가 매도
                # del self.owned_stocks[stock_code] # 매도 후 목록에서 제거
    
    def find_and_buy_stocks(self):
        """새로운 매수 대상을 찾고 조건 충족 시 매수 주문을 실행합니다."""
        logger.info("새로운 매수 대상 탐색 중...")
        
        # 1. 매수 후보군 선정 (예: 실시간 상승률 상위 종목)
        rising_stocks = self.api.get_top_30_rising_stocks()
        if not rising_stocks:
            logger.warning("매수 후보군(상승률 상위)을 가져오지 못했습니다.")
            return

        candidate_stocks = rising_stocks['pred_pre_flu_rt_upper']
        
        for stock in candidate_stocks:
            stock_code = stock.get('stk_cd')
            if not stock_code or stock_code in self.owned_stocks:
                continue # 이미 보유한 종목은 건너뛰기

            # 2. 매수 전략 분석
            buy_signal = self.strategy.generate_buy_signal(stock_code)
            if buy_signal:
                logger.info(f"매수 신호 감지: {buy_signal}")
                
                # 3. 자금 관리 및 매수 주문 실행
                # TODO: 현재 총 사용 예산 계산
                used_budget = sum(s['purchase_price'] * s['qty'] for s in self.owned_stocks.values())
                
                if self.total_budget - used_budget >= self.max_budget_per_stock:
                    # TODO: 실제 매수 주문 실행
                    # purchase_price = float(stock.get('cur_prc'))
                    # quantity_to_buy = self.max_budget_per_stock // purchase_price
                    # self.api.send_order(stock_code, quantity_to_buy, 0, "01") # 시장가 매수
                    logger.info(f"매수 주문 실행 (시뮬레이션): {stock_code}")
                else:
                    logger.info("예산 부족으로 더 이상 매수할 수 없습니다.")
                    break # 예산 없으면 루프 중단

if __name__ == '__main__':
    trader = AutoTrader()
    trader.run()
