import logging
from flask import Flask, jsonify
from threading import Thread
import os

# --- 로컬 모듈 임포트 ---
# api_server.py가 python_modules 밖에 위치할 것을 대비하여 경로 추가
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'python_modules'))

from python_modules.auto_trader import AutoTrader

# --- 기본 설정 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
app = Flask(__name__)

# --- 전역 변수 ---
# AutoTrader 인스턴스를 저장할 변수
trader_instance = None
# 자동매매 실행 스레드를 저장할 변수
trader_thread = None

@app.route('/start', methods=['POST'])
def start_trading():
    """자동매매를 시작하는 API 엔드포인트"""
    global trader_instance, trader_thread
    
    if trader_instance and trader_instance.is_running:
        return jsonify({"status": "error", "message": "자동매매가 이미 실행 중입니다."}), 400

    trader_instance = AutoTrader()
    # 별도의 스레드에서 자동매매 실행
    trader_thread = Thread(target=trader_instance.run)
    trader_thread.daemon = True # 메인 스레드 종료 시 함께 종료
    trader_thread.start()
    
    logging.info("자동매매 시작 API 호출됨.")
    return jsonify({"status": "success", "message": "자동매매를 시작합니다."})

@app.route('/stop', methods=['POST'])
def stop_trading():
    """자동매매를 중지하는 API 엔드포인트"""
    global trader_instance
    
    if not trader_instance or not trader_instance.is_running:
        return jsonify({"status": "error", "message": "자동매매가 실행 중이 아닙니다."}), 400

    trader_instance.stop()
    logging.info("자동매매 중지 API 호출됨.")
    return jsonify({"status": "success", "message": "자동매매를 중지합니다."})

@app.route('/status', methods=['GET'])
def get_status():
    """자동매매 상태를 확인하는 API 엔드포인트"""
    global trader_instance
    
    if trader_instance and trader_instance.is_running:
        status = {
            "isRunning": True,
            "totalBudget": trader_instance.total_budget,
            "maxBudgetPerStock": trader_instance.max_budget_per_stock,
            "ownedStocksCount": len(trader_instance.owned_stocks),
            "ownedStocks": list(trader_instance.owned_stocks.keys())
        }
        return jsonify({"status": "success", "data": status})
    else:
        return jsonify({"status": "success", "data": {"isRunning": False}})

if __name__ == '__main__':
    # host='0.0.0.0'로 설정하여 외부에서도 접근 가능하도록 함
    app.run(host='0.0.0.0', port=5000, debug=True)
