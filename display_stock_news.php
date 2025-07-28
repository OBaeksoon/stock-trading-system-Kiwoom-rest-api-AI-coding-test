<?php
session_start(); // 세션 시작

// 데이터베이스 연결 설정
$config_file = __DIR__ . '/config.ini';

if (!file_exists($config_file)) {
    die("Error: config.ini file not found at " . $config_file);
}

$config = parse_ini_file($config_file, true);

$db_host = $config['DB']['HOST'];
$db_user = $config['DB']['USER'];
$db_password = $config['DB']['PASSWORD'];
$db_name = $config['DB']['DATABASE'];
$db_port = $config['DB']['PORT'];

$conn = new mysqli($db_host, $db_user, $db_password, $db_name, $db_port);

if ($conn->connect_error) {
    die("Connection failed: " . $conn->connect_error);
}

// 검색어 처리 로직 수정
$search_query = '';
// 1. 새로운 검색어가 있으면 그 값을 사용하고 세션에 저장
if (isset($_GET['search_query'])) {
    $search_query = $_GET['search_query'];
    $_SESSION['last_search_query'] = $search_query;
} 
// 2. 새로운 검색어가 없고 세션에 마지막 검색어가 있으면 그 값을 사용
else if (isset($_SESSION['last_search_query'])) {
    $search_query = $_SESSION['last_search_query'];
}

$news_list = [];

// 검색어가 있을 경우에만 DB 조회
if (!empty($search_query)) {
    $search_term = "%" . $conn->real_escape_string($search_query) . "%";
    
    $sql = "SELECT sn.stock_code, sd.stock_name, sn.title, sn.link, sn.description, sn.pub_date 
            FROM stock_news sn
            JOIN stock_details sd ON sn.stock_code = sd.stock_code
            WHERE sd.stock_name LIKE ? OR sn.stock_code LIKE ?
            ORDER BY sn.pub_date DESC LIMIT 100";
    
    $stmt = $conn->prepare($sql);
    $stmt->bind_param("ss", $search_term, $search_term);
    $stmt->execute();
    $result = $stmt->get_result();

    if ($result->num_rows > 0) {
        while($row = $result->fetch_assoc()) {
            $news_list[] = $row;
        }
    }
    $stmt->close();
}
$conn->close();
?>
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>종목별 뉴스 검색</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; margin: 20px; background-color: #f8f9fa; color: #333; }
        .container { max-width: 1200px; margin: auto; background: #fff; padding: 20px 30px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
        h1 { color: #0056b3; text-align: center; margin-bottom: 20px; }
        .search-form { text-align: center; margin-bottom: 30px; }
        .search-form input[type="text"] { width: 50%; padding: 12px; font-size: 16px; border: 2px solid #dee2e6; border-radius: 5px; transition: border-color 0.2s; }
        .search-form input[type="text"]:focus { border-color: #007bff; outline: none; }
        .search-form input[type="submit"] { padding: 12px 20px; font-size: 16px; background-color: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; transition: background-color 0.2s; }
        .search-form input[type="submit"]:hover { background-color: #0056b3; }
        .news-item { border-bottom: 1px solid #eee; padding: 15px 0; }
        .news-item:last-child { border-bottom: none; }
        .news-title { font-size: 1.2em; font-weight: bold; margin-bottom: 5px; }
        .news-title a { color: #0056b3; text-decoration: none; }
        .news-title a:hover { text-decoration: underline; }
        .news-meta { font-size: 0.9em; color: #666; margin-bottom: 10px; }
        .news-description { font-size: 1em; line-height: 1.6; color: #555; }
        .stock-info { font-weight: bold; color: #28a745; margin-right: 10px; }
        .message { text-align: center; color: #6c757d; font-size: 1.1em; padding: 40px 0; }
        .home-link { display: block; text-align: center; margin-top: 30px; text-decoration: none; color: #007bff; font-weight: bold; }
        .search-suggestions { position: absolute; background: white; border: 1px solid #ddd; border-top: none; max-height: 200px; overflow-y: auto; width: 50%; z-index: 1000; display: none; }
        .suggestion-item { padding: 10px; cursor: pointer; border-bottom: 1px solid #eee; }
        .suggestion-item:hover { background-color: #f8f9fa; }
        .suggestion-item:last-child { border-bottom: none; }
        .search-container { position: relative; display: inline-block; width: 100%; }
        .loading { color: #666; font-style: italic; }
    </style>
</head>
<body>
    <div class="container">
        <h1>종목별 뉴스 검색</h1>
        <div class="search-form">
            <form action="" method="GET" id="searchForm">
                <div class="search-container">
                    <input type="text" name="search_query" id="searchInput" placeholder="종목명 또는 코드를 입력하세요" value="<?php echo htmlspecialchars($search_query); ?>" autocomplete="off">
                    <div id="suggestions" class="search-suggestions"></div>
                </div>
                <input type="submit" value="검색">
            </form>
        </div>
        <div id="newsResults">

        <?php if (!empty($search_query)): ?>
            <h2>'<?php echo htmlspecialchars($search_query); ?>'에 대한 검색 결과</h2>
            <?php if (!empty($news_list)): ?>
                <?php foreach ($news_list as $row): ?>
                    <div class="news-item">
                        <div class="news-meta"><span class="stock-info"><?php echo htmlspecialchars($row['stock_name']); ?> (<?php echo htmlspecialchars($row['stock_code']); ?>)</span><?php echo htmlspecialchars($row['pub_date']); ?></div>
                        <div class="news-title"><a href="<?php echo htmlspecialchars($row['link']); ?>" target="_blank"><?php echo htmlspecialchars($row['title']); ?></a></div>
                        <div class="news-description"><?php echo htmlspecialchars($row['description']); ?></div>
                    </div>
                <?php endforeach; ?>
            <?php else: ?>
                <p class="message">해당 종목에 대한 뉴스를 찾을 수 없습니다.</p>
            <?php endif; ?>
        <?php else: ?>
            <p class="message">상단 검색창을 통해 원하시는 종목의 뉴스를 찾아보세요.</p>
        <?php endif; ?>
        
        </div>
        <a href="index.php" class="home-link">메인으로 돌아가기</a>
    </div>

    <script>
        let searchTimeout;
        const searchInput = document.getElementById('searchInput');
        const suggestions = document.getElementById('suggestions');
        const newsResults = document.getElementById('newsResults');

        // 실시간 검색 기능
        searchInput.addEventListener('input', function() {
            const query = this.value.trim();
            
            clearTimeout(searchTimeout);
            
            if (query.length >= 1) {
                searchTimeout = setTimeout(() => {
                    searchStocks(query);
                    searchNews(query);
                }, 300);
            } else {
                suggestions.style.display = 'none';
                newsResults.innerHTML = '<p class="message">상단 검색창을 통해 원하시는 종목의 뉴스를 찾아보세요.</p>';
            }
        });

        // 종목 자동완성 검색
        function searchStocks(query) {
            fetch('search_stocks.php?q=' + encodeURIComponent(query))
                .then(response => response.json())
                .then(data => {
                    if (data.length > 0) {
                        let html = '';
                        data.forEach(stock => {
                            html += `<div class="suggestion-item" onclick="selectStock('${stock.code}', '${stock.name}')">${stock.name} (${stock.code})</div>`;
                        });
                        suggestions.innerHTML = html;
                        suggestions.style.display = 'block';
                    } else {
                        suggestions.style.display = 'none';
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    suggestions.style.display = 'none';
                });
        }

        // 뉴스 실시간 검색
        function searchNews(query) {
            newsResults.innerHTML = '<p class="loading">검색 중...</p>';
            
            fetch('search_news.php?q=' + encodeURIComponent(query))
                .then(response => response.text())
                .then(html => {
                    newsResults.innerHTML = html;
                })
                .catch(error => {
                    console.error('Error:', error);
                    newsResults.innerHTML = '<p class="message">검색 중 오류가 발생했습니다.</p>';
                });
        }

        // 종목 선택
        function selectStock(code, name) {
            searchInput.value = name;
            suggestions.style.display = 'none';
            searchNews(name);
        }

        // 외부 클릭 시 자동완성 숨기기
        document.addEventListener('click', function(e) {
            if (!e.target.closest('.search-container')) {
                suggestions.style.display = 'none';
            }
        });

        // 초기 로드 시 기존 검색어가 있으면 결과 표시
        <?php if (!empty($search_query)): ?>
        document.addEventListener('DOMContentLoaded', function() {
            const initialContent = `
                <h2>'<?php echo htmlspecialchars($search_query); ?>'에 대한 검색 결과</h2>
                <?php if (!empty($news_list)): ?>
                    <?php foreach ($news_list as $row): ?>
                        <div class="news-item">
                            <div class="news-meta"><span class="stock-info"><?php echo htmlspecialchars($row['stock_name']); ?> (<?php echo htmlspecialchars($row['stock_code']); ?>)</span><?php echo htmlspecialchars($row['pub_date']); ?></div>
                            <div class="news-title"><a href="<?php echo htmlspecialchars($row['link']); ?>" target="_blank"><?php echo htmlspecialchars($row['title']); ?></a></div>
                            <div class="news-description"><?php echo htmlspecialchars($row['description']); ?></div>
                        </div>
                    <?php endforeach; ?>
                <?php else: ?>
                    <p class="message">해당 종목에 대한 뉴스를 찾을 수 없습니다.</p>
                <?php endif; ?>
            `;
            newsResults.innerHTML = initialContent;
        });
        <?php else: ?>
        newsResults.innerHTML = '<p class="message">상단 검색창을 통해 원하시는 종목의 뉴스를 찾아보세요.</p>';
        <?php endif; ?>
    </script>
</body>
</html>
