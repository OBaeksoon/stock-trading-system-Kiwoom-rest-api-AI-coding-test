<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>코스피 및 코스닥 전종목</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; line-height: 1.7; color: #34495e; background-color: #f8f9fa; margin: 0; padding: 0; }
        .navbar { background-color: #2c3e50; padding: 15px 20px; color: white; text-align: center; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .navbar a { color: white; text-decoration: none; margin: 0 15px; font-weight: 500; transition: color 0.3s ease; }
        .navbar a:hover { color: #3498db; }
        .container { max-width: 1200px; margin: 20px auto; background-color: #ffffff; padding: 30px 50px; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
        h1 { color: #2c3e50; text-align: center; border-bottom: 3px solid #3498db; padding-bottom: 15px; margin-bottom: 20px; }
        pre { background-color: #eee; padding: 15px; border-radius: 5px; overflow-x: auto; white-space: pre-wrap; word-wrap: break-word; }
        .error { color: #e74c3c; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 0.9em; }
        th, td { border: 1px solid #ddd; padding: 10px; text-align: left; }
        th { background-color: #f2f2f2; font-weight: 600; position: sticky; top: 0; }
        tr:nth-child(even) { background-color: #f9f9f9; }
        .loading { text-align: center; font-size: 1.2em; color: #555; padding: 50px; }
        .search-container { margin-bottom: 20px; }
        .search-container input { width: 100%; padding: 10px; font-size: 1em; border-radius: 5px; border: 1px solid #ddd; box-sizing: border-box; }
    </style>
</head>
<body>
    <div class="navbar">
        <a href="index.php">프로젝트 개요</a>
        <a href="api_info.php">API 정보</a>
        <a href="all_stocks.php">코스피 및 코스닥 종목</a>
        <a href="updates.php">업데이트중</a>
    </div>
    <div class="container">
        <h1>코스피 및 코스닥 전종목 조회</h1>
        <p>키움증권 모의투자 API(ka10100)를 통해 조회한 코스피 및 코스닥의 전체 종목 목록입니다. 종목명 또는 종목코드로 검색할 수 있습니다.</p>
        
        <div class="search-container">
            <input type="text" id="search-input" placeholder="종목명 또는 종목코드 검색...">
        </div>
        
        <div id="stock-data">
            <p class="loading">종목 목록을 불러오는 중입니다...</p>
        </div>
    </div>

    <script>
        document.addEventListener("DOMContentLoaded", function() {
            const searchInput = document.getElementById('search-input');
            const stockDataContainer = document.getElementById('stock-data');
            let debounceTimer;

            function fetchStocks(searchTerm = '') {
                const loadingMessage = searchTerm ? '검색 중...' : '종목 목록을 불러오는 중입니다...';
                stockDataContainer.innerHTML = `<p class="loading">${loadingMessage}</p>`;
                fetch(`fetch_all_stocks.php?search=${encodeURIComponent(searchTerm)}`)
                    .then(response => response.text())
                    .then(html => {
                        stockDataContainer.innerHTML = html;
                    })
                    .catch(error => {
                        stockDataContainer.innerHTML = '<p class="error">데이터를 불러오는 중 오류가 발생했습니다: ' + error + '</p>';
                    });
            }

            // 초기 로드 시 데이터 가져오기
            fetchStocks();

            // --- 실시간 업데이트를 위한 추가된 부분 시작 ---
            // 5초마다 실시간 데이터 업데이트를 시도합니다.
            // 너무 짧은 간격은 웹 서버와 데이터베이스에 부하를 줄 수 있으니,
            // 웹페이지의 요구사항에 맞춰 이 간격을 조절해주세요 (예: 5000밀리초 = 5초).
            setInterval(function() {
                // 검색창에 입력값이 없을 때만 주기적으로 데이터를 업데이트합니다.
                // 사용자가 검색 중일 때는 검색 결과에 집중하도록 합니다.
                if (!searchInput.value) {
                    fetchStocks();
                }
            }, 60000); // 60000 밀리초 = 60초 간격
            // --- 실시간 업데이트를 위한 추가된 부분 끝 ---

            // 검색 입력 시 debounce를 사용하여 과도한 요청 방지
            searchInput.addEventListener('input', function() {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(() => {
                    fetchStocks(this.value);
                }, 300); // 300ms 지연 후 검색 실행
            });
        });
    </script>
</body>
</html>