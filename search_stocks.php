<?php
// config.ini 파일의 DB 정보를 사용하여 데이터베이스에 연결합니다.
header('Content-Type: application/json');

// config.ini 파일에서 데이터베이스 설정을 읽어옵니다.
$config = parse_ini_file('config.ini', true);

// --- 데이터베이스 연결 설정 ---
$host = $config['DB']['HOST'];
$db   = $config['DB']['DATABASE'];
$user = $config['DB']['USER'];
$pass = $config['DB']['PASSWORD'];
$port = $config['DB']['PORT'];
$charset = 'utf8mb4';

$dsn = "mysql:host=$host;port=$port;dbname=$db;charset=$charset";
$options = [
    PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
    PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    PDO::ATTR_EMULATE_PREPARES   => false,
];

try {
    $pdo = new PDO($dsn, $user, $pass, $options);
} catch (\PDOException $e) {
    // 데이터베이스 연결 실패 시 에러 메시지를 JSON으로 반환
    http_response_code(500); // 서버 에러 상태 코드
    echo json_encode(['error' => '데이터베이스 연결에 실패했습니다.']);
    exit;
}
// --- 연결 설정 끝 ---

$searchTerm = isset($_GET['term']) ? $_GET['term'] : '';

if (empty($searchTerm)) {
    echo json_encode([]);
    exit;
}

try {
    // 'stocks' 테이블에서 'stock_name' 또는 'stock_code'가 검색어로 시작하는 항목 검색
    // 참고: stocks 테이블과 stock_name, stock_code 컬럼이 있어야 합니다.
    $stmt = $pdo->prepare("
        SELECT stock_name, stock_code
        FROM stocks
        WHERE stock_name LIKE :term OR stock_code LIKE :term
        LIMIT 10
    ");
    
    $stmt->execute(['term' => $searchTerm . '%']);
    $suggestions = $stmt->fetchAll();

} catch (\PDOException $e) {
    http_response_code(500);
    // 실제 운영 환경에서는 에러를 로그 파일에 기록하는 것이 좋습니다.
    // error_log($e->getMessage());
    echo json_encode(['error' => '검색 중 오류가 발생했습니다.']);
    exit;
}

echo json_encode($suggestions);
?>