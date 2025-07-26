<?php
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

// 검색어 처리
$search_query = isset($_GET['search_query']) ? $_GET['search_query'] : '';
$news_list = [];

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
    </style>
</head>
<body>
    <div class="container">
        <h1>종목별 뉴스 검색</h1>
        <div class="search-form">
            <form action="" method="GET">
                <input type="text" name="search_query" placeholder="종목명 또는 코드를 입력하세요" value="<?php echo htmlspecialchars($search_query); ?>">
                <input type="submit" value="검색">
            </form>
        </div>

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
        
        <a href="index.php" class="home-link">메인으로 돌아가기</a>
    </div>
</body>
</html>
