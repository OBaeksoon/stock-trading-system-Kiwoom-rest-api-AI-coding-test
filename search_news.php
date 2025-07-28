<?php
$config_file = __DIR__ . '/config.ini';
if (!file_exists($config_file)) {
    echo '<p class="message">설정 파일을 찾을 수 없습니다.</p>';
    exit;
}

$config = parse_ini_file($config_file, true);
$conn = new mysqli($config['DB']['HOST'], $config['DB']['USER'], $config['DB']['PASSWORD'], $config['DB']['DATABASE'], $config['DB']['PORT']);

if ($conn->connect_error) {
    echo '<p class="message">데이터베이스 연결에 실패했습니다.</p>';
    exit;
}

$query = isset($_GET['q']) ? trim($_GET['q']) : '';
if (empty($query)) {
    echo '<p class="message">검색어를 입력해주세요.</p>';
    exit;
}

$search_term = "%" . $conn->real_escape_string($query) . "%";
$sql = "SELECT sn.stock_code, sd.stock_name, sn.title, sn.link, sn.description, sn.pub_date 
        FROM stock_news sn
        JOIN stock_details sd ON sn.stock_code = sd.stock_code
        WHERE sd.stock_name LIKE ? OR sn.stock_code LIKE ?
        ORDER BY sn.pub_date DESC LIMIT 50";

$stmt = $conn->prepare($sql);
$stmt->bind_param("ss", $search_term, $search_term);
$stmt->execute();
$result = $stmt->get_result();

echo "<h2>'" . htmlspecialchars($query) . "'에 대한 검색 결과</h2>";

if ($result->num_rows > 0) {
    while($row = $result->fetch_assoc()) {
        echo '<div class="news-item">';
        echo '<div class="news-meta"><span class="stock-info">' . htmlspecialchars($row['stock_name']) . ' (' . htmlspecialchars($row['stock_code']) . ')</span>' . htmlspecialchars($row['pub_date']) . '</div>';
        echo '<div class="news-title"><a href="' . htmlspecialchars($row['link']) . '" target="_blank">' . htmlspecialchars($row['title']) . '</a></div>';
        echo '<div class="news-description">' . htmlspecialchars($row['description']) . '</div>';
        echo '</div>';
    }
} else {
    echo '<p class="message">해당 종목에 대한 뉴스를 찾을 수 없습니다.</p>';
}

$stmt->close();
$conn->close();
?>