<?php
header('Content-Type: application/json');

require_once 'db_connection.php';

$searchTerm = $_GET['search'] ?? '';

if (empty($searchTerm)) {
    echo json_encode(['error' => '검색어를 입력해주세요.']);
    exit();
}

try {
    $pdo = get_db_connection();

    // 종목 코드 또는 종목명으로 검색
    $stmt = $pdo->prepare("SELECT stock_code, stock_name, market, current_price, closing_price, previous_day_closing_price, circulating_shares FROM stock_details WHERE stock_code = ? OR stock_name LIKE ?");
    $searchLike = "%" . $searchTerm . "%";
    $stmt->execute([$searchTerm, $searchLike]);
    
    $stockDetails = $stmt->fetch();

    if (!$stockDetails) {
        $stockDetails = null;
    }

    echo json_encode($stockDetails);

} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode(['error' => '데이터베이스 조회 중 오류가 발생했습니다.']);
}
?>