<?php
$config = parse_ini_file('config.ini', true);

$search_query = isset($_GET['stock_code']) ? trim($_GET['stock_code']) : '';
$data = [];
$error_message = '';
$update_requested = isset($_GET['update']) && $_GET['update'] == '1';

if (!empty($search_query)) {
    try {
        $pdo = new PDO("mysql:host={$config['DB']['HOST']};dbname={$config['DB']['DATABASE']};charset=utf8mb4", 
                      $config['DB']['USER'], $config['DB']['PASSWORD']);
        $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
        
        // 종목명으로 검색한 경우 종목 코드로 변환
        $actual_stock_code = $search_query;
        $debug_info = '';
        
        if (!preg_match('/^\d{6}$/', $search_query)) {
            // 전체 종목 수 확인
            $stmt = $pdo->prepare("SELECT COUNT(*) as total FROM all_stocks");
            $stmt->execute();
            $total_count = $stmt->fetch(PDO::FETCH_ASSOC)['total'];
            
            // 더 넓은 범위로 검색
            $stmt = $pdo->prepare("SELECT stock_code, stock_name FROM all_stocks WHERE stock_name LIKE ? OR stock_name LIKE ? OR stock_name LIKE ? LIMIT 10");
            $stmt->execute([
                '%' . $search_query . '%',
                $search_query . '%',
                '%' . $search_query
            ]);
            $results = $stmt->fetchAll(PDO::FETCH_ASSOC);
            
            $debug_info = "전체 종목 수: {$total_count}, 검색 결과: " . count($results) . "개";
            
            if (!empty($results)) {
                $actual_stock_code = $results[0]['stock_code'];
                $debug_info .= " (찾은 종목: {$results[0]['stock_name']})";
                
                // 여러 결과가 있으면 정확한 매칭 우선
                foreach ($results as $result) {
                    if (stripos($result['stock_name'], $search_query) !== false) {
                        $actual_stock_code = $result['stock_code'];
                        $debug_info .= " → 정확 매칭: {$result['stock_name']}";
                        break;
                    }
                }
            } else {
                // 검색 결과가 없으면 유사한 종목명 제안
                $stmt = $pdo->prepare("SELECT stock_name FROM all_stocks WHERE stock_name LIKE ? LIMIT 5");
                $stmt->execute(['%' . substr($search_query, 0, 1) . '%']);
                $suggestions = $stmt->fetchAll(PDO::FETCH_COLUMN);
                
                $error_message = "'{$search_query}' 종목을 찾을 수 없습니다. {$debug_info}";
                if (!empty($suggestions)) {
                    $error_message .= "<br>유사한 종목: " . implode(', ', array_slice($suggestions, 0, 5));
                }
            }
        }
        
        if (empty($error_message)) {
            // 업데이트 요청이 있으면 Python 스크립트 실행
            if ($update_requested) {
                $escaped_query = escapeshellarg($actual_stock_code);
                $command = "python3 " . __DIR__ . "/python_modules/get_technical_analysis.py " . $escaped_query . " 2>&1";
                exec($command, $output, $return_var);
                if ($return_var !== 0) {
                    $error_message .= "<br>데이터 업데이트 스크립트 오류: <pre>" . htmlspecialchars(implode("\n", $output)) . "</pre>";
                }
            }
            
            // DB에서 기술적 분석 데이터 조회
            $stmt = $pdo->prepare("
                SELECT * FROM technical_analysis 
                WHERE stock_code = ? 
                ORDER BY analysis_date DESC 
                LIMIT 30
            ");
            $stmt->execute([$actual_stock_code]);
            $data = $stmt->fetchAll(PDO::FETCH_ASSOC);
            
            if (empty($data)) {
                // DB에 데이터가 없으면 Python 스크립트 실행하여 생성
                $escaped_query = escapeshellarg($actual_stock_code);
                $command = "python3 " . __DIR__ . "/python_modules/get_technical_analysis.py " . $escaped_query . " 2>&1";
                exec($command, $output, $return_var);
                if ($return_var !== 0) {
                    $error_message .= "<br>데이터 업데이트 스크립트 오류: <pre>" . htmlspecialchars(implode("\n", $output)) . "</pre>";
                }
                
                // 다시 조회
                $stmt->execute([$actual_stock_code]);
                $data = $stmt->fetchAll(PDO::FETCH_ASSOC);
            }
        }
        
    } catch (PDOException $e) {
        $error_message = "데이터베이스 연결 오류: " . $e->getMessage();
    }
}
?>
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>종목별 기술적 지표 분석</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
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
        .chart-container { margin: 20px 0; height: 400px; }
        .view-toggle { text-align: center; margin: 20px 0; }
        .view-toggle button { padding: 10px 20px; margin: 0 5px; border: none; border-radius: 5px; cursor: pointer; }
        .view-toggle button.active { background-color: #007bff; color: white; }
        .view-toggle button:not(.active) { background-color: #e9ecef; color: #333; }
    </style>
</head>
<body>
    <div class="container">
        <h1>종목별 기술적 지표 분석</h1>
        <div class="search-form">
            <form action="" method="GET">
                <input type="text" name="stock_code" placeholder="종목 코드/종목명 입력 (예: 005930, 삼성전자)" value="<?php echo htmlspecialchars($search_query); ?>">
                <input type="submit" value="조회">
                <?php if (!empty($search_query)): ?>
                    <input type="submit" name="update" value="1" style="background-color: #28a745; margin-left: 10px;" onclick="this.form.submit(); this.value='업데이트 중...'; this.disabled=true;" title="최신 데이터로 업데이트">
                <?php endif; ?>
            </form>
        </div>

        <?php if (!empty($search_query)): ?>
            <h2>'<?php echo htmlspecialchars($search_query); ?>' 기술적 분석 결과</h2>
            <?php if (!empty($debug_info)): ?>
                <p style="font-size: 0.9em; color: #666; text-align: center;"><?php echo $debug_info; ?></p>
            <?php endif; ?>
            <?php if (!empty($data) && empty($error_message)): ?>
                <div class="view-toggle">
                    <button id="chartBtn" class="active" onclick="showChart()">차트 보기</button>
                    <button id="tableBtn" onclick="showTable()">테이블 보기</button>
                </div>
                
                <div id="chartView" class="chart-container">
                    <canvas id="technicalChart"></canvas>
                </div>
                
                <div id="tableView" style="display:none; overflow-x:auto;">
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
                        <?php foreach ($data as $row): // DB에서 이미 최신순으로 정렬됨 ?>
                            <tr>
                                <td><?php echo htmlspecialchars($row['analysis_date']); ?></td>
                                <td><?php echo $row['close_price'] ? number_format($row['close_price']) : '-'; ?></td>
                                <td><?php echo $row['sma_20'] ? number_format($row['sma_20'], 2) : '-'; ?></td>
                                <td><?php echo $row['rsi_14'] ? number_format($row['rsi_14'], 2) : '-'; ?></td>
                                <td><?php echo $row['bbl_20'] ? number_format($row['bbl_20'], 2) : '-'; ?></td>
                                <td><?php echo $row['bbm_20'] ? number_format($row['bbm_20'], 2) : '-'; ?></td>
                                <td><?php echo $row['bbu_20'] ? number_format($row['bbu_20'], 2) : '-'; ?></td>
                                <td><?php echo $row['macd'] ? number_format($row['macd'], 4) : '-'; ?></td>
                                <td><?php echo $row['macd_histogram'] ? number_format($row['macd_histogram'], 4) : '-'; ?></td>
                                <td><?php echo $row['macd_signal'] ? number_format($row['macd_signal'], 4) : '-'; ?></td>
                            </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>
                </div>
                </div>
                
                <script>
                const chartData = <?php echo json_encode(array_reverse($data)); ?>;
                
                function showChart() {
                    document.getElementById('chartView').style.display = 'block';
                    document.getElementById('tableView').style.display = 'none';
                    document.getElementById('chartBtn').classList.add('active');
                    document.getElementById('tableBtn').classList.remove('active');
                    if (!window.technicalChart) {
                        createChart();
                    }
                }
                
                function showTable() {
                    document.getElementById('chartView').style.display = 'none';
                    document.getElementById('tableView').style.display = 'block';
                    document.getElementById('chartBtn').classList.remove('active');
                    document.getElementById('tableBtn').classList.add('active');
                }
                
                function createChart() {
                    const ctx = document.getElementById('technicalChart').getContext('2d');
                    const labels = chartData.map(item => item.analysis_date);
                    
                    window.technicalChart = new Chart(ctx, {
                        type: 'line',
                        data: {
                            labels: labels,
                            datasets: [{
                                label: '종가',
                                data: chartData.map(item => item.close_price),
                                borderColor: 'rgb(75, 192, 192)',
                                backgroundColor: 'rgba(75, 192, 192, 0.1)',
                                yAxisID: 'y'
                            }, {
                                label: 'SMA 20',
                                data: chartData.map(item => item.sma_20),
                                borderColor: 'rgb(255, 99, 132)',
                                backgroundColor: 'rgba(255, 99, 132, 0.1)',
                                yAxisID: 'y'
                            }, {
                                label: 'RSI 14',
                                data: chartData.map(item => item.rsi_14),
                                borderColor: 'rgb(54, 162, 235)',
                                backgroundColor: 'rgba(54, 162, 235, 0.1)',
                                yAxisID: 'y1'
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            scales: {
                                y: {
                                    type: 'linear',
                                    display: true,
                                    position: 'left',
                                    title: {
                                        display: true,
                                        text: '가격'
                                    }
                                },
                                y1: {
                                    type: 'linear',
                                    display: true,
                                    position: 'right',
                                    title: {
                                        display: true,
                                        text: 'RSI'
                                    },
                                    min: 0,
                                    max: 100,
                                    grid: {
                                        drawOnChartArea: false,
                                    },
                                }
                            },
                            plugins: {
                                title: {
                                    display: true,
                                    text: '기술적 지표 차트'
                                }
                            }
                        }
                    });
                }
                
                // 페이지 로드 시 차트 생성
                document.addEventListener('DOMContentLoaded', function() {
                    createChart();
                });
                </script>
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
