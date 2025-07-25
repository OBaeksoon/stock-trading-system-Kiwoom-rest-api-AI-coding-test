<?php
// Set a longer timeout for this script as fetching all stocks from DB might take time for large datasets.
set_time_limit(120); // 2 minutes, adjusted from 5 minutes as Python execution is removed.

// 이 PHP 스크립트는 데이터베이스에서 종목 정보를 읽어와 HTML로 출력합니다.
// 파이썬 스크립트(get_all_stocks.py)는 별도의 스케줄러(예: cron job)를 통해
// 주기적으로 실행되어 데이터베이스를 업데이트해야 합니다.
// 웹 요청 시마다 파이썬 스크립트를 실행하는 것은 비효율적이며, API 요청 제한에 걸릴 수 있습니다.

$search_term = $_GET['search'] ?? '';
$db_file = '/home/stock/public_html/stock_data.db'; // stock_data.db 파일의 실제 경로

$data = [];
$error_message = '';

try {
    $pdo = new PDO('sqlite:' . $db_file);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $pdo->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC); // 결과를 연관 배열로 가져오기

    $sql = "SELECT stk_cd, stk_nm, cur_prc, cmpr_yd, flu_rt, trde_qty, trde_amt FROM korean_stock_list";
    $params = [];

    if (!empty($search_term)) {
        $sql .= " WHERE stk_nm LIKE ? OR stk_cd LIKE ?";
        $params[] = '%' . $search_term . '%';
        $params[] = '%' . $search_term . '%';
    }

    $sql .= " ORDER BY trde_amt DESC"; // 거래대금 기준으로 내림차순 정렬

    $stmt = $pdo->prepare($sql);
    $stmt->execute($params);
    $data = $stmt->fetchAll();

} catch (PDOException $e) {
    // 데이터베이스 연결 또는 쿼리 오류 발생 시
    $error_message = "데이터베이스 연결 또는 쿼리 오류: " . htmlspecialchars($e->getMessage());
    // 서버 로그에도 기록하여 디버깅에 활용
    error_log("Database error in fetch_all_stocks.php: " . $e->getMessage());
} catch (Exception $e) {
    // 기타 예상치 못한 오류 발생 시
    $error_message = "예상치 못한 오류가 발생했습니다: " . htmlspecialchars($e->getMessage());
    error_log("Unexpected error in fetch_all_stocks.php: " . $e->getMessage());
}

// 데이터 표시
if (!empty($error_message)) {
    // 오류가 있을 경우 오류 메시지 출력
    echo "<p class=\"error\">" . $error_message . "</p>";
} elseif (!empty($data)) {
    // 데이터가 있을 경우 테이블로 출력
    if (!empty($search_term)) {
        echo "<p>'" . htmlspecialchars($search_term) . "' 검색 결과: 총 " . count($data) . "개의 종목을 찾았습니다.</p>";
    } else {
        echo "<p>데이터베이스에서 총 " . count($data) . "개의 종목을 불러왔습니다. (거래대금 순 정렬)</p>";
    }
    
    echo "<table>";
    echo "<thead><tr><th>종목코드</th><th>종목명</th><th>현재가</th><th>전일대비</th><th>등락률</th><th>거래량</th><th>거래대금</th></tr></thead>";
    echo "<tbody>";
    foreach ($data as $stock) {
        echo "<tr>";
        echo "<td>" . htmlspecialchars($stock['stk_cd'] ?? '') . "</td>";
        echo "<td>" . htmlspecialchars($stock['stk_nm'] ?? '') . "</td>";
        echo "<td>" . htmlspecialchars(number_format($stock['cur_prc'] ?? 0)) . "</td>";
        echo "<td>" . htmlspecialchars(number_format($stock['cmpr_yd'] ?? 0)) . "</td>";
        echo "<td>" . htmlspecialchars($stock['flu_rt'] ?? '') . "</td>";
        echo "<td>" . htmlspecialchars(number_format($stock['trde_qty'] ?? 0)) . "</td>";
        echo "<td>" . htmlspecialchars(number_format($stock['trde_amt'] ?? 0)) . "</td>";
        echo "</tr>";
    }
    echo "</tbody></table>";
} else {
    // 데이터가 없고 검색어도 없는 경우 (초기 로딩 시 데이터가 없는 경우)
    if (!empty($search_term)) {
        echo "<p>'" . htmlspecialchars($search_term) . "'에 대한 검색 결과가 없습니다.</p>";
    } else {
        echo "<p class=\"info\">데이터베이스에 조회된 종목이 없습니다. 파이썬 스크립트(get_all_stocks.py)를 실행하여 데이터베이스를 업데이트해주세요.</p>";
    }
}
?>