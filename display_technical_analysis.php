<?php
$search_query = isset($_GET['stock_code']) ? trim($_GET['stock_code']) : '';
$json_data = '';
$data = [];
$error_message = '';

if (!empty($search_query)) {
    // 보안을 위해 쉘 인자 이스케이프
    $escaped_query = escapeshellarg($search_query);
    $command = "python3 " . __DIR__ . "/python_modules/get_technical_analysis.py " . $escaped_query;

    // 파이썬 스크립트 실행 및 결과 캡처
    $json_data = shell_exec($command);
    
    if ($json_data) {
        $data = json_decode($json_data, true);
        if (json_last_error() !== JSON_ERROR_NONE) {
            $error_message = "분석 데이터를 파싱하는 데 실패했습니다. (JSON 오류)";
            $data = [];
        }
    } else {
        $error_message = "데이터를 분석하는 중 오류가 발생했습니다.";
    }
}
?>
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>종목별 기술적 지표 분석</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; margin: 20px; background-color: #f8f9fa; color: #333; }
        .container { max-width: 95%; margin: auto; background: #fff; padding: 20px 30px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
        h1 { color: #0056b3; text-align: center; margin-bottom: 20px; }
        .search-form { text-align: center; margin-bottom: 30px; }
        .search-form input[type="text"] { width: 300px; padding: 12px; font-size: 16px; border: 2px solid #dee2e6; border-radius: 5px; }
        .search-form input[type="submit"] { padding: 12px 20px; font-size: 16px; background-color: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; }
        .message { text-align: center; color: #6c757d; font-size: 1.1em; padding: 40px 0; }
        .home-link { display: block; text-align: center; margin-top: 30px; text-decoration: none; color: #007bff; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; font-size: 0.9em; }
        th, td { padding: 8px 10px; border: 1px solid #dee2e6; text-align: right; }
        th { background-color: #e9ecef; white-space: nowrap; }
        td:first-child { text-align: center; white-space: nowrap; }
    </style>
</head>
<body>
    <div class="container">
        <h1>종목별 기술적 지표 분석</h1>
        <div class="search-form">
            <form action="" method="GET">
                <input type="text" name="stock_code" placeholder="종목 코드 입력 (예: 005930)" value="<?php echo htmlspecialchars($search_query); ?>">
                <input type="submit" value="조회">
            </form>
        </div>

        <?php if (!empty($search_query)): ?>
            <h2>'<?php echo htmlspecialchars($search_query); ?>' 기술적 분석 결과</h2>
            <?php if (!empty($data) && empty($error_message)): ?>
                <div style="overflow-x:auto;">
                <table>
                    <thead>
                        <tr>
                            <th>날짜</th>
                            <th>종가</th>
                            <th>SMA_20</th>
                            <th>RSI_14</th>
                            <th>BBL_20</th>
                            <th>BBM_20</th>
                            <th>BBU_20</th>
                            <th>MACD_12_26_9</th>
                            <th>MACDh_12_26_9</th>
                            <th>MACDs_12_26_9</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach (array_reverse($data) as $row): // 최신 날짜가 위로 오도록 역순 출력 ?>
                            <tr>
                                <td><?php echo htmlspecialchars($row['date']); ?></td>
                                <td><?php echo number_format($row['close']); ?></td>
                                <td><?php echo number_format($row['SMA_20_20'], 2); ?></td>
                                <td><?php echo number_format($row['RSI_14'], 2); ?></td>
                                <td><?php echo number_format($row['BBL_20_2.0'], 2); ?></td>
                                <td><?php echo number_format($row['BBM_20_2.0'], 2); ?></td>
                                <td><?php echo number_format($row['BBU_20_2.0'], 2); ?></td>
                                <td><?php echo number_format($row['MACD_12_26_9'], 2); ?></td>
                                <td><?php echo number_format($row['MACDh_12_26_9'], 2); ?></td>
                                <td><?php echo number_format($row['MACDs_12_26_9'], 2); ?></td>
                            </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>
                </div>
            <?php else: ?>
                <p class="message"><?php echo $error_message ?: "데이터를 가져오지 못했거나 해당 종목의 데이터가 없습니다."; ?></p>
            <?php endif; ?>
        <?php else: ?>
            <p class="message">상단 검색창을 통해 원하시는 종목의 기술적 지표를 조회해보세요.</p>
        <?php endif; ?>
        
        <a href="index.php" class="home-link">메인으로 돌아가기</a>
    </div>
</body>
</html>
