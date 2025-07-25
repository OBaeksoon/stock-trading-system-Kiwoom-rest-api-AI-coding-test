<?php
// stock_data.db 파일 경로 설정 (all_stocks.php와 같은 디렉토리에 있다고 가정)
$dbPath = __DIR__ . '/stock_data.db';

// 검색어 및 시장 타입 초기화
$searchQuery = isset($_GET['search']) ? trim($_GET['search']) : '';
$marketFilter = isset($_GET['market']) ? $_GET['market'] : 'all'; // 'all', 'kospi', 'kosdaq'

// 데이터베이스 연결 함수
function connectDb($dbPath) {
    try {
        $pdo = new PDO("sqlite:" . $dbPath);
        $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
        return $pdo;
    } catch (PDOException $e) {
        // 오류 로그는 웹 서버의 오류 로그 파일 (예: Apache의 error.log)에 기록됩니다.
        error_log("데이터베이스 연결 오류: " . $e->getMessage());
        return null;
    }
}

// 종목 데이터 불러오는 함수
function getStocks($pdo, $marketType = 'all', $searchQuery = '') {
    // 실시간 시세 컬럼을 포함하도록 SQL 쿼리 수정
    $sql = "SELECT code, name, marketCode, marketName, current_price, fluctuation_rate, trade_volume, trade_value FROM all_stocks WHERE 1=1";
    $params = [];

    if ($marketType === 'kospi') {
        $sql .= " AND marketCode = '0'";
    } elseif ($marketType === 'kosdaq') {
        $sql .= " AND marketCode = '10'";
    }

    if (!empty($searchQuery)) {
        // 종목명 또는 종목 코드로 검색
        $sql .= " AND (name LIKE :searchQuery OR code LIKE :searchQuery)";
        $params[':searchQuery'] = '%' . $searchQuery . '%';
    }

    $sql .= " ORDER BY name ASC"; // 종목명을 기준으로 오름차순 정렬

    try {
        $stmt = $pdo->prepare($sql);
        $stmt->execute($params);
        return $stmt->fetchAll(PDO::FETCH_ASSOC);
    } catch (PDOException $e) {
        error_log("종목 데이터 조회 오류: " . $e->getMessage());
        return [];
    }
}

$pdo = connectDb($dbPath);
$kospiStocks = [];
$kosdaqStocks = [];

if ($pdo) {
    // 필터에 따라 코스피 또는 코스닥 데이터를 로드
    if ($marketFilter === 'kospi' || $marketFilter === 'all') {
        $kospiStocks = getStocks($pdo, 'kospi', $searchQuery);
    }
    if ($marketFilter === 'kosdaq' || $marketFilter === 'all') {
        $kosdaqStocks = getStocks($pdo, 'kosdaq', $searchQuery);
    }
} else {
    // DB 연결 실패 시 사용자에게 메시지 표시 (개발 중일 때 유용)
    echo "<p class='error'>데이터베이스에 연결할 수 없습니다. `stock_data.db` 파일 경로(`$dbPath`)를 확인해주세요.</p>";
}

?>

<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>키움증권 자동 매매 - 전체 종목 목록</title>
    <link rel="stylesheet" href="style.css">
    <meta http-equiv="refresh" content="5"> 
    <style>
        /* 실시간 데이터 숫자 정렬을 위한 CSS */
        .stock-table td.numeric {
            text-align: right;
        }
        .stock-table th {
            white-space: nowrap; /* 헤더 텍스트 줄바꿈 방지 */
        }
        /* 등락률 색상 (선택 사항) */
        .fluctuation-positive { color: red; }
        .fluctuation-negative { color: blue; }
    </style>
</head>
<body>
    <div class="container">
        <h1>키움증권 자동 매매 시스템</h1>

        <nav class="main-nav">
            <ul>
                <li><a href="all_stocks.php">메인 페이지</a></li>
                <li><a href="all_stocks.php" class="active">전체 종목</a></li>
                </ul>
        </nav>

        <div class="search-filter-section">
            <form action="all_stocks.php" method="GET" class="search-form">
                <input type="text" name="search" placeholder="종목명 또는 코드 검색" value="<?= htmlspecialchars($searchQuery) ?>">
                <select name="market">
                    <option value="all" <?= $marketFilter === 'all' ? 'selected' : '' ?>>전체 시장</option>
                    <option value="kospi" <?= $marketFilter === 'kospi' ? 'selected' : '' ?>>코스피</option>
                    <option value="kosdaq" <?= $marketFilter === 'kosdaq' ? 'selected' : '' ?>>코스닥</option>
                </select>
                <button type="submit">검색 및 필터</button>
            </form>
        </div>

        <?php if (!empty($searchQuery)): ?>
            <p class="search-info">검색어: "<strong><?= htmlspecialchars($searchQuery) ?></strong>" (현재 필터: <?php
                if ($marketFilter === 'kospi') echo '코스피';
                elseif ($marketFilter === 'kosdaq') echo '코스닥';
                else echo '전체 시장';
            ?>)</p>
        <?php endif; ?>

        <?php if ($marketFilter === 'kospi' || $marketFilter === 'all'): ?>
        <section class="stock-section">
            <h2>코스피 종목 (<?= count($kospiStocks) ?>개)</h2>
            <?php if (!empty($kospiStocks)): ?>
            <table class="stock-table">
                <thead>
                    <tr>
                        <th>코드</th>
                        <th>종목명</th>
                        <th>시장</th>
                        <th>현재가</th>
                        <th>등락률 (%)</th>
                        <th>거래량</th>
                        <th>거래대금</th>
                    </tr>
                </thead>
                <tbody>
                    <?php foreach ($kospiStocks as $stock): ?>
                        <tr>
                            <td><?= htmlspecialchars($stock['code']) ?></td>
                            <td><?= htmlspecialchars($stock['name']) ?></td>
                            <td><?= htmlspecialchars($stock['marketName']) ?></td>
                            <td class="numeric"><?= number_format($stock['current_price']) ?></td>
                            <td class="numeric <?= $stock['fluctuation_rate'] > 0 ? 'fluctuation-positive' : ($stock['fluctuation_rate'] < 0 ? 'fluctuation-negative' : '') ?>">
                                <?= number_format($stock['fluctuation_rate'], 2) ?>
                            </td>
                            <td class="numeric"><?= number_format($stock['trade_volume']) ?></td>
                            <td class="numeric"><?= number_format($stock['trade_value']) ?></td>
                        </tr>
                    <?php endforeach; ?>
                </tbody>
            </table>
            <?php else: ?>
                <p>코스피 종목이 없거나 검색 결과가 없습니다.</p>
            <?php endif; ?>
        </section>
        <?php endif; ?>

        <?php if ($marketFilter === 'kosdaq' || $marketFilter === 'all'): ?>
        <section class="stock-section">
            <h2>코스닥 종목 (<?= count($kosdaqStocks) ?>개)</h2>
            <?php if (!empty($kosdaqStocks)): ?>
            <table class="stock-table">
                <thead>
                    <tr>
                        <th>코드</th>
                        <th>종목명</th>
                        <th>시장</th>
                        <th>현재가</th>
                        <th>등락률 (%)</th>
                        <th>거래량</th>
                        <th>거래대금</th>
                    </tr>
                </thead>
                <tbody>
                    <?php foreach ($kosdaqStocks as $stock): ?>
                        <tr>
                            <td><?= htmlspecialchars($stock['code']) ?></td>
                            <td><?= htmlspecialchars($stock['name']) ?></td>
                            <td><?= htmlspecialchars($stock['marketName']) ?></td>
                            <td class="numeric"><?= number_format($stock['current_price']) ?></td>
                            <td class="numeric <?= $stock['fluctuation_rate'] > 0 ? 'fluctuation-positive' : ($stock['fluctuation_rate'] < 0 ? 'fluctuation-negative' : '') ?>">
                                <?= number_format($stock['fluctuation_rate'], 2) ?>
                            </td>
                            <td class="numeric"><?= number_format($stock['trade_volume']) ?></td>
                            <td class="numeric"><?= number_format($stock['trade_value']) ?></td>
                        </tr>
                    <?php endforeach; ?>
                </tbody>
            </table>
            <?php else: ?>
                <p>코스닥 종목이 없거나 검색 결과가 없습니다.</p>
            <?php endif; ?>
        </section>
        <?php endif; ?>
    </div>
</body>
</html>