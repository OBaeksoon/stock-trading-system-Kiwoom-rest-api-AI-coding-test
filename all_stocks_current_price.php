<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>코스피/코스닥 전체 종목 현재가</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>📊</text></svg>">
    <link rel="shortcut icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>📊</text></svg>">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f4f4f4;
            color: #333;
        }
        .container {
            background-color: #fff;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        h1 {
            color: #0056b3;
            text-align: center;
            margin-bottom: 10px;
        }
        .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 20px;
            font-size: 16px;
        }
        #searchInput {
            width: 100%;
            padding: 10px;
            margin-bottom: 20px;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
        }
        .floating-home {
            position: fixed;
            bottom: 30px;
            right: 30px;
            width: 60px;
            height: 60px;
            background: linear-gradient(135deg, #007bff, #0056b3);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 12px rgba(0, 123, 255, 0.3);
            cursor: pointer;
            transition: all 0.3s ease;
            z-index: 1000;
            text-decoration: none;
            color: white;
            font-size: 24px;
        }
        .floating-home:hover {
            transform: scale(1.1);
            box-shadow: 0 6px 20px rgba(0, 123, 255, 0.4);
        }
        .search-results {
            margin-bottom: 10px;
            font-size: 14px;
            color: #666;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            padding: 10px;
            border: 1px solid #ddd;
            text-align: left;
            white-space: nowrap;
        }
        td.news-title {
            white-space: normal;
            max-width: 200px;
        }
        th {
            background-color: #007bff;
            color: white;
            position: sticky;
            top: 0;
        }
        tr:nth-child(even) {
            background-color: #f2f2f2;
        }
        tr:hover {
            background-color: #ddd;
        }
        .positive {
            color: red;
            font-weight: bold;
        }
        .negative {
            color: blue;
            font-weight: bold;
        }
        .news-link {
            color: #0056b3;
            text-decoration: none;
        }
        .news-link:hover {
            text-decoration: underline;
        }
        .error {
            color: red;
            text-align: center;
            margin-top: 20px;
        }
        .no-data {
            text-align: center;
            font-weight: bold;
            color: #555;
        }
    </style>
    <script>
        function searchTable() {
            var input, filter, table, tr, i, visibleCount = 0;
            input = document.getElementById("searchInput");
            filter = input.value.toUpperCase();
            table = document.getElementById("stockTable");
            if (!table) return;

            tr = table.getElementsByTagName("tr");

            for (i = 1; i < tr.length; i++) {
                let tds = tr[i].getElementsByTagName("td");
                let found = false;
                
                for (let j = 0; j < tds.length; j++) {
                    if (tds[j]) {
                        let txtValue = tds[j].textContent || tds[j].innerText;
                        if (txtValue.toUpperCase().indexOf(filter) > -1) {
                            found = true;
                            break;
                        }
                    }
                }
                
                if (found) {
                    tr[i].style.display = "";
                    visibleCount++;
                } else {
                    tr[i].style.display = "none";
                }
            }
            
            var resultsDiv = document.getElementById("searchResults");
            if (filter === "") {
                resultsDiv.innerHTML = "";
            } else {
                resultsDiv.innerHTML = `검색 결과: ${visibleCount}개 종목`;
            }
        }
    </script>
</head>
<body>
    <div class="container">
        <h1>코스피/코스닥 전체 종목 현재가</h1>
        <p class="subtitle" id="subtitle">데이터 로딩 중...</p>
        <input type="text" id="searchInput" placeholder="실시간 검색: 종목 코드, 종목명, 뉴스 내용 입력...">
        <div id="searchResults" class="search-results"></div>

        <?php
        $config_file = __DIR__ . '/config.ini';

        if (!file_exists($config_file)) {
            die("<p class=\"error\">오류: config.ini 파일을 찾을 수 없습니다.</p>");
        }

        $config = parse_ini_file($config_file, true);

        if ($config === false || !isset($config['DB'])) {
            die("<p class=\"error\">오류: config.ini 파일에 [DB] 섹션이 누락되었습니다.</p>");
        }

        $db_host = $config['DB']['HOST'];
        $db_user = $config['DB']['USER'];
        $db_password = $config['DB']['PASSWORD'];
        $db_name = $config['DB']['DATABASE'];
        $db_port = $config['DB']['PORT'];

        $conn = new mysqli($db_host, $db_user, $db_password, $db_name, $db_port);

        if ($conn->connect_error) {
            die("<p class=\"error\">데이터베이스 연결 실패: " . $conn->connect_error . "</p>");
        }
        
        $conn->set_charset("utf8mb4");

        // stock_details와 stock_news 테이블 조인하여 데이터 조회 (유통주식수가 있는 종목만)
        $sql = "
            SELECT 
                sd.stock_code,
                sd.stock_name,
                sd.market,
                sd.current_price,
                sd.previous_day_closing_price,
                sd.circulating_shares,
                sn.title AS news_title,
                sn.link AS news_link
            FROM stock_details sd
            LEFT JOIN (
                SELECT stock_code, title, link, 
                       ROW_NUMBER() OVER(PARTITION BY stock_code ORDER BY pub_date DESC) as rn
                FROM stock_news
            ) sn ON sd.stock_code = sn.stock_code AND sn.rn = 1
            WHERE sd.circulating_shares IS NOT NULL 
                AND sd.circulating_shares != '' 
                AND sd.circulating_shares != '0'
            ORDER BY sd.stock_name ASC
        ";
        
        $result = $conn->query($sql);

        if ($result && $result->num_rows > 0) {
            $rising_count = 0;
            $falling_count = 0;
            $rows = [];
            
            // 먼저 모든 데이터를 배열에 저장하면서 상승/하락 개수 계산
            while($row = $result->fetch_assoc()) {
                $current_price = str_replace(['+', '-'], '', $row["current_price"]);
                $prev_price = str_replace(['+', '-'], '', $row["previous_day_closing_price"]);
                
                if (is_numeric($current_price) && is_numeric($prev_price) && $prev_price != 0) {
                    $fluctuation_rate = (($current_price - $prev_price) / $prev_price) * 100;
                    if ($fluctuation_rate > 0) {
                        $rising_count++;
                    } elseif ($fluctuation_rate < 0) {
                        $falling_count++;
                    }
                }
                $rows[] = $row;
            }
            
            echo "<script>";
            echo "document.getElementById('subtitle').innerHTML = '상승종목: <span style=\"color: red; font-weight: bold;\">{$rising_count}개</span> / 하락종목: <span style=\"color: blue; font-weight: bold;\">{$falling_count}개</span>';";
            echo "</script>";
            
            echo "<table id='stockTable'>";
            echo "<thead><tr><th>종목코드</th><th>종목명</th><th>시장</th><th>현재가</th><th>등락률</th><th>전일종가</th><th>유통주수</th><th>관련뉴스</th></tr></thead>";
            echo "<tbody>";
            
            foreach($rows as $row) {
                // 가격 데이터 처리 (+/- 부호 제거)
                $current_price = str_replace(['+', '-'], '', $row["current_price"]);
                $prev_price = str_replace(['+', '-'], '', $row["previous_day_closing_price"]);
                
                // 등락률 계산
                $fluctuation_rate_str = 'N/A';
                $rate_class = '';
                if (is_numeric($current_price) && is_numeric($prev_price) && $prev_price != 0) {
                    $fluctuation_rate = (($current_price - $prev_price) / $prev_price) * 100;
                    $fluctuation_rate_str = number_format($fluctuation_rate, 2) . '%';
                    if ($fluctuation_rate > 0) {
                        $rate_class = 'positive';
                    } elseif ($fluctuation_rate < 0) {
                        $rate_class = 'negative';
                    }
                }

                echo "<tr>";
                echo "<td>" . htmlspecialchars($row["stock_code"]) . "</td>";
                echo "<td>" . htmlspecialchars($row["stock_name"]) . "</td>";
                echo "<td>" . htmlspecialchars($row["market"]) . "</td>";
                echo "<td>" . (is_numeric($current_price) ? number_format($current_price) : 'N/A') . "</td>";
                echo "<td class='" . $rate_class . "'>" . $fluctuation_rate_str . "</td>";
                echo "<td>" . (is_numeric($prev_price) ? number_format($prev_price) : 'N/A') . "</td>";
                echo "<td>" . (is_numeric($row["circulating_shares"]) && $row["circulating_shares"] != '' ? number_format($row["circulating_shares"]) : 'N/A') . "</td>";
                
                // 뉴스 제목을 링크로 표시
                $news_title = htmlspecialchars($row["news_title"] ?? 'N/A');
                $news_link = htmlspecialchars($row["news_link"] ?? '#');
                if ($news_link !== '#' && $news_title !== 'N/A') {
                    echo "<td class='news-title'><a href='" . $news_link . "' target='_blank' class='news-link'>" . $news_title . "</a></td>";
                } else {
                    echo "<td class='news-title'>" . $news_title . "</td>";
                }
                
                echo "</tr>";
            }
            echo "</tbody>";
            echo "</table>";
        } else {
            echo "<p class='no-data'>데이터를 찾을 수 없습니다. Python 스크립트를 실행하여 데이터를 수집했는지 확인하세요.</p>";
        }

        $conn->close();
        ?>
    </div>

    <!-- 메인으로 가는 플로팅 버튼 -->
    <a href="index.php" class="floating-home" title="메인으로 이동">
        🏠 메인으로 이동
    </a>

    <script>
        document.addEventListener('DOMContentLoaded', function() {
            var searchInput = document.getElementById("searchInput");
            if (searchInput) {
                searchInput.addEventListener('input', searchTable);
                
                searchInput.addEventListener('keypress', function(event) {
                    if (event.key === "Enter") {
                        event.preventDefault();
                        searchTable();
                    }
                });
            }
        });
    </script>
</body>
</html>