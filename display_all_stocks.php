<?php
// 에러 리포팅 활성화 (개발용)
ini_set('display_errors', 1);
error_reporting(E_ALL);

// 설정 파일 로드
$config_file = __DIR__ . '/config.ini';
if (!file_exists($config_file)) {
    die("<p class=\"error\">오류: config.ini 파일을 찾을 수 없습니다.</p>");
}
$config = parse_ini_file($config_file, true);
if ($config === false || !isset($config['DB'])) {
    die("<p class=\"error\">오류: config.ini 파일의 [DB] 섹션이 유효하지 않습니다.</p>");
}

// 데이터베이스 연결
try {
    $pdo = new PDO(
        "mysql:host={$config['DB']['HOST']};dbname={$config['DB']['DATABASE']};port={$config['DB']['PORT']};charset=utf8mb4",
        $config['DB']['USER'],
        $config['DB']['PASSWORD'],
        [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        ]
    );
} catch (PDOException $e) {
    die("<p class=\"error\">데이터베이스 연결 실패: " . $e->getMessage() . "</p>");
}

// --- 데이터 조회 및 처리 ---

// 1. 전체 종목 통계 계산
$stats_sql = "
    SELECT 
        SUM(CASE WHEN CAST(REPLACE(REPLACE(REPLACE(current_price, ',', ''), '+', ''), '-', '') AS DECIMAL(20,2)) > CAST(REPLACE(REPLACE(REPLACE(previous_day_closing_price, ',', ''), '+', ''), '-', '') AS DECIMAL(20,2)) THEN 1 ELSE 0 END) as rising_count,
        SUM(CASE WHEN CAST(REPLACE(REPLACE(REPLACE(current_price, ',', ''), '+', ''), '-', '') AS DECIMAL(20,2)) < CAST(REPLACE(REPLACE(REPLACE(previous_day_closing_price, ',', ''), '+', ''), '-', '') AS DECIMAL(20,2)) THEN 1 ELSE 0 END) as falling_count
    FROM stock_details
    WHERE previous_day_closing_price IS NOT NULL 
      AND current_price IS NOT NULL
      AND previous_day_closing_price REGEXP '^[+-]?[0-9,.]+$' 
      AND current_price REGEXP '^[+-]?[0-9,.]+$'
";
$stats = $pdo->query($stats_sql)->fetch();

// 2. 페이징 설정
$page = isset($_GET['page']) && is_numeric($_GET['page']) ? (int)$_GET['page'] : 1;
$limit = 100;
$offset = ($page - 1) * $limit;
$total_rows = $pdo->query('SELECT COUNT(*) FROM stock_details')->fetchColumn();
$total_pages = ceil($total_rows / $limit);

// 3. 메인 데이터 조회 (최신 뉴스는 별도 조회)
$main_sql = "
    SELECT 
        stock_code, stock_name, market, current_price, previous_day_closing_price, circulating_shares
    FROM stock_details
    ORDER BY stock_name ASC
    LIMIT :limit OFFSET :offset
";
$stmt = $pdo->prepare($main_sql);
$stmt->bindValue(':limit', $limit, PDO::PARAM_INT);
$stmt->bindValue(':offset', $offset, PDO::PARAM_INT);
$stmt->execute();
$stocks = $stmt->fetchAll();

// 4. 최신 뉴스 조회 (조회된 종목에 대해서만)
$news_data = [];
if (!empty($stocks)) {
    $stock_codes = array_column($stocks, 'stock_code');
    $placeholders = implode(',', array_fill(0, count($stock_codes), '?'));
    
    $news_sql = "
        SELECT stock_code, title, link
        FROM (
            SELECT 
                stock_code, title, link,
                ROW_NUMBER() OVER(PARTITION BY stock_code ORDER BY pub_date DESC) as rn
            FROM stock_news
            WHERE stock_code IN ($placeholders)
        ) as latest_news
        WHERE rn = 1
    ";
    $news_stmt = $pdo->prepare($news_sql);
    $news_stmt->execute($stock_codes);
    $news_data_raw = $news_stmt->fetchAll(PDO::FETCH_GROUP);
    
    // PDO::FETCH_GROUP은 각 키에 대해 배열을 반환하므로, 첫 번째 항목만 사용하도록 데이터를 재구성합니다.
    foreach ($news_data_raw as $code => $news_items) {
        $news_data[$code] = $news_items[0];
    }
}

?>
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>코스피/코스닥 전체 종목</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 20px; background-color: #f8f9fa; }
        .container { max-width: 95%; margin: auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { text-align: center; color: #0056b3; }
        .subtitle { text-align: center; color: #666; margin-bottom: 20px; }
        #searchInput { width: 100%; padding: 10px; margin-bottom: 10px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
        .search-results { font-size: 14px; color: #666; margin-bottom: 10px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 10px; border: 1px solid #ddd; text-align: left; white-space: nowrap; }
        th { background-color: #007bff; color: white; position: sticky; top: 0; }
        tr:nth-child(even) { background-color: #f2f2f2; }
        .positive { color: red; }
        .negative { color: blue; }
        .news-title { white-space: normal; max-width: 250px; }
        .pagination { text-align: center; margin-top: 20px; }
        .pagination a, .pagination strong { padding: 8px 12px; margin: 0 2px; border: 1px solid #ddd; text-decoration: none; color: #007bff; }
        .pagination strong { background-color: #007bff; color: white; border-color: #007bff; }
        .home-link { position: fixed; bottom: 20px; right: 20px; background-color: #007bff; color: white; padding: 10px 15px; border-radius: 5px; text-decoration: none; box-shadow: 0 2px 4px rgba(0,0,0,0.2); }
    </style>
</head>
<body>
    <div class="container">
        <h1>코스피/코스닥 전체 종목</h1>
        <p class="subtitle">
            상승: <span class="positive"><?= $stats['rising_count'] ?? 0 ?></span> / 
            하락: <span class="negative"><?= $stats['falling_count'] ?? 0 ?></span> / 
            전체: <?= $total_rows ?>
        </p>
        <input type="text" id="searchInput" onkeyup="searchTable()" placeholder="실시간 검색: 종목 코드, 종목명 등...">
        <div id="searchResults" class="search-results"></div>

        <table id="stockTable">
            <thead>
                <tr><th>종목코드</th><th>종목명</th><th>시장</th><th>현재가</th><th>등락률</th><th>전일종가</th><th>유통주수</th><th style="width: 250px;">최신뉴스</th></tr>
            </thead>
            <tbody>
                <?php if (!empty($stocks)): ?>
                    <?php foreach ($stocks as $row): ?>
                        <?php
                        $current_price = (float)str_replace([',', '+', '-'], '', $row["current_price"]);
                        $prev_price = (float)str_replace([',', '+', '-'], '', $row["previous_day_closing_price"]);
                        $rate_str = 'N/A';
                        $rate_class = '';
                        if ($prev_price != 0) {
                            $rate = (($current_price - $prev_price) / $prev_price) * 100;
                            $rate_str = number_format($rate, 2) . '%';
                            if ($rate > 0) $rate_class = 'positive';
                            if ($rate < 0) $rate_class = 'negative';
                        }
                        ?>
                        <tr>
                            <td><?= htmlspecialchars($row["stock_code"]) ?></td>
                            <td><?= htmlspecialchars($row["stock_name"]) ?></td>
                            <td><?= htmlspecialchars($row["market"]) ?></td>
                            <td><?= number_format($current_price) ?></td>
                            <td class="<?= $rate_class ?>"><?= $rate_str ?></td>
                            <td><?= number_format($prev_price) ?></td>
                            <td><?= is_numeric($row["circulating_shares"]) ? number_format($row["circulating_shares"]) : 'N/A' ?></td>
                            <td class="news-title">
                                <?php if (isset($news_data[$row['stock_code']])): ?>
                                    <a href="<?= htmlspecialchars($news_data[$row['stock_code']]['link']) ?>" target="_blank"><?= htmlspecialchars($news_data[$row['stock_code']]['title']) ?></a>
                                <?php else: ?>
                                    N/A
                                <?php endif; ?>
                            </td>
                        </tr>
                    <?php endforeach; ?>
                <?php else: ?>
                    <tr><td colspan="8" style="text-align:center;">표시할 데이터가 없습니다.</td></tr>
                <?php endif; ?>
            </tbody>
        </table>

        <div class="pagination">
            <?php for ($i = 1; $i <= $total_pages; $i++):
                if ($i == $page):
                    echo "<strong>{$i}</strong>";
                else:
                    echo "<a href=\" ?page= ". $i . " \">{$i}</a>";
                endif;
            endfor; ?>
        </div>
    </div>
    <a href="index.php" class="home-link">메인</a>
    <script>
        function searchTable() {
            const input = document.getElementById("searchInput");
            const filter = input.value.toUpperCase();
            const table = document.getElementById("stockTable");
            const tr = table.getElementsByTagName("tr");
            let visibleCount = 0;

            for (let i = 1; i < tr.length; i++) {
                let found = Array.from(tr[i].getElementsByTagName("td")).some(td => 
                    td.textContent.toUpperCase().includes(filter)
                );
                tr[i].style.display = found ? "" : "none";
                if (found) visibleCount++;
            }
            document.getElementById("searchResults").textContent = filter ? `검색 결과: ${visibleCount}개` : '';
        }
    </script>
</body>
</html>