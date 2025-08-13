# SuperClaude 전체 명령어

이 문서는 사용 가능한 모든 SuperClaude 명령어와 그에 대한 설명을 한국어로 제공합니다.

---

### **sc_analyze**
- **설명:** 다차원 코드베이스 분석
- **페르소나:** analyzer, architect, security
- **복잡도:** 높음
- **사용 예제:** `sc_analyze --args "src/api" --flags "--deep --security"` (src/api 디렉토리에 대해 심층 보안 분석 실행)

---

### **sc_build**
- **설명:** 지능형 스캐폴딩을 통한 범용 프로젝트 빌더
- **페르소나:** architect, frontend, backend
- **복잡도:** 중간
- **사용 예제:** `sc_build --args "new-feature-branch" --persona "frontend"` (프론트엔드 페르소나를 사용하여 'new-feature-branch' 빌드)

---

### **sc_cleanup**
- **설명:** 프로젝트 정리 및 기술 부채 감소
- **페르소나:** refactorer
- **복잡도:** 중간
- **사용 예제:** `sc_cleanup --args "./" --flags "--unused --formatting"` (프로젝트 전체에서 사용되지 않는 코드 정리 및 코드 포맷팅)

---

### **sc_design**
- **설명:** 시스템 설계 및 아키텍처 오케스트레이션
- **페르소나:** architect, frontend
- **복잡도:** 높음
- **사용 예제:** `sc_design --args "user-authentication-service" --flags "--architecture --api"` (사용자 인증 서비스의 아키텍처 및 API 설계)

---

### **sc_document**
- **설명:** 포괄적인 문서 생성
- **페르소나:** scribe, mentor
- **복잡도:** 중간
- **사용 예제:** `sc_document --args "src/utils" --flags "--api --readme"` (src/utils 디렉토리에 대한 API 문서 및 README 파일 생성)

---

### **sc_estimate**
- **설명:** 증거 기반 프로젝트 추정
- **페르소나:** analyzer, architect
- **복잡도:** 높음
- **사용 예제:** `sc_estimate --args "payment-gateway-integration" --flags "--detailed --risks"` (결제 게이트웨이 통합 작업에 대한 상세 견적 및 위험 분석)

---

### **sc_explain**
- **설명:** 상세한 컨텍스트를 포함한 교육용 설명
- **페르소나:** mentor, scribe
- **복잡도:** 중간
- **사용 예제:** `sc_explain --args "React Hooks" --flags "--simple --examples"` (React Hooks에 대해 간단한 예제와 함께 설명)

---

### **sc_git**
- **설명:** 지능형 작업을 통한 Git 워크플로우 도우미
- **페르소나:** devops, scribe
- **복잡도:** 중간
- **사용 예제:** `sc_git --args "commit -m 'feat: add user login'" --flags "--checkpoint"` ('feat: add user login' 메시지로 현재 변경사항을 커밋하고 체크포인트 생성)

---

### **sc_implement**
- **설명:** 페르소나 기반 접근 방식을 통한 기능 구현
- **페르소나:** frontend, backend, architect
- **복잡도:** 높음
- **사용 예제:** `sc_implement --args "user-profile-page" --persona "frontend" --flags "--test"` (프론트엔드 페르소나를 사용하여 테스트와 함께 사용자 프로필 페이지 구현)

---

### **sc_improve**
- **설명:** 증거 기반 코드 개선
- **페르소나:** refactorer, performance, architect
- **복잡도:** 중간
- **사용 예제:** `sc_improve --args "src/database/query.js" --flags "--refactor --optimize"` (src/database/query.js 파일 리팩토링 및 최적화)

---

### **sc_index**
- **설명:** 명령어 카탈로그 브라우징 및 검색
- **페르소나:** mentor, analyzer
- **복잡도:** 낮음
- **사용 예제:** `sc_index --args "git"` ('git'과 관련된 모든 명령어 검색)

---

### **sc_load**
- **설명:** 프로젝트 컨텍스트 로딩 및 구성
- **페르소나:** analyzer, architect, scribe
- **복잡도:** 중간
- **사용 예제:** `sc_load --args "my-workflow.json" --flags "--workflow"` (my-workflow.json 파일에서 워크플로우 구성 로드)

---

### **sc_mcp**
- **설명:** MCP 서버 통합 및 라우팅 관리
- **사용 예제:** `sc_mcp --action "route" --servers "playwright"` (요청을 Playwright 서버로 라우팅)

---

### **sc_optimize**
- **설명:** 토큰 최적화 및 효율성 설정 구성
- **사용 예제:** `sc_optimize --mode "adaptive"` (토큰 최적화 모드를 '적응형'으로 설정)

---

### **sc_persona**
- **설명:** 행동 적응을 통한 활성 SuperClaude 페르소나 전환 또는 쿼리
- **사용 예제:** `sc_persona --action "switch" --name "backend"` (활성 페르소나를 '백엔드'로 전환)

---

### **sc_spawn**
- **설명:** 특수 에이전트 스포닝 및 조정
- **페르소나:** architect
- **복잡도:** 높음
- **사용 예제:** `sc_spawn --args "code-review" --flags "--role 'security'"` (보안 검토 역할을 가진 전문 에이전트 생성)

---

### **sc_task**
- **설명:** 장기적인 작업 및 프로젝트 관리
- **페르소나:** architect, devops
- **복잡도:** 낮음
- **사용 예제:** `sc_task --args "create 'Setup production environment'" --flags "--milestone 'v1.0'"` ('v1.0' 마일스톤에 '프로덕션 환경 설정' 작업 생성)

---

### **sc_test**
- **설명:** 포괄적인 테스트 전략
- **페르소나:** qa
- **복잡도:** 중간
- **사용 예제:** `sc_test --args "src/components" --flags "--unit --coverage"` (src/components에 대해 단위 테스트 실행 및 커버리지 확인)

---

### **sc_troubleshoot**
- **설명:** 지능형 문제 진단 및 해결
- **페르소나:** analyzer, backend
- **복잡도:** 중간
- **사용 예제:** `sc_troubleshoot --args "api-500-error" --flags "--logs --fix"` (API 500 에러에 대해 로그를 분석하고 수정 시도)

---

### **sc_workflow**
- **설명:** 다단계 워크플로우 오케스트레이션
- **페르소나:** architect, devops
- **복잡도:** 높음
- **사용 예제:** `sc_workflow --args "deploy-to-staging" --flags "--stages 'build,test,deploy'"` ('build, test, deploy' 단계를 포함하는 '스테이징 배포' 워크플로우 실행)


docker run -d -p 3000:8080 -v ollama:/root/.ollama -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:ollama

sc_optimize --mode "adaptive" sc_improve --args "@display_top_30_rising_stocks.php" --flags "--refactor --optimize" 

sc_optimize --mode "adaptive" sc_improve --args "@display_top_30_rising_stocks.php" --flags "--refactor --optimize" sc_troubleshoot --args "뉴스 업데이트 시작 버튼을 클릭하면 업데이트 중 오류가 발생했습니다. 라는 오류가 나와" --flags "--logs --fix"  

sc_git --args "commit -m 'feat: add user login'" --flags "--checkpoint"

sc_spawn --args "code-review" --flags "--role 'security'" sc_task --args "create 'Setup production environment'" --flags "--milestone 'v1.0'"

sc_spawn --args "code-review" --flags "--role 'security'" sc_task --args "create 'Setup production environment'" --flags "--milestone 'v1.0'"

sc_troubleshoot --args "index.php에 연결된 각 메뉴의 파일에 에대해 문제점을 찾고 해결, 로그가 없다면 각 파일에 로그을 출력 하는 기능을 추가 하고 진행" --flags "--logs --fix"