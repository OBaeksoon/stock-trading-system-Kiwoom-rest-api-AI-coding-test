<?php
// 에러 리포팅 활성화 (개발용)
ini_set('display_errors', 1);
error_reporting(E_ALL);

// 로그 파일 경로 설정
define('LOG_FILE', __DIR__ . '/../logs/themed_news.log');

require_once __DIR__ . '/../includes/log_utils.php';

write_log("MD/themed_news.php 스크립트 시작");

// --- 데이터베이스 연결 설정 ---
$config_file = __DIR__ . '/../config.ini';
if (!file_exists($config_file)) {
    write_log("오류: config.ini 파일을 찾을 수 없습니다.");
    die("<p class=\"error\">오류: config.ini 파일을 찾을 수 없습니다.</p>");
}
$config = parse_ini_file($config_file, true);
if ($config === false || !isset($config['DB'])) {
    write_log("오류: config.ini 파일의 [DB] 섹션이 유효하지 않습니다.");
    die("<p class=\"error\">오류: config.ini 파일의 [DB] 섹션이 유효하지 않습니다.</p>");
}

$conn = new mysqli($config['DB']['HOST'], $config['DB']['USER'], $config['DB']['PASSWORD'], $config['DB']['DATABASE'], $config['DB']['PORT']);

if ($conn->connect_error) {
    write_log("데이터베이스 연결 실패: " . $conn->connect_error);
    die("Connection failed: " . $conn->connect_error);
}
write_log("데이터베이스 연결 성공.");

// --- 테마별 뉴스 개수 조회 ---
$sql = "SELECT theme, COUNT(*) as news_count 
        FROM stock_news 
        WHERE theme IS NOT NULL AND theme != '' 
        GROUP BY theme 
        ORDER BY news_count DESC";
write_log("테마별 뉴스 개수 조회 쿼리 실행: " . $sql);
$result = $conn->query($sql);

$themes = [];
if ($result) {
    if ($result->num_rows > 0) {
        while($row = $result->fetch_assoc()) {
            $themes[] = $row;
        }
        write_log("테마별 뉴스 조회 성공. 총 " . count($themes) . "개 테마 발견.");
    } else {
        write_log("테마별 뉴스 조회 결과: 데이터 없음.");
    }
} else {
    write_log("테마별 뉴스 조회 쿼리 실패: " . $conn->error);
}
$conn->close();
write_log("데이터베이스 연결 종료.");
write_log("MD/themed_news.php 스크립트 종료");
?>

<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>주요 테마별 뉴스</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f4f7f6;
            color: #333;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        h1 {
            text-align: center;
            color: #2c3e50;
            margin-bottom: 40px;
        }
        .theme-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 20px;
        }
        .theme-card {
            background-color: #ffffff;
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            padding: 20px;
            text-align: center;
            transition: transform 0.2s, box-shadow 0.2s;
            text-decoration: none;
            color: inherit;
            display: block;
        }
        .theme-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        }
        .theme-card h2 {
            margin-top: 0;
            color: #3498db;
            font-size: 1.5em;
        }
        .theme-card p {
            font-size: 1.2em;
            color: #555;
        }
        .theme-card .count {
            font-weight: bold;
            color: #e74c3c;
        }
        .home-link {
            display: block;
            text-align: center;
            margin-top: 40px;
            text-decoration: none;
            color: #3498db;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>주요 테마별 뉴스 현황</h1>
        <?php if (!empty($themes)): ?>
            <div class="theme-grid">
                <?php foreach ($themes as $theme):
                    // Ensure theme and news_count are properly escaped for HTML output
                    $safe_theme = htmlspecialchars($theme['theme']);
                    $safe_news_count = htmlspecialchars($theme['news_count']);
                    $encoded_theme = urlencode($theme['theme']);
                ?>
                    <a href="display_theme_news_details.php?theme=<?php echo $encoded_theme; ?>" class="theme-card">
                        <h2><?php echo $safe_theme; ?></h2>
                        <p><span class="count"><?php echo $safe_news_count; ?></span>개의 관련 뉴스</p>
                    </a>
                <?php endforeach; ?>
            </div>
        <?php else: ?>
            <p style="text-align:center;">분류된 테마가 없습니다.</p>
        <?php endif; ?>
        <a href="../index.php" class="home-link">메인으로 돌아가기</a>
    </div>
</body>
</html>