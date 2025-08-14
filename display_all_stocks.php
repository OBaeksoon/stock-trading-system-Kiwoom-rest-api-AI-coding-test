<?php
// 에러 리포팅 활성화 (개발용)
ini_set('display_errors', 1);
error_reporting(E_ALL);

// 로그 파일 경로 설정
define('LOG_FILE', __DIR__ . '/../logs/display_all_stocks.log');

function write_log($message) {
    error_log(date('[Y-m-d H:i:s]') . ' ' . $message . PHP_EOL, 3, LOG_FILE);
}

write_log("display_all_stocks.php 스크립트 시작");

// 설정 파일 로드
$config_file = __DIR__ . '/config.ini';
if (!file_exists($config_file)) {
    write_log("오류: config.ini 파일을 찾을 수 없습니다.");
    die("<p class=\"error\">오류: config.ini 파일을 찾을 수 없습니다.</p>");
}
$config = parse_ini_file($config_file, true);
if ($config === false || !isset($config['DB'])) {
    write_log("오류: config.ini 파일의 [DB] 섹션이 유효하지 않습니다.");
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
    write_log("데이터베이스 연결 성공.");
} catch (PDOException $e) {
    write_log("데이터베이스 연결 실패: " . $e->getMessage());
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
try {
    $stats = $pdo->query($stats_sql)->fetch();
    write_log("종목 통계 조회 성공: " . json_encode($stats));
} catch (PDOException $e) {
    write_log("종목 통계 조회 실패: " . $e->getMessage());
    $stats = ['rising_count' => 0, 'falling_count' => 0]; // 오류 시 기본값 설정
}


// 2. 페이징 설정
$page = isset($_GET['page']) && is_numeric($_GET['page']) ? (int)$_GET['page'] : 1;
$limit = 100;
$offset = ($page - 1) * $limit;
try {
    $total_rows = $pdo->query('SELECT COUNT(*) FROM stock_details')->fetchColumn();
    write_log("총 종목 수 조회 성공: " . $total_rows);
} catch (PDOException $e) {
    write_log("총 종목 수 조회 실패: " . $e->getMessage());
    $total_rows = 0; // 오류 시 기본값 설정
}
$total_pages = ceil($total_rows / $limit);

// 3. 메인 데이터 조회 (최신 뉴스는 별도 조회)
$main_sql = "
    SELECT 
        stock_code, stock_name, market, current_price, previous_day_closing_price, circulating_shares
    FROM stock_details
    ORDER BY stock_name ASC
    LIMIT :limit OFFSET :offset
";
try {
    $stmt = $pdo->prepare($main_sql);
    $stmt->bindValue(':limit', $limit, PDO::PARAM_INT);
    $stmt->bindValue(':offset', $offset, PDO::PARAM_INT);
    $stmt->execute();
    $stocks = $stmt->fetchAll();
    write_log("메인 종목 데이터 조회 성공. 조회된 종목 수: " . count($stocks));
} catch (PDOException $e) {
    write_log("메인 종목 데이터 조회 실패: " . $e->getMessage());
    $stocks = []; // 오류 시 빈 배열 설정
}


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
    try {
        $news_stmt = $pdo->prepare($news_sql);
        $news_stmt->execute($stock_codes);
        $news_data_raw = $news_stmt->fetchAll(PDO::FETCH_GROUP);
        
        foreach ($news_data_raw as $code => $news_items) {
            $news_data[$code] = $news_items[0];
        }
        write_log("뉴스 데이터 조회 성공. 조회된 뉴스 수: " . count($news_data));
    } catch (PDOException $e) {
        write_log("뉴스 데이터 조회 실패: " . $e->getMessage());
        $news_data = []; // 오류 시 빈 배열 설정
    }
} else {
    write_log("조회된 종목이 없어 뉴스 데이터를 조회하지 않습니다.");
}

write_log("display_all_stocks.php 스크립트 종료");
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
            상승: <span class="positive"><?php echo number_format($stats['rising_count'] ?? 0); ?></span> | 
            하락: <span class="negative"><?php echo number_format($stats['falling_count'] ?? 0); ?></span>
        </p>
        
        <input type="text" id="searchInput" onkeyup="filterTable()" placeholder="종목명 또는 코드로 검색...">

        <div style="overflow-x:auto;">
            <table id="stocksTable">
                <thead>
                    <tr>
                        <th>종목코드</th>
                        <th>종목명</th>
                        <th>시장</th>
                        <th>현재가</th>
                        <th>전일비</th>
                        <th>등락률</th>
                        <th>유통주식수</th>
                        <th>최신 뉴스</th>
                    </tr>
                </thead>
                <tbody>
                    <?php if (!empty($stocks)): ?>
                        <?php foreach ($stocks as $stock): ?>
                            <?php
                                // 데이터 클리닝 및 숫자 변환
                                $current_price_val = is_numeric(str_replace(',', '', $stock['current_price'])) ? (float)str_replace(',', '', $stock['current_price']) : 0;
                                $prev_price_val = is_numeric(str_replace(',', '', $stock['previous_day_closing_price'])) ? (float)str_replace(',', '', $stock['previous_day_closing_price']) : 0;
                                
                                $change = $current_price_val - $prev_price_val;
                                $change_rate = ($prev_price_val != 0) ? ($change / $prev_price_val) * 100 : 0;
                                
                                $change_class = $change > 0 ? 'positive' : ($change < 0 ? 'negative' : '');
                                $change_symbol = $change > 0 ? '▲' : ($change < 0 ? '▼' : '');
                            ?>
                            <tr>
                                <td><?php echo htmlspecialchars($stock['stock_code']); ?></td>
                                <td><?php echo htmlspecialchars($stock['stock_name']); ?></td>
                                <td><?php echo htmlspecialchars($stock['market']); ?></td>
                                <td class="<?php echo $change_class; ?>"><?php echo htmlspecialchars($stock['current_price']); ?></td>
                                <td class="<?php echo $change_class; ?>"><?php echo $change_symbol . ' ' . number_format(abs($change)); ?></td>
                                <td class="<?php echo $change_class; ?>"><?php echo number_format($change_rate, 2); ?>%</td>
                                <td><?php echo number_format($stock['circulating_shares']); ?></td>
                                <td class="news-title">
                                    <?php if (isset($news_data[$stock['stock_code']])): ?>
                                        <a href="<?php echo htmlspecialchars($news_data[$stock['stock_code']]['link']); ?>" target="_blank">
                                            <?php echo htmlspecialchars($news_data[$stock['stock_code']]['title']); ?>
                                        </a>
                                    <?php else: ?>
                                        -
                                    <?php endif; ?>
                                </td>
                            </tr>
                        <?php endforeach; ?>
                    <?php else: ?>
                        <tr>
                            <td colspan="8" style="text-align:center;">표시할 데이터가 없습니다.</td>
                        </tr>
                    <?php endif; ?>
                </tbody>
            </table>
        </div>

        <div class="pagination">
            <?php if ($total_pages > 1): ?>
                <?php for ($i = 1; $i <= $total_pages; $i++): ?>
                    <?php if ($i == $page): ?>
                        <strong><?php echo $i; ?></strong>
                    <?php else: ?>
                        <a href="?page=<?php echo $i; ?>"><?php echo $i; ?></a>
                    <?php endif; ?>
                <?php endfor; ?>
            <?php endif; ?>
        </div>
    </div>

    <a href="index.php" class="home-link">메인</a>

    <script>
    function filterTable() {
        const input = document.getElementById("searchInput");
        const filter = input.value.toUpperCase();
        const table = document.getElementById("stocksTable");
        const tr = table.getElementsByTagName("tr");

        for (let i = 1; i < tr.length; i++) { // 1부터 시작하여 aheade 건너뛰기
            let td1 = tr[i].getElementsByTagName("td")[0]; // 종목코드
            let td2 = tr[i].getElementsByTagName("td")[1]; // 종목명
            if (td1 || td2) {
                if (td1.textContent.toUpperCase().indexOf(filter) > -1 || td2.textContent.toUpperCase().indexOf(filter) > -1) {
                    tr[i].style.display = "";
                } else {
                    tr[i].style.display = "none";
                }
            }       
        }
    }
    </script>
</body>
</html>