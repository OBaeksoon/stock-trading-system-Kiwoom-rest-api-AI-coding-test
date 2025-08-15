import requests
import json
import configparser
import os
import time
import kiwoom_api # kiwoom_api 모듈 import
import logging # logging 모듈 추가

# kiwoom_api에서 설정된 logger를 사용
logger = logging.getLogger('kiwoom_api') 

# --- 파일 경로 설정 (상대 경로 사용) ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(CURRENT_DIR, '..')

config = configparser.ConfigParser()
config_path = os.path.join(PROJECT_ROOT, 'config.ini')
config.read(config_path)

try:
    APP_KEY = config['API']['APP_KEY']
    APP_SECRET = config['API']['APP_SECRET']
    BASE_URL = config['API']['BASE_URL'] 
except (configparser.NoSectionError, configparser.NoOptionError) as e:
    logger.error(f"오류: config.ini 파일에 [API] 섹션 또는 필요한 키가 누락되었습니다. ({e})")
    logger.error("[API] 섹션 안에 APP_KEY, APP_SECRET, BASE_URL 키가 있는지 확인해주세요.")
    APP_KEY = None
    APP_SECRET = None
    BASE_URL = None

# 종목정보 조회 (ka10099) - 시장구분 및 페이지네이션 포함
def get_all_stocks_list_by_market(token, base_url, market_type):
    """
    키움 Open API (ka10099)를 통해 특정 시장의 종목 정보를 조회합니다.
    market_type: '0' (코스피), '10' (코스닥)
    """
    host = base_url
    endpoint = '/api/dostk/stkinfo'
    url = host + endpoint

    market_stocks = [] # 현재 시장에서 수집된 종목들을 저장할 리스트
    cont_yn = 'N' 
    next_key = '' 

    market_name = "코스피" if market_type == '0' else "코스닥"
    logger.info(f"--- {market_name} 종목 정보를 가져오는 중...")

    while True:
        headers = {
            'Content-Type': 'application/json;charset=UTF-8',
            'authorization': f'Bearer {token}',
            'cont-yn': cont_yn,
            'next-key': next_key,
            'api-id': 'ka10099', # 'ka10099' API ID 사용
        }
        params = {
            'mrkt_tp': market_type,  # 시장 구분 파라미터 사용
        }

        try:
            response = requests.post(url, headers=headers, json=params)
            response.raise_for_status() 

            res_json = response.json() 
            
            # API 응답 전체를 로그 파일에 기록 (자세한 디버깅용)
            logger.debug(f"Raw API 응답 for {market_name} (Page cont-yn={cont_yn}, next-key={next_key}): {json.dumps(res_json, indent=4, ensure_ascii=False)}")
            
            # 'list' 필드가 존재하고 리스트인지 확인
            if res_json.get('list') and isinstance(res_json['list'], list):
                new_stocks = res_json['list'] # 'data' 대신 'list' 필드 사용
                
                if new_stocks: # 새로 받아온 데이터가 실제로 비어있지 않다면
                    current_batch_count = len(new_stocks)
                    market_stocks.extend(new_stocks)
                    logger.info(f"({market_name}) 현재 페이지에서 {current_batch_count}개 종목 추가 완료. 현재까지 총 {len(market_stocks)}개 수집.")
                else: # 'list' 필드는 있지만 비어있는 리스트인 경우, 더 이상 데이터가 없다고 판단
                    logger.info(f"({market_name}) 'list' 필드는 존재하지만 더 이상 종목이 없습니다. 루프를 종료합니다.")
                    break 
            else:
                # 'list' 필드 자체가 없거나 리스트가 아닌 경우 (예: 오류 응답)
                logger.warning(f"API 응답에 'list' 필드가 없거나 유효한 리스트가 아닙니다. 응답: {json.dumps(res_json, indent=4, ensure_ascii=False)}")
                break # 유효한 데이터가 없으므로 루프 종료

            cont_yn = response.headers.get('cont-yn', 'N')
            next_key = response.headers.get('next-key', '')

            # 연속 조회가 아니거나 next_key가 없으면 루프 종료
            if cont_yn != 'Y' or not next_key:
                logger.info(f"({market_name}) 더 이상 다음 페이지가 없습니다. 최종 수집 완료.")
                break
            
            # 지연 시간을 60초로 설정
            time.sleep(60) # 요청하신 대로 API 호출 사이에 60초 지연 시간을 추가합니다.

        except requests.exceptions.RequestException as e:
            logger.error(f"API 요청 중 오류 발생: {e}")
            if e.response is not None:
                logger.error(f"응답 내용: {e.response.text}")
            return [] # 오류 발생 시 빈 리스트 반환
        except json.JSONDecodeError:
            logger.error(f"응답 JSON 파싱 오류. 응답: {response.text}")
            return [] # 파싱 오류 시 빈 리스트 반환

    logger.info(f"--- 총 {len(market_stocks)}개의 {market_name} 종목 정보 수집 완료.")
    return market_stocks


if __name__ == '__main__':
    logger.info("--- 코스피/코스닥 전종목 정보 업데이트 시작 ---")
    # kiwoom_api.initialize_db() # DB 초기화 확인

    # 필수 API 설정 로드 여부 확인
    if not all([APP_KEY, APP_SECRET, BASE_URL]):
        logger.error("필수 API 설정이 누락되었습니다. config.ini 파일을 확인하고 스크립트를 다시 실행해주세요.")
        exit()

    token_params = {
        'grant_type': 'client_credentials',
        'appkey': APP_KEY,
        'secretkey': APP_SECRET,
    }
    
    # kiwoom_api에서 토큰 발급 함수 호출
    token_response = kiwoom_api.issue_access_token(base_url=BASE_URL, data=token_params)
    
    # token_response 딕셔너리에서 접근 토큰 가져오기
    access_token = token_response.get('access_token') if token_response else None

    if access_token:
        all_stocks = []
        
        # 코스피 종목 조회 (mrkt_tp='0')
        kospi_stocks = get_all_stocks_list_by_market(access_token, BASE_URL, '0')
        all_stocks.extend(kospi_stocks)
        
        # 코스닥 종목 조회 (mrkt_tp='10')
        kosdaq_stocks = get_all_stocks_list_by_market(access_token, BASE_URL, '10')
        all_stocks.extend(kosdaq_stocks)

        if all_stocks: 
            logger.info(f"\n--- 최종적으로 수집된 전체 종목 수: {len(all_stocks)}개 ---")
            kiwoom_api.save_all_stocks_to_db(all_stocks)
        else:
            logger.info("수집된 종목 정보가 없어 DB 저장을 건너깁니다.")
    else:
        logger.error("토큰 발급 실패로 인해 종목 정보를 업데이트할 수 없습니다. 위 로그를 확인해주세요.")

    logger.info("--- 전종목 정보 업데이트 완료 ---")