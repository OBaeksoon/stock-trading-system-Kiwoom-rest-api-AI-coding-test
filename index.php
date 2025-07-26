<?php
// --- 데이터베이스 연결 설정 ---
$config = parse_ini_file('config.ini');
$db_host = $config['HOST'];
$db_user = $config['USER'];
$db_pass = $config['PASSWORD'];
$db_name = $config['DATABASE'];
$db_port = $config['PORT'];

$conn = new mysqli($db_host, $db_user, $db_pass, $db_name, $db_port);
if ($conn->connect_error) {
    die("Connection failed: " . $conn->connect_error);
}

// --- 대시보드 데이터 조회 ---
// 1. 전체 종목 수
$total_stocks_result = $conn->query("SELECT COUNT(*) as count FROM stock_details");
$total_stocks = $total_stocks_result->fetch_assoc()['count'];

// 2. 전체 뉴스 수
$total_news_result = $conn->query("SELECT COUNT(*) as count FROM stock_news");
$total_news = $total_news_result->fetch_assoc()['count'];

// 3. 분류된 테마 종류 수
$total_themes_result = $conn->query("SELECT COUNT(DISTINCT theme) as count FROM stock_news WHERE theme IS NOT NULL AND theme != ''");
$total_themes = $total_themes_result->fetch_assoc()['count'];

// 4. 상위 5개 테마
$top_themes_result = $conn->query("SELECT theme, COUNT(*) as count 
                                   FROM stock_news 
                                   WHERE theme IS NOT NULL AND theme != '' 
                                   GROUP BY theme 
                                   ORDER BY count DESC 
                                   LIMIT 5");
$top_themes = [];
while($row = $top_themes_result->fetch_assoc()) {
    $top_themes[] = $row;
}

$conn->close();
?>
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>주식 자동매매 시스템 대시보드</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f0f2f5;
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
            color: #1a2c4e;
            margin-bottom: 30px;
            font-size: 2.5em;
        }
        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }
        .stat-card {
            background: #fff;
            border-radius: 10px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            padding: 20px;
            text-align: center;
            text-decoration: none;
            color: inherit;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .stat-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 6px 16px rgba(0,0,0,0.12);
        }
        .stat-card h3 {
            margin: 0 0 10px 0;
            font-size: 1.1em;
            color: #555;
        }
        .stat-card .stat-number {
            font-size: 2.2em;
            font-weight: 700;
            color: #3498db;
        }
        .top-themes-card {
            grid-column: 1 / -1; /* Full width */
            background: #fff;
            border-radius: 10px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            padding: 20px;
        }
        .top-themes-card h3 {
            text-align: center;
            margin: 0 0 20px 0;
            color: #555;
        }
        .top-themes-list {
            list-style: none;
            padding: 0;
            margin: 0;
        }
        .top-themes-list li {
            display: flex;
            justify-content: space-between;
            padding: 10px;
            border-bottom: 1px solid #f0f2f5;
        }
        .top-themes-list li:last-child {
            border-bottom: none;
        }
        .top-themes-list .theme-name {
            font-weight: 600;
        }
        .top-themes-list .theme-count {
            font-weight: bold;
            color: #e74c3c;
        }
        .menu-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 25px;
        }
        .menu-card {
            background: linear-gradient(145deg, #ffffff, #e6e9ee);
            border-radius: 15px;
            box-shadow: 8px 8px 16px #d1d9e6, -8px -8px 16px #ffffff;
            padding: 25px;
            text-align: center;
            transition: all 0.3s ease-in-out;
            text-decoration: none;
            color: inherit;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            min-height: 120px;
        }
        .menu-card:hover {
            transform: translateY(-5px);
        }
        .menu-card h2 {
            margin: 0 0 10px 0;
            color: #3498db;
            font-size: 1.5em;
        }
        .menu-card p {
            font-size: 0.9em;
            color: #555;
            margin: 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>주식 자동매매 대시보드</h1>

        <div class="dashboard-grid">
            <a href="display_all_stocks.php" class="stat-card">
                <h3>총 관리 종목</h3>
                <p class="stat-number"><?php echo number_format($total_stocks); ?></p>
            </a>
            <a href="MD/themed_news.php" class="stat-card">
                <h3>수집된 뉴스</h3>
                <p class="stat-number"><?php echo number_format($total_news); ?></p>
            </a>
            <a href="MD/themed_news.php" class="stat-card">
                <h3>분류된 테마</h3>
                <p class="stat-number"><?php echo number_format($total_themes); ?></p>
            </a>
            <div class="top-themes-card">
                <h3>뉴스 상위 테마 (Top 5)</h3>
                <ul class="top-themes-list">
                    <?php foreach($top_themes as $theme): ?>
                        <li>
                            <span class="theme-name"><?php echo htmlspecialchars($theme['theme']); ?></span>
                            <span class="theme-count"><?php echo number_format($theme['count']); ?> 개</span>
                        </li>
                    <?php endforeach; ?>
                </ul>
            </div>
        </div>

        <div class="menu-grid">
            <a href="display_all_stocks.php" class="menu-card">
                <h2>전체 종목 조회</h2>
                <p>코스피/코스닥 모든 종목의 현재가를 확인합니다.</p>
            </a>
            <a href="MD/themed_news.php" class="menu-card">
                <h2>테마별 뉴스</h2>
                <p>주요 테마별 뉴스 현황을 봅니다.</p>
            </a>
            <a href="display_stock_news.php" class="menu-card">
                <h2>종목별 뉴스 검색</h2>
                <p>특정 주식 종목에 대한 최신 뉴스를 검색합니다.</p>
            </a>
            <a href="display_stock_details.php" class="menu-card">
                <h2>종목 상세 정보</h2>
                <p>종목 코드를 입력하여 상세 정보를 조회합니다.</p>
            </a>
            <a href="display_technical_analysis.php" class="menu-card">
                <h2>기술적 지표 조회</h2>
                <p>종목의 이동평균, RSI, MACD 등 기술적 지표를 확인합니다.</p>
            </a>
        </div>
    </div>
</body>
</html>
