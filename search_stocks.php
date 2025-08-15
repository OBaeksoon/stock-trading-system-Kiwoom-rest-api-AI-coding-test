<?php
header('Content-Type: application/json');

// 에러 리포팅 활성화 (개발용)
ini_set('display_errors', 1);
error_reporting(E_ALL);

// 로그 파일 경로 설정
define('LOG_FILE', __DIR__ . '/../logs/search_stocks.log');

require_once __DIR__ . '/includes/log_utils.php';

write_log("search_stocks.php 스크립트 시작");

require_once 'db_connection.php';
write_log("db_connection.php 로드 완료.");

$searchTerm = isset($_GET['term']) ? trim($_GET['term']) : '';
write_log("검색어 수신: " . $searchTerm);

if (empty($searchTerm)) {
    write_log("검색어가 비어 있습니다. 빈 배열 반환.");
    echo json_encode([]);
    exit;
}

try {
    $pdo = get_db_connection();
    write_log("데이터베이스 연결 성공.");
    // 'stocks' 테이블에서 'stock_name' 또는 'stock_code'가 검색어로 시작하는 항목 검색
    // 참고: stocks 테이블과 stock_name, stock_code 컬럼이 있어야 합니다.
    $sql = "
        SELECT stock_name, stock_code
        FROM stock_details  -- 'stocks' 대신 'stock_details' 테이블 사용 (프로젝트 개요에 따름)
        WHERE stock_name LIKE :term OR stock_code LIKE :term
        LIMIT 10
    ";
    write_log("SQL 쿼리 실행: " . $sql . " (검색어: " . $searchTerm . "%)");
    
    $stmt = $pdo->prepare($sql);
    $stmt->execute(['term' => $searchTerm . '%']);
    $suggestions = $stmt->fetchAll();
    write_log("검색 결과 성공. 조회된 제안 수: " . count($suggestions));

} catch (\PDOException $e) {
    http_response_code(500);
    write_log("검색 중 데이터베이스 오류: " . $e->getMessage());
    echo json_encode(['error' => '검색 중 오류가 발생했습니다.']);
    exit;
}

echo json_encode($suggestions);
write_log("search_stocks.php 스크립트 종료");
?>