# 주식 정보 시스템 프로젝트

키움증권 API를 활용한 주식 정보 조회 및 뉴스 분석 시스템

## 📁 프로젝트 구조

### 🔧 설정 파일
- **config.ini** - 데이터베이스 및 API 설정
- **db_setup.py** - 데이터베이스 초기 설정 스크립트
- **.gitignore** - Git 버전 관리 제외 파일 목록

### 🌐 웹 인터페이스 (PHP)

#### 메인 페이지
- **index.php** - 메인 대시보드 페이지

#### 종목 관련
- **display_all_stocks.php** - 전체 종목 목록 조회 (페이징 처리로 성능 개선)
- **display_stock_details.php** - 종목 상세 정보 표시
- **display_stock_chart.php** - 종목 차트 표시
- **display_technical_analysis.php** - 기술적 지표 분석 결과 (실시간 분석 및 오류 진단 강화)
- **search_stocks.php** - 종목 검색 기능
- **search_stock_by_name.php** - 종목명으로 검색
- **get_stock_details.php** - 종목 상세 정보 API

#### 실시간 상승률 분석 (NEW!)
- **MD/top_30_rising_stocks.php** - 실시간 상승률 30위 종목 표시 (DB 연동)
- **MD/update_news.php** - 뉴스 데이터 업데이트 API

#### 뉴스 관련
- **display_stock_news.php** - 종목별 뉴스 표시
- **search_news.php** - 뉴스 검색 기능

#### 차트 관련
- **chart.html** - 차트 표시용 HTML
- **view_stock_chart.php** - 실시간 HTS 스타일 차트 뷰어
- **fetch_chart_data.php** - 차트 데이터 API (실시간 데이터 중계)

### 🐍 Python 모듈 (python_modules/)

#### 키움증권 API 연동
- **kiwoom_api.py** - 키움증권 REST API 클라이언트

#### 데이터 수집
- **get_all_stocks_to_db.py** - 전체 종목 정보 DB 저장
- **get_stock_details_to_db.py** - 종목 상세 정보 수집
- **get_stock_chart_data.py** - 실시간 차트 데이터 조회 (API 직접 호출)
- **get_stock_code_by_name.py** - 종목명으로 코드 조회
- **get_technical_analysis.py** - 기술적 지표 분석

#### 실시간 상승률 분석 (NEW!)
- **get_top_30_rising_stocks.py** - 실시간 상승률 30위 종목 조회 및 DB 저장
- **get_top_30_themes_news.py** - 상위 종목 관련 뉴스 수집 및 테마 분류

#### 뉴스 분석
- **naver_news_collector.py** - 네이버 뉴스 수집
- **classify_news.py** - 뉴스 분류 기능
- **theme_classifier.py** - 테마별 뉴스 분류 (키움 API 연동)

#### 데이터베이스 관리
- **add_theme_column.py** - 테마 컬럼 추가 스크립트

### 🤖 AI Hedge Fund (ai_hedge_fund/)
AI 기반 주식 분석 및 자동매매 시스템 모듈

### 🏗️ 키움 MCP 모듈 (kiwoom_mcp/)
키움증권 API를 위한 MCP(Model Context Protocol) 구현

#### 설정 (config/)
- **constants.py** - 상수 정의
- **settings.py** - 설정 관리

#### 핸들러 (handlers/)
- **auth.py** - 인증 처리
- **base.py** - 기본 핸들러
- **orders.py** - 주문 처리

#### 모델 (models/)
- **exceptions.py** - 예외 처리
- **types.py** - 데이터 타입 정의

#### 유틸리티 (utils/)
- **datetime_utils.py** - 날짜/시간 유틸리티
- **logging.py** - 로깅 설정

#### 메인 파일
- **main.py** - 메인 실행 파일
- **server.py** - 서버 구동

### 📊 로그 파일 (logs/)
- **kiwoom_api_YYYYMMDD.log** - 키움 API 호출 로그

### 📋 기타 파일
- **프로젝트진행순서.txt** - 프로젝트 진행 순서 가이드

## 🚀 주요 기능

### 1. 종목 정보 관리
- 전체 종목 목록 조회
- 종목별 상세 정보 (현재가, 등락률, 거래량 등)
- 실시간 차트 데이터
- 기술적 지표 분석

### 2. 실시간 상승률 분석 ⭐ NEW!
- **실서버 키움증권 API 연동**으로 실시간 상승률 30위 종목 조회
- 종목별 관련 뉴스 자동 수집 및 표시
- AI 기반 테마 자동 분류
- 현대적이고 반응형 카드 기반 UI
- 고정 메인 페이지 이동 버튼
- 원클릭 뉴스 업데이트 기능

### 3. 뉴스 분석
- 종목별 뉴스 수집 (네이버 뉴스 API)
- AI 기반 테마 분류
- 키움증권 API 테마 정보 연동

### 5. AI Hedge Fund 분석 (NEW!)
- AI 기반 주식 분석 및 자동매매 시스템 연동
- `ai_hedge_fund/` 디렉토리에 위치한 모듈을 통해 고급 분석 기능 제공

## 🔧 설치 및 실행

### 1. 환경 설정
```bash
# Python 의존성 설치
pip install mysql-connector-python requests configparser

# 데이터베이스 초기화
python db_setup.py
```

### 2. 설정 파일 수정
```ini
# config.ini
[DB]
HOST = localhost
USER = your_db_user
PASSWORD = your_db_password
DATABASE = stock
PORT = 3306

[API]
BASE_URL = https://api.kiwoom.com

[NAVER_API]
CLIENT_ID = your_client_id
CLIENT_SECRET = your_client_secret
```

### 3. 데이터베이스 설정
```sql
-- settings 테이블에 API 키 저장
INSERT INTO settings (setting_key, setting_value) VALUES 
('APP_KEY', 'your_kiwoom_app_key'),
('APP_SECRET', 'your_kiwoom_app_secret');
```

### 4. 데이터 수집 실행
```bash
# 전체 종목 정보 수집
python3 python_modules/get_all_stocks_to_db.py

# 실시간 상승률 30위 종목 조회
python3 python_modules/get_top_30_rising_stocks.py

# 상위 종목 뉴스 수집 및 테마 분류
python3 python_modules/get_top_30_themes_news.py

# 뉴스 수집 및 분류
python3 python_modules/naver_news_collector.py
python3 python_modules/theme_classifier.py
```

## 📊 데이터베이스 스키마

### 주요 테이블
- **all_stocks** - 전체 종목 정보
- **stock_details** - 종목 상세 정보
- **stock_news** - 종목별 뉴스 (테마 분류 포함)
- **top_30_rising_stocks** - 상승률 30위 종목 (NEW!)
- **settings** - 시스템 설정 (API 키 등)

## 🔐 보안 고려사항
- API 키는 데이터베이스에 암호화 저장
- CSRF 토큰을 통한 보안 강화
- SQL 인젝션 방지를 위한 Prepared Statement 사용

## 🆕 최신 업데이트 (2025-07-30)

### 실시간 상승률 30위 종목 페이지 개발 완료
- ✅ 실서버 키움증권 API 연동하여 실시간 데이터 조회
- ✅ 종목별 관련 뉴스 자동 수집 및 테마 분류
- ✅ 현대적이고 반응형 UI 디자인 (그라데이션, 카드 레이아웃)
- ✅ 고정 메인 페이지 이동 버튼 (스크롤 시에도 항상 표시)
- ✅ 원클릭 뉴스 업데이트 기능
- ✅ 모바일 최적화 반응형 디자인
- ✅ 전체 프로젝트 구조 정리 및 최적화
- ✅ updates.php 페이지 추가 (업데이트 내역 추적)

### Git 커밋 내역
- `61bf00d` - Fix: MD/top_30_rising_stocks.php 페이지 작동 문제 해결 및 DB 연동
- `f7ddf6c` - 전체 프로젝트 업데이트 및 정리
- `aeb820d` - README.md 업데이트: 실시간 상승률 30위 종목 기능 추가
- `0e19290` - 실시간 상승률 30위 종목 페이지 개발 완료

### 🆕 최신 업데이트 (2025-08-03)

### 차트 데이터 수집 시 수정주가 사용 명시
- ✅ `python_modules/get_stock_chart_data.py` 스크립트에서 키움증권 API로 차트 데이터 요청 시, 수정주가를 사용하도록 명시적으로 코드를 수정하여 가독성 및 유지보수성 향상.

### Git 커밋 내역
- `8d97b95` - feat: 수정주가 사용을 명시적으로 코드에 반영

### 🆕 최신 업데이트 (2025-08-05)

### AI Hedge Fund 분석 메뉴 추가 및 관련 파일 포함
- ✅ `index.php`에 AI Hedge Fund 분석 메뉴 추가
- ✅ `ai_hedge_fund/` 디렉토리 포함 및 관련 파일 정리

### Git 커밋 내역
- `b969ecf` - feat: AI Hedge Fund 분석 메뉴 추가 및 관련 파일 포함

### 🆕 최신 업데이트 (2025-08-01)

### MD/top_30_rising_stocks.php 페이지 작동 문제 해결 및 DB 연동
- ✅ `db_setup.py`에 `top_30_rising_stocks` 테이블 생성 로직 추가
- ✅ `python_modules/get_top_30_rising_stocks.py` 스크립트가 API 데이터를 성공적으로 가져오면 `top_30_rising_stocks` 테이블에 저장하도록 변경
- ✅ `MD/top_30_rising_stocks.php` 페이지가 실시간 스크립트 실행 대신 `top_30_rising_stocks` 테이블에서 데이터를 읽어오도록 로직 변경
- ✅ 장중이 아닐 때도 마지막으로 성공한 데이터를 표시하여 페이지가 비어 보이는 문제 해결

### display_us_stocks.php 연관 국내 종목 표시 문제 해결
- ✅ `display_us_stocks.php`에서 연관 국내 종목 검색 시 `stock_news` 테이블의 테마와 부분적으로 일치하도록 `LIKE` 연산자 사용

### 접근 방법
1. 메인 대시보드에서 "실시간 상승률 30위 종목" 클릭
2. 또는 직접 URL: `/MD/top_30_rising_stocks.php`
3. 업데이트 내역 확인: `/updates.php`

## 📝 라이선스
이 프로젝트는 개인 사용 목적으로 제작되었습니다.

---

## 🤖 Kiwoom MCP 모듈 활용

`kiwoom_mcp/` 디렉토리는 키움증권 API와 상호작용하기 위한 핵심 모듈입니다. 이 프로젝트에서는 `kiwoom_mcp`를 별도의 서버로 실행하는 대신, 필요한 Python 스크립트에서 직접 모듈을 가져와(`import`) 사용하는 것을 기본 방식으로 합니다.

이를 통해 API 클라이언트(`kiwoom/client.py`), 데이터 모델(`models/types.py`) 등의 기능을 다른 파이썬 코드에서 재사용하여 API 연동을 효율적으로 관리할 수 있습니다.

### 🛠️ 주요 활용 방식
- **API 클라이언트 직접 사용**: `python_modules` 내의 스크립트에서 `from kiwoom_mcp.kiwoom.client import KiwoomClient`와 같이 클라이언트를 직접 임포트하여 API를 호출합니다.
- **통합된 설정**: 프로젝트 루트의 `config.ini` 파일에서 API 키와 같은 설정을 읽어와 `kiwoom_mcp` 모듈에 전달합니다.

### 고급 사용: 독립 서버 실행
필요에 따라 `kiwoom_mcp`를 독립적인 **MCP(Model-Context-Protocol) 서버**로 실행하여 API를 테스트하거나 외부 애플리케이션과 연동할 수도 있습니다.

**실행 방법:**
프로젝트 루트 디렉토리에서 다음 명령어를 실행하여 서버를 시작합니다.
```bash
python3 kiwoom_mcp/main.py
```

**제공 도구:**
서버 모드로 실행 시, 다음과 같은 내장 도구를 통해 API 기능을 직접 테스트할 수 있습니다.
- **인증**: `get_access_token`, `check_token_status` 등
- **주문**: `stock_buy_order`, `stock_sell_order` 등
