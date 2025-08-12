<?php
$config = parse_ini_file('config.ini', true);

$search_query = isset($_GET['stock_code']) ? trim($_GET['stock_code']) : '';
$data = [];
$error_message = '';
$debug_info = '';
$update_requested = isset($_GET['update']) && $_GET['update'] == '1';

function execute_python_script($command, &$output, &$return_var) {
    exec($command, $output, $return_var);
    // UTF-8 인코딩 시도
    foreach ($output as &$line) {
        if (!mb_check_encoding($line, 'UTF-8')) {
            $line = mb_convert_encoding($line, 'UTF-8', 'EUC-KR');
        }
    }
}

if (!empty($search_query)) {
    try {
        require_once 'db_connection.php';
        $pdo = get_db_connection();
        
        $actual_stock_code = $search_query;
        
        // 검색어가 종목코드가 아니면, 파이썬 스크립트로 종목코드 조회
        if (!preg_match('/^\d{6}$/', $search_query)) {
            $escaped_query = escapeshellarg($search_query);
            $command = "python3 " . __DIR__ . "/python_modules/search_stock_by_name.py " . $escaped_query;
            execute_python_script($command, $py_output, $return_var);
            
            if ($return_var === 0 && !empty($py_output)) {
                $result = json_decode(implode('', $py_output), true);
                if (isset($result['stock_code'])) {
                    $actual_stock_code = $result['stock_code'];
                    $found_name = isset($result['found_name']) ? $result['found_name'] : $search_query;
                    $debug_info = "종목명 '{$search_query}'을(를) 종목코드 '{$actual_stock_code}' ({$found_name})로 변환했습니다.";
                } else {
                    $error_message = "'{$search_query}'에 해당하는 종목을 찾을 수 없습니다. " . ($result['error'] ?? '');
                }
            } else {
                $error_message = "종목 검색 스크립트 실행 중 오류가 발생했습니다.";
                $debug_info = implode("\n", $py_output);
            }
        }
        
        if (empty($error_message)) {
            $stmt = $pdo->prepare("SELECT COUNT(*) FROM technical_analysis WHERE stock_code = ?");
            $stmt->execute([$actual_stock_code]);
            $data_exists = $stmt->fetchColumn() > 0;

            // 데이터가 없거나 업데이트 요청이 있을 경우 데이터 파이프라인 실행
            if (!$data_exists || $update_requested) {
                $debug_info .= "<br>데이터를 생성/업데이트합니다...";
                
                // 1. 차트 데이터 수집 (get_stock_chart_data.py)
                $chart_command = "python3 " . __DIR__ . "/python_modules/get_stock_chart_data.py " . escapeshellarg($actual_stock_code) . " daily 2>&1";
                execute_python_script($chart_command, $chart_output, $chart_return_var);
                if ($chart_return_var !== 0) {
                    $error_message .= "<br>차트 데이터 수집 스크립트 오류: <pre>" . htmlspecialchars(implode("\n", $chart_output)) . "</pre>";
                } else {
                    $debug_info .= "<br>차트 데이터 수집 완료.";
                    // 2. 기술적 분석 데이터 생성 (get_technical_analysis.py)
                    $tech_command = "python3 " . __DIR__ . "/python_modules/get_technical_analysis.py " . escapeshellarg($actual_stock_code) . " 2>&1";
                    execute_python_script($tech_command, $tech_output, $tech_return_var);
                    if ($tech_return_var !== 0) {
                        $error_message .= "<br>기술적 분석 스크립트 오류: <pre>" . htmlspecialchars(implode("\n", $tech_output)) . "</pre>";
                    } else {
                         $debug_info .= "<br>기술적 분석 완료.";
                    }
                }
            }
            
            // 최종적으로 DB에서 기술적 분석 데이터 조회
            $stmt = $pdo->prepare(
                "SELECT * FROM technical_analysis 
                WHERE stock_code = ? 
                ORDER BY analysis_date DESC 
                LIMIT 30
            ");
            $stmt->execute([$actual_stock_code]);
            $data = $stmt->fetchAll(PDO::FETCH_ASSOC);

            if (empty($data) && empty($error_message)) {
                 $error_message = "분석 데이터를 생성하지 못했습니다. 입력한 종목코드를 확인해주세요.";
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
        .search-form button { padding: 12px 20px; font-size: 16px; background-color: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; }
        .message { text-align: center; color: #6c757d; font-size: 1.1em; padding: 40px 0; }
        .home-link { position: fixed; bottom: 20px; right: 20px; background-color: #007bff; color: white; padding: 10px 15px; border-radius: 5px; text-decoration: none; box-shadow: 0 2px 4px rgba(0,0,0,0.2); }
        table { width: 100%; border-collapse: collapse; font-size: 0.9em; }
        th, td { padding: 8px 10px; border: 1px solid #dee2e6; text-align: right; }
        th { background-color: #e9ecef; white-space: nowrap; }
        td:first-child { text-align: center; white-space: nowrap; }
        .chart-container { margin: 20px 0; height: 400px; }
        .view-toggle { text-align: center; margin: 20px 0; }
        .view-toggle button { padding: 10px 20px; margin: 0 5px; border: none; border-radius: 5px; cursor: pointer; }
        .view-toggle button.active { background-color: #007bff; color: white; }
        .view-toggle button:not(.active) { background-color: #e9ecef; color: #333; }
        .debug-info { background-color: #e9ecef; padding: 10px; border-radius: 5px; font-size: 0.8em; color: #333; margin-top: 15px; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <h1>종목별 기술적 지표 분석</h1>
        <div class="search-form">
            <form action="" method="GET">
                <input type="text" name="stock_code" placeholder="종목 코드/종목명 입력 (예: 005930, 삼성전자)" value="<?php echo htmlspecialchars($search_query); ?>" required>
                <button type="submit">조회</button>
                <?php if (!empty($search_query) && empty($error_message)): ?>
                    <button type="submit" name="update" value="1" style="background-color: #28a745; margin-left: 10px;" title="최신 데이터로 강제 업데이트">강제 업데이트</button>
                <?php endif; ?>
            </form>
        </div>

        <?php if (!empty($search_query)): ?>
            <h2>'<?php echo htmlspecialchars($search_query); ?>' 기술적 분석 결과</h2>
            
            <?php if (!empty($debug_info)): ?>
                <div class="debug-info"><?php echo $debug_info; ?></div>
            <?php endif; ?>

            <?php if (!empty($data)): ?>
                <div class="view-toggle">
                    <button id="chartBtn" class="active" onclick="showView('chart')">차트 보기</button>
                    <button id="tableBtn" onclick="showView('table')">테이블 보기</button>
                </div>
                
                <div id="chartView" class="chart-container">
                    <canvas id="technicalChart"></canvas>
                </div>
                
                <div id="tableView" style="display:none; overflow-x:auto;">
                    <table>
                        <thead>
                            <tr>
                                <th>날짜</th><th>종가</th><th>SMA_20</th><th>RSI_14</th><th>BBL_20</th><th>BBM_20</th><th>BBU_20</th><th>MACD</th><th>MACD_Hist</th><th>MACD_Signal</th>
                            </tr>
                        </thead>
                        <tbody>
                            <?php foreach ($data as $row): ?>
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
            <?php elseif (!empty($error_message)): ?>
                <p class="message"><?php echo $error_message; ?></p>
            <?php else: ?>
                 <p class="message">데이터가 없습니다. '강제 업데이트'를 시도해보세요.</p>
            <?php endif; ?>
        <?php else: ?>
            <p class="message">상단 검색창을 통해 원하시는 종목의 기술적 지표를 조회해보세요.</p>
        <?php endif; ?>
    </div>
    
    <a href="index.php" class="home-link">메인</a>

    <?php if (!empty($data)):
    ?><script>
        const chartData = <?php echo json_encode(array_reverse($data)); ?>;
        let technicalChart;

        function showView(view) {
            document.getElementById('chartView').style.display = view === 'chart' ? 'block' : 'none';
            document.getElementById('tableView').style.display = view === 'table' ? 'block' : 'none';
            document.getElementById('chartBtn').classList.toggle('active', view === 'chart');
            document.getElementById('tableBtn').classList.toggle('active', view === 'table');
        }
        
        function createChart() {
            if (technicalChart) {
                technicalChart.destroy();
            }
            const ctx = document.getElementById('technicalChart').getContext('2d');
            const labels = chartData.map(item => item.analysis_date);
            
            technicalChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        { label: '종가', data: chartData.map(item => item.close_price), borderColor: 'rgb(75, 192, 192)', yAxisID: 'y' },
                        { label: 'SMA 20', data: chartData.map(item => item.sma_20), borderColor: 'rgb(255, 159, 64)', yAxisID: 'y' },
                        { label: 'BBU 20', data: chartData.map(item => item.bbu_20), borderColor: 'rgba(255, 99, 132, 0.5)', fill: '+1', yAxisID: 'y' },
                        { label: 'BBL 20', data: chartData.map(item => item.bbl_20), borderColor: 'rgba(255, 99, 132, 0.5)', yAxisID: 'y' },
                        { label: 'RSI 14', data: chartData.map(item => item.rsi_14), borderColor: 'rgb(54, 162, 235)', yAxisID: 'y1', hidden: true }
                    ]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    scales: {
                        y: { type: 'linear', display: true, position: 'left', title: { display: true, text: '가격' } },
                        y1: { type: 'linear', display: true, position: 'right', title: { display: true, text: 'RSI' }, min: 0, max: 100, grid: { drawOnChartArea: false } }
                    }
                }
            });
        }
        
        document.addEventListener('DOMContentLoaded', createChart);
    </script>
    <?php endif; ?>
</body>
</html>