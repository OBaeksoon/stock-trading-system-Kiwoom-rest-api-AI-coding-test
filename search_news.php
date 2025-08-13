<?php
// 에러 리포팅 활성화 (개발용)
ini_set('display_errors', 1);
error_reporting(E_ALL);

// 로그 파일 경로 설정
define('LOG_FILE', __DIR__ . '/../logs/search_news.log');

function write_log($message) {
    error_log(date('[Y-m-d H:i:s]') . ' ' . $message . PHP_EOL, 3, LOG_FILE);
}

write_log("search_news.php 스크립트 시작");

require_once 'db_connection.php';
write_log("db_connection.php 로드 완료.");

$query = isset($_GET['q']) ? trim($_GET['q']) : '';
write_log("검색 쿼리 수신: " . $query);

if (empty($query)) {
    write_log("검색어가 비어 있습니다. 메시지 출력 후 종료.");
    echo '<p class="message">검색어를 입력해주세요.</p>';
    exit;
}

try {
    $pdo = get_db_connection();
    write_log("데이터베이스 연결 성공.");
    $search_term = "%" . $query . "%";
    $sql = "SELECT sn.stock_code, sd.stock_name, sn.title, sn.link, sn.description, sn.pub_date 
            FROM stock_news sn
            JOIN stock_details sd ON sn.stock_code = sd.stock_code
            WHERE sd.stock_name LIKE ? OR sn.stock_code LIKE ?
            ORDER BY sn.pub_date DESC LIMIT 50";

    write_log("뉴스 검색 쿼리 실행: " . $sql . " (검색어: " . $query . ")");
    $stmt = $pdo->prepare($sql);
    $stmt->execute([$search_term, $search_term]);
    $news_list = $stmt->fetchAll();
    write_log("뉴스 검색 성공. 조회된 뉴스 수: " . count($news_list));

    echo "<h2>'" . htmlspecialchars($query) . "'에 대한 검색 결과</h2>";

    if (count($news_list) > 0) {
        foreach ($news_list as $row) {
            echo '<div class="news-item">';
            echo '<div class="news-meta"><span class="stock-info">' . htmlspecialchars($row['stock_name']) . ' (' . htmlspecialchars($row['stock_code']) . ')</span>' . htmlspecialchars($row['pub_date']) . '</div>';
            echo '<div class="news-title"><a href="' . htmlspecialchars($row['link']) . '" target="_blank">' . htmlspecialchars($row['title']) . '</a></div>';
            echo '<div class="news-description">' . htmlspecialchars($row['description']) . '</div>';
            echo '</div>';
        }
    } else {
        write_log("해당 검색어에 대한 뉴스를 찾을 수 없습니다.");
        echo '<p class="message">해당 종목에 대한 뉴스를 찾을 수 없습니다.</p>';
    }

} catch (PDOException $e) {
    write_log("데이터베이스 검색 중 오류가 발생했습니다: " . $e->getMessage());
    echo '<p class="message">데이터베이스 검색 중 오류가 발생했습니다.</p>';
}

write_log("search_news.php 스크립트 종료");
?>