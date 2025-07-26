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

// MySQLi 객체 생성
$conn = new mysqli($db_host, $db_user, $db_password, $db_name, $db_port);

// 연결 확인
if ($conn->connect_error) {
    die("Connection failed: " . $conn->connect_error);
}

// 뉴스 데이터 가져오기
$sql = "SELECT sn.stock_code, sd.stock_name, sn.title, sn.link, sn.description, sn.pub_date 
        FROM stock_news sn
        JOIN stock_details sd ON sn.stock_code = sd.stock_code
        ORDER BY sn.pub_date DESC LIMIT 100"; // 최신 뉴스 100개
$result = $conn->query($sql);

?>
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>주식 뉴스</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f4f4f4; color: #333; }
        .container { max-width: 1200px; margin: auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #0056b3; text-align: center; margin-bottom: 30px; }
        .news-item { border-bottom: 1px solid #eee; padding: 15px 0; }
        .news-item:last-child { border-bottom: none; }
        .news-title { font-size: 1.2em; font-weight: bold; margin-bottom: 5px; }
        .news-title a { color: #0056b3; text-decoration: none; }
        .news-title a:hover { text-decoration: underline; }
        .news-meta { font-size: 0.9em; color: #666; margin-bottom: 10px; }
        .news-description { font-size: 1em; line-height: 1.6; color: #555; }
        .stock-info { font-weight: bold; color: #28a745; margin-right: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>최신 주식 뉴스</h1>
        <?php
        if ($result->num_rows > 0) {
            while($row = $result->fetch_assoc()) {
                echo "<div class=\"news-item\">";
                echo "<div class=\"news-meta\"><span class=\"stock-info\">" . htmlspecialchars($row['stock_name']) . " (" . htmlspecialchars($row['stock_code']) . ")</span>" . htmlspecialchars($row['pub_date']) . "</div>";
                echo "<div class=\"news-title\"><a href=\"" . htmlspecialchars($row['link']) . "\" target=\"_blank\">" . htmlspecialchars($row['title']) . "</a></div>";
                echo "<div class=\"news-description\">" . htmlspecialchars($row['description']) . "</div>";
                echo "</div>";
            }
        } else {
            echo "<p>뉴스를 찾을 수 없습니다.</p>";
        }
        $conn->close();
        ?>
    </div>
</body>
</html>
