<?php
require_once 'db_connection.php';

$query = isset($_GET['q']) ? trim($_GET['q']) : '';
if (empty($query)) {
    echo '<p class="message">검색어를 입력해주세요.</p>';
    exit;
}

try {
    $pdo = get_db_connection();
    $search_term = "%" . $query . "%";
    $sql = "SELECT sn.stock_code, sd.stock_name, sn.title, sn.link, sn.description, sn.pub_date 
            FROM stock_news sn
            JOIN stock_details sd ON sn.stock_code = sd.stock_code
            WHERE sd.stock_name LIKE ? OR sn.stock_code LIKE ?
            ORDER BY sn.pub_date DESC LIMIT 50";

    $stmt = $pdo->prepare($sql);
    $stmt->execute([$search_term, $search_term]);
    $news_list = $stmt->fetchAll();

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
        echo '<p class="message">해당 종목에 대한 뉴스를 찾을 수 없습니다.</p>';
    }

} catch (PDOException $e) {
    error_log($e->getMessage());
    echo '<p class="message">데이터베이스 검색 중 오류가 발생했습니다.</p>';
}
?>