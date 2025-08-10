<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>실시간 상승률 30위 종목</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            color: #333;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
        }
        .header h1 {
            color: white;
            font-size: 2.5em;
            font-weight: 300;
            text-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }
        .home-btn {
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(255,255,255,0.2);
            color: white;
            padding: 12px 24px;
            border: 2px solid rgba(255,255,255,0.3);
            border-radius: 25px;
            text-decoration: none;
            font-weight: 500;
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
            z-index: 1000;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }
        .home-btn:hover {
            background: rgba(255,255,255,0.3);
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0,0,0,0.3);
        }
        .container {
            background: rgba(255,255,255,0.95);
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            backdrop-filter: blur(10px);
            overflow: hidden;
        }
        .stats-bar {
            background: linear-gradient(45deg, #4CAF50, #45a049);
            color: white;
            padding: 20px;
            text-align: center;
            font-size: 1.1em;
            font-weight: 500;
        }
        .stock-grid {
            display: grid;
            gap: 20px;
            padding: 30px;
        }
        .stock-card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.08);
            border: 1px solid rgba(0,0,0,0.05);
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        .stock-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 35px rgba(0,0,0,0.15);
        }
        .stock-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(45deg, #667eea, #764ba2);
        }
        .stock-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .stock-rank {
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 1.1em;
        }
        .stock-name {
            flex: 1;
            margin-left: 15px;
        }
        .stock-name h3 {
            color: #2c3e50;
            font-size: 1.3em;
            margin-bottom: 5px;
        }
        .stock-code {
            color: #7f8c8d;
            font-size: 0.9em;
        }
        .stock-metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .metric {
            text-align: center;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 10px;
        }
        .metric-label {
            font-size: 0.8em;
            color: #6c757d;
            margin-bottom: 5px;
        }
        .metric-value {
            font-size: 1.1em;
            font-weight: bold;
        }
        .price { color: #2c3e50; }
        .change { color: #e74c3c; }
        .volume { color: #3498db; }
        .news-section {
            border-top: 1px solid #ecf0f1;
            padding-top: 20px;
        }
        .news-title {
            color: #34495e;
            font-size: 1.1em;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
        }
        .news-title::before {
            content: '📰';
            margin-right: 8px;
        }
        .news-list {
            list-style: none;
        }
        .news-item {
            padding: 12px 0;
            border-bottom: 1px solid #f1f2f6;
        }
        .news-item:last-child {
            border-bottom: none;
        }
        .news-link {
            color: #2c3e50;
            text-decoration: none;
            font-weight: 500;
            line-height: 1.4;
            transition: color 0.3s ease;
        }
        .news-link:hover {
            color: #667eea;
        }
        .theme-tag {
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 0.7em;
            margin-left: 8px;
            font-weight: 500;
        }
        .news-date {
            color: #95a5a6;
            font-size: 0.8em;
            margin-left: 8px;
        }
        .no-news {
            color: #95a5a6;
            font-style: italic;
            text-align: center;
            padding: 20px;
        }
        .update-section {
            background: linear-gradient(45deg, #f8f9fa, #e9ecef);
            margin: 30px;
            padding: 25px;
            border-radius: 15px;
            text-align: center;
        }
        .update-btn {
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            padding: 12px 30px;
            border: none;
            border-radius: 25px;
            font-size: 1em;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        }
        .update-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
        }
        .error {
            background: #fee;
            color: #c33;
            padding: 15px;
            border-radius: 10px;
            margin: 20px;
            text-align: center;
        }
        @media (max-width: 768px) {
            .header h1 { font-size: 2em; }
            .stock-metrics { grid-template-columns: 1fr; }
            .stock-header { flex-direction: column; text-align: center; }
            .stock-name { margin-left: 0; margin-top: 10px; }
        }
    </style>
</head>
<body>
    <a href="index.php" class="home-btn">🏠 메인으로</a>
    <div class="header">
        <h1>📈 실시간 상승률 30위</h1>
    </div>
    <div class="container">
        <?php
        // 데이터베이스 연결
        $config = parse_ini_file('config.ini', true); // 섹션을 파싱하도록 true 추가
        $conn = new mysqli(
            $config['DB']['HOST'],
            $config['DB']['USER'],
            $config['DB']['PASSWORD'],
            $config['DB']['DATABASE'],
            $config['DB']['PORT']
        );
        if ($conn->connect_error) {
            die("Connection failed: " . $conn->connect_error);
        }
        $conn->set_charset("utf8mb4");

        // [수정된 부분 1] SQL 쿼리에서 'fluctuation_rate'를 'fluctuation_rate'로 변경
        $sql = "
            SELECT
                t.rank, t.stock_code, t.stock_name, t.current_price, t.fluctuation_rate, t.volume, t.updated_at,
                n.title, n.link, n.pub_date, n.theme
            FROM
                top_30_rising_stocks t
            LEFT JOIN (
                SELECT
                    stock_code, title, link, pub_date, theme,
                    ROW_NUMBER() OVER(PARTITION BY stock_code ORDER BY pub_date DESC) as rn
                FROM
                    stock_news
            ) n ON SUBSTRING_INDEX(t.stock_code, '_', 1) = n.stock_code AND n.rn <= 3
            WHERE t.rank > 0
            ORDER BY
                t.rank ASC, n.pub_date DESC
        ";

        $result = $conn->query($sql);

        if (!$result) {
            echo "<p class='error'>SQL Error: " . $conn->error . "</p>";
        }

        if ($result && $result->num_rows > 0) {
            $stocks = [];
            while($row = $result->fetch_assoc()) {
                $stock_code = $row['stock_code'];
                if (!isset($stocks[$stock_code])) {
                    $stocks[$stock_code] = [
                        'rank' => $row['rank'],
                        'stock_code' => $row['stock_code'],
                        'stock_name' => $row['stock_name'],
                        'current_price' => $row['current_price'],
                        'fluctuation_rate' => $row['fluctuation_rate'], // [수정된 부분 2] 배열 키를 'fluctuation_rate'로 변경
                        'volume' => $row['volume'],
                        'updated_at' => $row['updated_at'],
                        'news' => []
                    ];
                }
                if ($row['title']) {
                    $stocks[$stock_code]['news'][] = [
                        'title' => $row['title'],
                        'link' => $row['link'],
                        'theme' => $row['theme'],
                        'pub_date' => $row['pub_date']
                    ];
                }
            }

            $first_stock = reset($stocks);
            echo "<div class='stats-bar'>📊 총 " . count($stocks) . "개 종목 | 마지막 업데이트 " . date('Y-m-d H:i', strtotime($first_stock['updated_at'])) . "</div>";
            echo "<div class='stock-grid'>";

            foreach ($stocks as $stock) {
                echo "<div class='stock-card'>";
                echo "<div class='stock-header'>";
                echo "<div class='stock-rank'>" . htmlspecialchars($stock['rank']) . "</div>";
                echo "<div class='stock-name'>";
                echo "<h3>" . htmlspecialchars($stock['stock_name']) . "</h3>";
                echo "<div class='stock-code'>" . htmlspecialchars($stock['stock_code']) . "</div>";
                echo "</div>";
                echo "</div>";

                echo "<div class='stock-metrics'>";
                echo "<div class='metric'><div class='metric-label'>현재가</div><div class='metric-value price'>" . number_format(intval($stock['current_price'])) . "원</div></div>";
                // [수정된 부분 3] 출력 부분에서 'fluctuation_rate'를 'fluctuation_rate'로 변경
                echo "<div class='metric'><div class='metric-label'>등락률</div><div class='metric-value change'>" . ($stock['fluctuation_rate'] >= 0 ? '+' : '') . htmlspecialchars($stock['fluctuation_rate']) . "%</div></div>";
                echo "<div class='metric'><div class='metric-label'>거래량</div><div class='metric-value volume'>" . number_format(intval($stock['volume'])) . "</div></div>";
                echo "</div>";

                echo "<div class='news-section'>";
                if (!empty($stock['news'])) {
                    echo "<div class='news-title'>관련 뉴스</div>";
                    echo "<ul class='news-list'>";
                    foreach ($stock['news'] as $news) {
                        echo "<li class='news-item'>";
                        echo "<a href='" . htmlspecialchars($news['link']) . "' target='_blank' class='news-link'>";
                        echo htmlspecialchars($news['title']);
                        echo "</a>";
                        if ($news['theme']) {
                            echo "<span class='theme-tag'>" . htmlspecialchars($news['theme']) . "</span>";
                        }
                        if ($news['pub_date']) {
                            echo "<span class='news-date'>" . date('m-d H:i', strtotime($news['pub_date'])) . "</span>";
                        }
                        echo "</li>";
                    }
                    echo "</ul>";
                } else {
                    echo "<div class='no-news'>📭 관련 뉴스가 없습니다</div>";
                }
                echo "</div>";
                echo "</div>";
            }
            echo "</div>";
        } else {
            echo "<p class='error'>장중에 데이터가 업데이트됩니다.</p>";
        }

        $conn->close();
        ?>
        
        <div class="update-section">
            <h3 style="margin-bottom: 15px; color: #2c3e50;">🔄 뉴스 데이터 업데이트</h3>
            <p style="margin-bottom: 20px; color: #6c757d;">관련 뉴스가 표시되지 않는 경우 최신 뉴스를 수집할 수 있습니다</p>
            <button onclick="updateNews()" class="update-btn">뉴스 업데이트 시작</button>
            <div id="updateStatus" style="margin-top: 15px;"></div>
        </div>
        
        <script>
        function updateNews() {
            document.getElementById('updateStatus').innerHTML = '<p style="color: #0056b3;">뉴스를 업데이트 중입니다. 잠시만 기다려주세요...</p>';
            
            fetch('update_news.php')
                .then(response => response.text())
                .then(data => {
                    document.getElementById('updateStatus').innerHTML = '<p style="color: green;">뉴스 업데이트가 완료되었습니다. 페이지를 새로고침하세요.</p>';
                })
                .catch(error => {
                    document.getElementById('updateStatus').innerHTML = '<p style="color: red;">업데이트 중 오류가 발생했습니다.</p>';
                });
        }
        </script>
    </div>
</body>
</html>