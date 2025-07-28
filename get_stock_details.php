<?php
header('Content-Type: application/json');

// config.ini에서 데이터베이스 설정 읽기
$config_file = __DIR__ . '/config.ini';

if (!file_exists($config_file)) {
    echo json_encode(['error' => 'config.ini 파일을 찾을 수 없습니다.']);
    exit();
}

$config = parse_ini_file($config_file, true);

if (!$config || !isset($config['DB'])) {
    echo json_encode(['error' => 'config.ini 파일에 [DB] 섹션이 없습니다.']);
    exit();
}

$servername = $config['DB']['HOST'];
$username = $config['DB']['USER'];
$password = $config['DB']['PASSWORD'];
$dbname = $config['DB']['DATABASE'];
$port = $config['DB']['PORT'];

// Create connection
$conn = new mysqli($servername, $username, $password, $dbname, $port);

// Check connection
if ($conn->connect_error) {
    echo json_encode(['error' => '데이터베이스 연결 실패: ' . $conn->connect_error]);
    exit();
}

$searchTerm = $_GET['search'] ?? '';

if (empty($searchTerm)) {
    echo json_encode(['error' => '검색어를 입력해주세요.']);
    $conn->close();
    exit();
}

// 종목 코드 또는 종목명으로 검색
$stmt = $conn->prepare("SELECT stock_code, stock_name, market, current_price, closing_price, previous_day_closing_price, circulating_shares FROM stock_details WHERE stock_code = ? OR stock_name LIKE ?");
$searchLike = "%" . $searchTerm . "%";
$stmt->bind_param("ss", $searchTerm, $searchLike);
$stmt->execute();
$result = $stmt->get_result();

$stockDetails = null;
if ($result->num_rows > 0) {
    $row = $result->fetch_assoc();
    $stockDetails = [
        'stock_code' => $row['stock_code'],
        'stock_name' => $row['stock_name'],
        'market' => $row['market'],
        'current_price' => $row['current_price'],
        'closing_price' => $row['closing_price'],
        'previous_day_closing_price' => $row['previous_day_closing_price'],
        'circulating_shares' => $row['circulating_shares']
    ];
}

echo json_encode($stockDetails);

$stmt->close();
$conn->close();
?>