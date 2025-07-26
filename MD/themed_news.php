<?php
// --- 데이터베이스 연결 설정 ---
$config = parse_ini_file('../config.ini');
$db_host = $config['HOST'];
$db_user = $config['USER'];
$db_pass = $config['PASSWORD'];
$db_name = $config['DATABASE'];
$db_port = $config['PORT'];

$conn = new mysqli($db_host, $db_user, $db_pass, $db_name, $db_port);

if ($conn->connect_error) {
    die("Connection failed: " . $conn->connect_error);
}

// --- 테마별 뉴스 개수 조회 ---
$sql = "SELECT theme, COUNT(*) as news_count 
        FROM stock_news 
        WHERE theme IS NOT NULL AND theme != '' 
        GROUP BY theme 
        ORDER BY news_count DESC";
$result = $conn->query($sql);

$themes = [];
if ($result->num_rows > 0) {
    while($row = $result->fetch_assoc()) {
        $themes[] = $row;
    }
}
$conn->close();
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
                <?php foreach ($themes as $theme): ?>
                    <a href="display_theme_news_details.php?theme=<?php echo urlencode($theme['theme']); ?>" class="theme-card">
                        <h2><?php echo htmlspecialchars($theme['theme']); ?></h2>
                        <p><span class="count"><?php echo $theme['news_count']; ?></span>개의 관련 뉴스</p>
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
