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

        function write_log($message) {
            error_log(date('[Y-m-d H:i:s]') . ' ' . $message . PHP_EOL, 3, LOG_FILE);
        }

        write_log("display_us_stocks.php 스크립트 시작");

        // DB 연결
        $config_file = __DIR__ . '/config.ini';
        if (!file_exists($config_file)) {
            write_log("오류: config.ini 파일을 찾을 수 없습니다.");
            die("<p class='error'>config.ini 파일을 찾을 수 없습니다.</p>");
        }
        $config = parse_ini_file($config_file, true);
        if ($config === false || !isset($config['DB'])) {
            write_log("오류: config.ini 파일의 [DB] 섹션이 유효하지 않습니다.");
            die("<p class='error'>config.ini 파일의 [DB] 섹션이 유효하지 않습니다.</p>");
        }

        $conn = new mysqli($config['DB']['HOST'], $config['DB']['USER'], $config['DB']['PASSWORD'], $config['DB']['DATABASE'], $config['DB']['PORT']);
        if ($conn->connect_error) {
            write_log("DB 연결 실패: " . $conn->connect_error);
            die("<p class='error'>DB 연결 실패: " . $conn->connect_error . "</p>");
        }
        $conn->set_charset("utf8mb4");
        write_log("데이터베이스 연결 성공.");

        // 종목코드를 종목명으로 변환하는 함수
        function getStockName($stock_code) {
            // 이 부분은 나중에 DB에서 동적으로 가져오도록 개선 필요
            $stock_names = [
                '000020' => '동화약품', '000040' => 'KR모터스', '000050' => '경방', '000070' => '삼성중공업',
                '000075' => '영풍제지', '000080' => '하이트진로', '000087' => '영원무역', '000100' => '유한양행',
                '000105' => '유한양행우', '000120' => 'CJ대한통운', '000140' => '하이트진로', '000145' => '중외제약',
                '000150' => '두산', '000210' => '대림산업', '000220' => '유진투자증권', '000230' => '일진전기',
                '000240' => '한국코아옵틱스', '000250' => '삼전약품', '000270' => '기아', '000300' => '대유위니아',
                '000430' => '대원강업', '000480' => '조선선박', '000490' => '대동', '000700' => '유진',
                '000950' => '전량선법', '001040' => 'CJ', '001060' => 'JW중외제약', '001120' => '미래산업',
                '001200' => 'GS', '001340' => '백광산업'
            ];
            return isset($stock_names[$stock_code]) ? $stock_names[$stock_code] : $stock_code;
        }

        // 영문-한글 테마 매핑 (실제 DB 테마에 맞게 수정)
        $theme_map = [
            'Technology' => ['AI & 반도체', '로봇'],
            'Healthcare' => ['헬스케어 & 바이오'],
            'Financial Services' => ['가상자산 & 게임 & NFT'],
            'Consumer Cyclical' => ['2차전지 & 전기차'],
            'Industrials' => ['조선 & 전력 인프라', '우주 & 항공 & 방산'],
            'Communication Services' => ['가상자산 & 게임 & NFT'],
            'Energy' => ['친환경 & 원자력'],
            'Basic Materials' => ['친환경 & 원자력'],
            'Real Estate' => [],
            'Utilities' => ['조선 & 전력 인프라'],
            'Consumer Defensive' => []
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
        write_log("시가총액 상위 10위 주식 조회 시작.");
        echo "<h2>시가총액 상위 10위 주식</h2>";
        $sql_market_cap = "SELECT ticker, company_name, market_cap FROM us_top_market_cap_stocks ORDER BY market_cap DESC LIMIT 10";
        $result_market_cap = $conn->query($sql_market_cap);

        if ($result_market_cap) {
            if ($result_market_cap->num_rows > 0) {
                write_log("시가총액 상위 10위 주식 조회 성공. 총 " . $result_market_cap->num_rows . "개 종목 발견.");
                echo "<table><thead><tr><th>티커</th><th>종목명</th><th>시가총액</th></tr></thead><tbody>";
                while($row = $result_market_cap->fetch_assoc()) {
                    echo "<tr>";
                    echo "<td>" . htmlspecialchars($row["ticker"]) . "</td>";
                    echo "<td>" . htmlspecialchars($row["company_name"]) . "</td>";
                    echo "<td>" . number_format($row["market_cap"]) . "</td>";
                    echo "</tr>";
                }
                echo "</tbody></table>";
            } else {
                write_log("시가총액 상위 10위 주식 데이터 없음.");
                echo "<p class='no-data'>시가총액 상위 10위 주식 데이터를 찾을 수 없습니다. 'python_modules/get_us_top_30_stocks.py'를 실행해주세요.</p>";
            }
        } else {
            write_log("시가총액 상위 10위 주식 쿼리 실패: " . $conn->error);
            echo "<p class='error'>시가총액 상위 10위 주식 데이터를 가져오는 중 오류가 발생했습니다.</p>";
        }


        // --- 상승률 상위 주식 및 연관 국내 테마 ---
        write_log("상승률 상위 주식 및 연관 국내 테마 조회 시작.");
        echo "<h2>상승률 상위 주식 및 연관 국내 테마</h2>";
        $sql_stocks = "SELECT ticker, company_name, theme, last_price, change_val, percent_change FROM us_top_stocks ORDER BY percent_change DESC";
        $result_stocks = $conn->query($sql_stocks);
        
        if ($result_stocks) {
            if ($result_stocks->num_rows > 0) {
                write_log("상승률 상위 주식 조회 성공. 총 " . $result_stocks->num_rows . "개 종목 발견.");
                echo "<table><thead><tr><th>티커</th><th>종목명</th><th>테마</th><th>현재가</th><th>등락률</th><th>연관 국내 종목</th></tr></thead><tbody>";
                
                while($row = $result_stocks->fetch_assoc()) {
                    $rate_class = $row["percent_change"] >= 0 ? 'positive' : 'negative';
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
                            $like_conditions[] = "sn.theme LIKE ?"; // LIKE 연산자 사용
                            $bind_params[] = "%" . $theme . "%"; // 부분 일치를 위해 % 추가
                        }
                        $sql_related = "SELECT DISTINCT sn.stock_code, COALESCE(a.stock_name, sn.stock_code) as display_name FROM stock_news sn LEFT JOIN all_stocks a ON sn.stock_code = a.stock_code WHERE " . implode(' OR ', $like_conditions) . " ORDER BY display_name LIMIT 10";
                        write_log("연관 국내 종목 쿼리 실행: " . preg_replace('/[\s]+/S', ' ', $sql_related) . " (바인딩 파라미터: " . implode(', ', $bind_params) . ")");
                        
                        $stmt = $conn->prepare($sql_related);
                        
                        // bind_param 처리
                        $types = str_repeat('s', count($bind_params));
                        $stmt->bind_param($types, ...$bind_params);

                        $stmt->execute();
                        $related_result = $stmt->get_result();
                        
                        if ($related_result->num_rows > 0) {
                            write_log("연관 국내 종목 조회 성공. 총 " . $related_result->num_rows . "개 종목 발견.");
                            echo "<ul class='related-stocks'>";
                            while($related_row = $related_result->fetch_assoc()) {
                                $stock_name = getStockName($related_row['stock_code']);
                                echo "<li><a href='display_stock_news.php?stock_code=" . urlencode($related_row['stock_code']) . "'>" . htmlspecialchars($stock_name) . "</a></li>";
                            }
                            echo "</ul>";
                        } else {
                            write_log("연관 국내 종목 데이터 없음.");
                            echo "N/A";
                        }
                        $stmt->close();
                    } else {
                        write_log("미국 테마에 대한 국내 테마 매핑 또는 관련 국내 종목 없음.");
                        echo "N/A";
                    }
                    echo "</td></tr>";
                }
                echo "</tbody></table>";
            } else {
                write_log("상승률 상위 주식 데이터 없음.");
                echo "<p class='no-data'>상승률 상위 주식 데이터를 찾을 수 없습니다. 'python_modules/get_us_top_30_stocks.py'를 실행해주세요.</p>";
            }
        }

        $conn->close();
        write_log("데이터베이스 연결 종료.");
        write_log("display_us_stocks.php 스크립트 종료");
        ?>
        <a href="index.php" class="fixed-home-button">메인</a>
    </div>
</body>
</html>