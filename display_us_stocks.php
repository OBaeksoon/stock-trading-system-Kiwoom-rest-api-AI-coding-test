<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>미국 주식 현황 및 국내 연관 테마</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; background-color: #f8f9fa; color: #212529; }
        .container { max-width: 1400px; margin: 0 auto; background-color: #ffffff; padding: 30px; border-radius: 10px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08); }
        h1, h2 { color: #0056b3; text-align: center; margin-bottom: 20px; }
        h2 { margin-top: 40px; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 12px 15px; border-bottom: 1px solid #dee2e6; text-align: left; vertical-align: middle; }
        th { background-color: #007bff; color: white; position: sticky; top: 0; font-weight: 600; }
        tr:nth-child(even) { background-color: #f8f9fa; }
        tr:hover { background-color: #e9ecef; }
        .error, .no-data { color: #dc3545; text-align: center; margin-top: 20px; font-size: 18px; }
        .positive { color: #dc3545; font-weight: bold; }
        .negative { color: #007bff; font-weight: bold; }
        .home-link { display: block; text-align: center; margin-top: 40px; text-decoration: none; color: #007bff; font-weight: bold; }
        .theme-badge { display: inline-block; padding: 5px 10px; border-radius: 15px; background-color: #6c757d; color: white; font-size: 12px; }
        .related-stocks { list-style: none; padding-left: 0; margin: 0; }
        .related-stocks li { display: inline-block; margin: 2px; }
        .related-stocks a { color: #28a745; text-decoration: none; font-size: 13px; background-color: #eaf6ec; padding: 3px 8px; border-radius: 10px; }
        .related-stocks a:hover { background-color: #d4edda; }
        .fixed-home-button {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background-color: #007bff;
            color: white;
            padding: 10px 15px;
            border-radius: 5px;
            text-decoration: none;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            z-index: 1000;
        }
        .fixed-home-button:hover {
            background-color: #0056b3;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>미국 주식 현황 및 국내 연관 테마</h1>

        <?php
        // 에러 리포팅 활성화 (개발용)
        ini_set('display_errors', 1);
        error_reporting(E_ALL);

        // 로그 파일 경로 설정
        define('LOG_FILE', __DIR__ . '/../logs/display_us_stocks.log');

        require_once __DIR__ . '/includes/log_utils.php';

        write_log("display_us_stocks.php 스크립트 시작");

        // --- Python 스크립트 실행하여 데이터 가져오기 ---
        $python_executable = escapeshellcmd(__DIR__ . '/.venv/bin/python');
        $script_path = escapeshellcmd(__DIR__ . '/python_modules/get_us_top_30_stocks.py');
        $command = $python_executable . ' ' . $script_path . ' 2>&1';
        
        write_log("Python 스크립트 실행: " . $command);
        $json_output = shell_exec($command);
        write_log("Python 스크립트 결과 (raw): " . $json_output);

        $data = json_decode($json_output, true);

        if (json_last_error() !== JSON_ERROR_NONE || !isset($data['top_gainers']) || !isset($data['top_market_cap'])) {
            write_log("Python 스크립트 결과 파싱 실패. JSON 오류: " . json_last_error_msg());
            echo "<p class='error'>미국 주식 데이터를 가져오는 데 실패했습니다. 로그를 확인해주세요.</p>";
            // 스크립트 실행을 중단하지 않고, 아래 DB 로직이 실행될 수 있도록 함 (연관 테마 등)
        } else {
            write_log("Python 스크립트 결과 파싱 성공.");
        }

        // --- DB 연결 (국내 연관 테마 조회를 위해 필요) ---
        $config_file = __DIR__ . '/config.ini';
        if (!file_exists($config_file)) {
            write_log("오류: config.ini 파일을 찾을 수 없습니다.");
            die("<p class='error'>config.ini 파일을 찾을 수 없습니다.</p>");
        }
        $config = parse_ini_file($config_file, true);
        $conn = new mysqli($config['DB']['HOST'], $config['DB']['USER'], $config['DB']['PASSWORD'], $config['DB']['DATABASE'], $config['DB']['PORT']);
        if ($conn->connect_error) {
            write_log("DB 연결 실패: " . $conn->connect_error);
            die("<p class='error'>DB 연결 실패: " . $conn->connect_error . "</p>");
        }
        $conn->set_charset("utf8mb4");
        write_log("데이터베이스 연결 성공 (국내 연관 테마용).");

        // 영문-한글 테마 매핑
        $theme_map = [
            'Technology' => ['AI & 반도체', '로봇'], 'Healthcare' => ['헬스케어 & 바이오'],
            'Financial Services' => ['가상자산 & 게임 & NFT'], 'Consumer Cyclical' => ['2차전지 & 전기차'],
            'Industrials' => ['조선 & 전력 인프라', '우주 & 항공 & 방산'], 'Communication Services' => ['가상자산 & 게임 & NFT'],
            'Energy' => ['친환경 & 원자력'], 'Basic Materials' => ['친환경 & 원자력'],
            'Real Estate' => [], 'Utilities' => ['조선 & 전력 인프라'], 'Consumer Defensive' => []
        ];

    
        // --- 주요 지수 ---
        write_log("주요 지수 조회 시작.");
        echo "<h2>주요 지수</h2>";
        $sql_indices = "SELECT name, last_price, change_val, percent_change, updated_at FROM us_indices ORDER BY id";
        $result_indices = $conn->query($sql_indices);
        if ($result_indices) {
            if ($result_indices->num_rows > 0) {
                write_log("주요 지수 조회 성공. 총 " . $result_indices->num_rows . "개 지수 발견.");
                echo "<table><thead><tr><th>지수명</th><th>현재가</th><th>등락</th><th>등락률</th><th>업데이트</th></tr></thead><tbody>";
                while($row = $result_indices->fetch_assoc()) {
                    $rate_class = $row["percent_change"] >= 0 ? 'positive' : 'negative';
                    echo "<tr><td>" . htmlspecialchars($row["name"]) . "</td><td>" . number_format($row["last_price"], 2) . "</td><td class='" . $rate_class . "'>" . number_format($row["change_val"], 2) . "</td><td class='" . $rate_class . "'>" . number_format($row["percent_change"], 2) . "%</td><td>" . htmlspecialchars($row["updated_at"]) . "</td></tr>";
                }
                echo "</tbody></table>";
            } else {
                write_log("주요 지수 데이터 없음.");
                echo "<p class='no-data'>주요 지수 데이터를 찾을 수 없습니다.</p>";
            }
        } else {
            write_log("주요 지수 쿼리 실패: " . $conn->error);
            echo "<p class='error'>주요 지수 데이터를 가져오는 중 오류가 발생했습니다.</p>";
        }

        // --- 시가총액 상위 10위 주식 ---
        echo "<h2>시가총액 상위 10위 주식</h2>";
        if (!empty($data['top_market_cap'])) {
            write_log("시가총액 상위 10위 주식 데이터 표시 시작.");
            echo "<table><thead><tr><th>티커</th><th>종목명</th><th>시가총액</th><th>등락률</th></tr></thead><tbody>";
            foreach($data['top_market_cap'] as $row) {
                $rate_class = ($row["percent_change"] ?? 0) >= 0 ? 'positive' : 'negative';
                echo "<tr>";
                echo "<td>" . htmlspecialchars($row["ticker"]) . "</td>";
                echo "<td>" . htmlspecialchars($row["company_name"]) . "</td>";
                echo "<td>$" . number_format($row["market_cap"] / 1000000000, 2) . "B</td>"; // 억 달러 단위로 표시
                echo "<td class='" . $rate_class . "'>" . number_format($row["percent_change"] ?? 0, 2) . "%</td>";
                echo "</tr>";
            }
            echo "</tbody></table>";
        } else {
            write_log("시가총액 상위 10위 주식 데이터 없음.");
            echo "<p class='no-data'>시가총액 상위 10위 주식 데이터를 찾을 수 없습니다.</p>";
        }

        // --- 상승률 상위 주식 및 연관 국내 테마 ---
        echo "<h2>상승률 상위 주식 및 연관 국내 테마</h2>";
        if (!empty($data['top_gainers'])) {
            write_log("상승률 상위 주식 데이터 표시 시작.");
            echo "<table><thead><tr><th>티커</th><th>종목명</th><th>테마</th><th>현재가</th><th>등락률</th><th>연관 국내 종목</th></tr></thead><tbody>";
            
            foreach($data['top_gainers'] as $row) {
                $rate_class = ($row["percent_change"] ?? 0) >= 0 ? 'positive' : 'negative';
                echo "<tr>";
                echo "<td>" . htmlspecialchars($row["ticker"]) . "</td>";
                echo "<td>" . htmlspecialchars($row["company_name"]) . "</td>";
                echo "<td><span class='theme-badge'>" . htmlspecialchars($row["theme"]) . "</span></td>";
                echo "<td>" . number_format($row["last_price"], 2) . "</td>";
                echo "<td class='" . $rate_class . "'>" . number_format($row["percent_change"], 2) . "%</td>";
                
                echo "<td>";
                $us_theme = $row['theme'];
                if (!empty($us_theme) && isset($theme_map[$us_theme]) && !empty($theme_map[$us_theme])) {
                    $korean_themes = $theme_map[$us_theme];
                    $like_conditions = [];
                    $bind_params = [];
                    foreach ($korean_themes as $theme) {
                        $like_conditions[] = "sn.theme LIKE ?";
                        $bind_params[] = "%" . $theme . "%";
                    }
                    $sql_related = "SELECT DISTINCT sn.stock_code, COALESCE(a.stock_name, sn.stock_code) as display_name FROM stock_news sn LEFT JOIN all_stocks a ON sn.stock_code = a.stock_code WHERE " . implode(' OR ', $like_conditions) . " ORDER BY display_name LIMIT 10";
                    
                    $stmt = $conn->prepare($sql_related);
                    $stmt->bind_param(str_repeat('s', count($bind_params)), ...$bind_params);
                    $stmt->execute();
                    $related_result = $stmt->get_result();
                    
                    if ($related_result->num_rows > 0) {
                        echo "<ul class='related-stocks'>";
                        while($related_row = $related_result->fetch_assoc()) {
                            echo "<li><a href='display_stock_news.php?stock_code=" . urlencode($related_row['stock_code']) . "'>" . htmlspecialchars($related_row['display_name']) . "</a></li>";
                        }
                        echo "</ul>";
                    } else {
                        echo "N/A";
                    }
                    $stmt->close();
                } else {
                    echo "N/A";
                }
                echo "</td></tr>";
            }
            echo "</tbody></table>";
        } else {
            write_log("상승률 상위 주식 데이터 없음.");
            echo "<p class='no-data'>상승률 상위 주식 데이터를 찾을 수 없습니다.</p>";
        }

        $conn->close();
        write_log("데이터베이스 연결 종료.");
        write_log("display_us_stocks.php 스크립트 종료");
        ?>
        <a href="index.php" class="fixed-home-button">메인</a>
    </div>
</body>
</html>