<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>미국 주식 현황 및 국내 연관 테마</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; background-color: #f8f9fa; color: #212529; }
        .container { max-width: 1400px; margin: 0 auto; background-color: #ffffff; padding: 30px; border-radius: 10px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08); }
        h1, h2 { color: #0056b3; text-align: center; margin-bottom: 20px; }
        h2 { margin-top: 40px; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 12px 15px; border-bottom: 1px solid #dee2e6; text-align: left; vertical-align: middle; }
        th { background-color: #007bff; color: white; position: sticky; top: 0; font-weight: 600; }
        tr:nth-child(even) { background-color: #f8f9fa; }
        tr:hover { background-color: #e9ecef; }
        .error, .no-data { color: #dc3545; text-align: center; margin-top: 20px; font-size: 18px; }
        .positive { color: #dc3545; font-weight: bold; }
        .negative { color: #007bff; font-weight: bold; }
        .home-link { display: block; text-align: center; margin-top: 40px; text-decoration: none; color: #007bff; font-weight: bold; }
        .theme-badge { display: inline-block; padding: 5px 10px; border-radius: 15px; background-color: #6c757d; color: white; font-size: 12px; }
        .related-stocks { list-style: none; padding-left: 0; margin: 0; }
        .related-stocks li { display: inline-block; margin: 2px; }
        .related-stocks a { color: #28a745; text-decoration: none; font-size: 13px; background-color: #eaf6ec; padding: 3px 8px; border-radius: 10px; }
        .related-stocks a:hover { background-color: #d4edda; }
    </style>
</head>
<body>
    <div class="container">
        <h1>미국 주식 현황 및 국내 연관 테마</h1>

        <?php
        // DB 연결
        $config = parse_ini_file(__DIR__ . '/config.ini', true);
        $conn = new mysqli($config['DB']['HOST'], $config['DB']['USER'], $config['DB']['PASSWORD'], $config['DB']['DATABASE'], $config['DB']['PORT']);
        if ($conn->connect_error) {
            die("<p class='error'>DB 연결 실패: " . $conn->connect_error . "</p>");
        }
        $conn->set_charset("utf8mb4");

        // 영문-한글 테마 매핑 (실제 DB 테마에 맞게 수정)
        $theme_map = [
            'Technology' => ['AI & 반도체', '로봇'],
            'Healthcare' => ['헬스케어 & 바이오'],
            'Financial Services' => ['가상자산 & 게임 & NFT'],
            'Consumer Cyclical' => ['2차전지 & 전기차'],
            'Industrials' => ['조선 & 전력 인프라', '우주 & 항공 & 방산'],
            'Communication Services' => ['가상자산 & 게임 & NFT'],
            'Energy' => ['친환경 & 원자력'],
            'Basic Materials' => ['친환경 & 원자력'],
            'Real Estate' => [],
            'Utilities' => ['조선 & 전력 인프라'],
            'Consumer Defensive' => []
        ];

        // --- 주요 지수 ---
        echo "<h2>주요 지수</h2>";
        $sql_indices = "SELECT name, last_price, change_val, percent_change, updated_at FROM us_indices ORDER BY id";
        $result_indices = $conn->query($sql_indices);
        if ($result_indices && $result_indices->num_rows > 0) {
            echo "<table><thead><tr><th>지수명</th><th>현재가</th><th>등락</th><th>등락률</th><th>업데이트</th></tr></thead><tbody>";
            while($row = $result_indices->fetch_assoc()) {
                $rate_class = $row["percent_change"] >= 0 ? 'positive' : 'negative';
                echo "<tr><td>" . htmlspecialchars($row["name"]) . "</td><td>" . number_format($row["last_price"], 2) . "</td><td class='" . $rate_class . "'>" . number_format($row["change_val"], 2) . "</td><td class='" . $rate_class . "'>" . number_format($row["percent_change"], 2) . "%</td><td>" . htmlspecialchars($row["updated_at"]) . "</td></tr>";
            }
            echo "</tbody></table>";
        } else {
            echo "<p class='no-data'>주요 지수 데이터를 찾을 수 없습니다.</p>";
        }

        // --- 상승률 상위 주식 및 연관 국내 테마 ---
        echo "<h2>상승률 상위 주식 및 연관 국내 테마</h2>";
        $sql_stocks = "SELECT ticker, company_name, theme, last_price, change_val, percent_change FROM us_top_stocks ORDER BY percent_change DESC";
        $result_stocks = $conn->query($sql_stocks);
        
        if ($result_stocks && $result_stocks->num_rows > 0) {
            echo "<table><thead><tr><th>티커</th><th>종목명</th><th>테마</th><th>현재가</th><th>등락률</th><th>연관 국내 종목</th></tr></thead><tbody>";
            
            while($row = $result_stocks->fetch_assoc()) {
                $rate_class = $row["percent_change"] >= 0 ? 'positive' : 'negative';
                echo "<tr>";
                echo "<td>" . htmlspecialchars($row["ticker"]) . "</td>";
                echo "<td>" . htmlspecialchars($row["company_name"]) . "</td>";
                echo "<td><span class='theme-badge'>" . htmlspecialchars($row["theme"]) . "</span></td>";
                echo "<td>" . number_format($row["last_price"], 2) . "</td>";
                echo "<td class='" . $rate_class . "'>" . number_format($row["percent_change"], 2) . "%</td>";
                
                echo "<td>";
                $us_theme = $row['theme'];
                if (!empty($us_theme) && isset($theme_map[$us_theme]) && !empty($theme_map[$us_theme])) {
                    $korean_themes = $theme_map[$us_theme];
                    $like_conditions = [];
                    $bind_params = [];
                    foreach ($korean_themes as $theme) {
                        $like_conditions[] = "sn.theme = ?";
                        $bind_params[] = $theme;
                    }
                    $sql_related = "SELECT DISTINCT sn.stock_code FROM stock_news sn WHERE " . implode(' OR ', $like_conditions) . " ORDER BY sn.stock_code LIMIT 10";
                    
                    $stmt = $conn->prepare($sql_related);
                    
                    // bind_param 처리
                    $types = str_repeat('s', count($bind_params));
                    $stmt->bind_param($types, ...$bind_params);

                    $stmt->execute();
                    $related_result = $stmt->get_result();
                    
                    if ($related_result->num_rows > 0) {
                        echo "<ul class='related-stocks'>";
                        while($related_row = $related_result->fetch_assoc()) {
                            echo "<li><a href='display_stock_news.php?stock_code=" . urlencode($related_row['stock_code']) . "'>" . htmlspecialchars($related_row['stock_code']) . "</a></li>";
                        }
                        echo "</ul>";
                    } else {
                        echo "N/A";
                    }
                    $stmt->close();
                } else {
                    echo "N/A";
                }
                echo "</td></tr>";
            }
            echo "</tbody></table>";
        } else {
            echo "<p class='no-data'>상승률 상위 주식 데이터를 찾을 수 없습니다. 'python_modules/get_us_top_30_stocks.py'를 실행해주세요.</p>";
        }

        $conn->close();
        ?>
        <a href="index.php" class="home-link">메인으로 돌아가기</a>
    </div>
</body>
</html>