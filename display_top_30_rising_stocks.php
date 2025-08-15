<?php
// 에러 리포팅 활성화 (개발용)
ini_set('display_errors', 1);
error_reporting(E_ALL);

// 로그 파일 경로 설정
define('LOG_FILE', __DIR__ . '/../logs/display_top_30_rising_stocks.log');

require_once __DIR__ . '/includes/log_utils.php';

write_log("display_top_30_rising_stocks.php 스크립트 시작");

// 데이터베이스 연결 및 데이터 페칭 로직을 포함합니다.
require_once 'db_connection.php';
write_log("db_connection.php 로드 완료.");
require_once 'stock_data_fetcher.php';
write_log("stock_data_fetcher.php 로드 완료.");

// 데이터베이스에서 상위 30개 상승 종목 데이터를 가져옵니다.
write_log("get_top_30_rising_stocks 함수 호출 시작.");
$stocks = get_top_30_rising_stocks($conn);
write_log("get_top_30_rising_stocks 함수 호출 완료. 조회된 종목 수: " . count($stocks));

write_log("display_top_30_rising_stocks.php 스크립트 종료");
?>
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>실시간 상승률 30위 종목</title>
    <link rel="stylesheet" href="assets/css/top_30_stocks.css">
</head>
<body>
    <a href="index.php" class="fixed-home-button">메인</a>
    <div class="header">
        <h1>📈 실시간 상승률 30위</h1>
    </div>
    <div class="container">
        <?php if (!empty($stocks)): ?>
            <?php $first_stock = reset($stocks); ?>
            <div class='stats-bar'>📊 총 <?= count($stocks) ?>개 종목 | 마지막 업데이트 <?= date('Y-m-d H:i', strtotime($first_stock['updated_at'])) ?></div>
            <div class='stock-grid'>
                <?php foreach ($stocks as $stock): ?>
                    <div class='stock-card'>
                        <div class='stock-header'>
                            <div class='stock-rank'><?= htmlspecialchars($stock['rank']) ?></div>
                            <div class='stock-name'>
                                <h3><?= htmlspecialchars($stock['stock_name']) ?></h3>
                                <div class='stock-code'><?= htmlspecialchars($stock['stock_code']) ?></div>
                            </div>
                        </div>

                        <div class='stock-metrics'>
                            <div class='metric'><div class='metric-label'>현재가</div><div class='metric-value price'><?= number_format((int)$stock['current_price']) ?>원</div></div>
                            <div class='metric'><div class='metric-label'>등락률</div><div class='metric-value change'><?= ($stock['fluctuation_rate'] >= 0 ? '+' : '') . htmlspecialchars($stock['fluctuation_rate']) ?>%</div></div>
                            <div class='metric'><div class='metric-label'>거래량</div><div class='metric-value volume'><?= number_format((int)$stock['volume']) ?></div></div>
                        </div>

                        <div class='news-section'>
                            <?php if (!empty($stock['news'])): ?>
                                <div class='news-title'>관련 뉴스</div>
                                <ul class='news-list'>
                                    <?php foreach ($stock['news'] as $news): ?>
                                        <li class='news-item'>
                                            <a href='<?= htmlspecialchars($news['link']) ?>' target='_blank' class='news-link'>
                                                <?= htmlspecialchars($news['title']) ?>
                                            </a>
                                            <?php if ($news['theme']): ?>
                                                <span class='theme-tag'><?= htmlspecialchars($news['theme']) ?></span>
                                            <?php endif; ?>
                                            <?php if ($news['pub_date']): ?>
                                                <span class='news-date'><?= date('m-d H:i', strtotime($news['pub_date'])) ?></span>
                                            <?php endif; ?>
                                        </li>
                                    <?php endforeach; ?>
                                </ul>
                            <?php else: ?>
                                <div class='no-news'>📭 관련 뉴스가 없습니다</div>
                            <?php endif; ?>
                        </div>
                    </div>
                <?php endforeach; ?>
            </div>
        <?php else: ?>
            <p class='error'>장중에 데이터가 업데이트됩니다.</p>
        <?php endif; ?>
        
        <div class="update-section">
            <h3 style="margin-bottom: 15px; color: #2c3e50;">🔄 뉴스 데이터 업데이트</h3>
            <p style="margin-bottom: 20px; color: #6c757d;">관련 뉴스가 표시되지 않는 경우 최신 뉴스를 수집할 수 있습니다</p>
            <button onclick="updateNews()" class="update-btn">뉴스 업데이트 시작</button>
            <div id="updateStatus" style="margin-top: 15px;"></div>
        </div>
    </div>
    <script src="assets/js/update_news.js"></script>
</body>
</html>