<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>전체 종목 조회 (테마 및 뉴스 포함)</title>
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
            margin-bottom: 20px;
        }
        #searchInput {
            width: 100%;
            padding: 10px;
            margin-bottom: 20px;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            padding: 12px;
            border: 1px solid #ddd;
            text-align: left;
            white-space: nowrap;
        }
        td.news-title {
            white-space: normal; /* 뉴스 제목은 여러 줄로 표시될 수 있도록 설정 */
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
        .news-link {
            color: #0056b3;
            text-decoration: none;
        }
        .news-link:hover {
            text-decoration: underline;
        }
        .positive {
            color: red;
        }
        .negative {
            color: blue;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>전체 종목 조회 (테마 및 뉴스 포함)</h1>
        <input type="text" id="searchInput" onkeyup="searchTable()" placeholder="종목, 테마, 또는 뉴스 내용 검색...">

        <?php
        // DB 연결 설정 로드
        $config_file = __DIR__ . '/config.ini';

        if (!file_exists($config_file)) {
            die("<p class=\"error\">오류: config.ini 파일을 찾을 수 없습니다.</p>");
        }

        $config = parse_ini_file($config_file, true);

        if ($config === false || !isset($config['DB'])) {
            die("<p class=\"error\">오류: config.ini 파일에 [DB] 섹션 또는 필요한 키가 누락되었습니다.</p>");
        }

        $db_host = $config['DB']['HOST'];
        $db_user = $config['DB']['USER'];
        $db_password = $config['DB']['PASSWORD'];
        $db_name = $config['DB']['DATABASE'];
        $db_port = $config['DB']['PORT'];

        // MySQL 데이터베이스 연결
        $conn = new mysqli($db_host, $db_user, $db_password, $db_name, $db_port);

        if ($conn->connect_error) {
            die("<p class=\"error\">데이터베이스 연결 실패: " . $conn->connect_error . "</p>");
        }
        
        // UTF-8 인코딩 설정
        $conn->set_charset("utf8mb4");

        // SQL 쿼리 수정: all_stocks, stock_details, stock_news 테이블을 조인합니다.
        $sql = "
            SELECT
                a.stock_code,
                a.stock_name,
                a.market,
                d.current_price,
                d.previous_day_closing_price,
                (SELECT theme FROM stock_news WHERE stock_code = a.stock_code ORDER BY pub_date DESC LIMIT 1) AS theme,
                (SELECT title FROM stock_news WHERE stock_code = a.stock_code ORDER BY pub_date DESC LIMIT 1) AS news_title,
                (SELECT link FROM stock_news WHERE stock_code = a.stock_code ORDER BY pub_date DESC LIMIT 1) AS news_link
            FROM
                all_stocks a
            LEFT JOIN
                stock_details d ON a.stock_code = d.stock_code
            ORDER BY
                a.stock_name ASC;
        ";
        
        $result = $conn->query($sql);

        if ($result && $result->num_rows > 0) {
            echo "<table id='stockTable'>";
            echo "<thead><tr><th>종목코드</th><th>종목명</th><th>시장</th><th>현재가</th><th>등락률</th><th>테마</th><th>최신 뉴스</th></tr></thead>";
            echo "<tbody>";
            while($row = $result->fetch_assoc()) {
                // 등락률 계산
                $fluctuation_rate_str = 'N/A';
                $rate_class = '';
                if (is_numeric($row["current_price"]) && is_numeric($row["previous_day_closing_price"]) && $row["previous_day_closing_price"] != 0) {
                    $current_price = floatval($row["current_price"]);
                    $prev_close_price = floatval($row["previous_day_closing_price"]);
                    $fluctuation_rate = (($current_price - $prev_close_price) / $prev_close_price) * 100;
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
                echo "<td>" . (is_numeric($row["current_price"]) ? number_format($row["current_price"]) : 'N/A') . "</td>";
                echo "<td class='" . $rate_class . "'>" . $fluctuation_rate_str . "</td>";
                echo "<td>" . htmlspecialchars($row["theme"] ?? 'N/A') . "</td>";
                
                // 뉴스 제목을 링크로 만듭니다.
                $news_title = htmlspecialchars($row["news_title"] ?? 'N/A');
                $news_link = htmlspecialchars($row["news_link"] ?? '#');
                if ($news_link !== '#') {
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

    <script>
        function searchTable() {
            var input, filter, table, tr, i, txtValue;
            input = document.getElementById("searchInput");
            filter = input.value.toUpperCase();
            table = document.getElementById("stockTable");
            if (!table) return;

            tr = table.getElementsByTagName("tr");

            for (i = 1; i < tr.length; i++) { // 헤더 행 건너뛰기
                // 모든 td를 순회하며 검색
                let display = "none";
                let tds = tr[i].getElementsByTagName("td");
                for (let j = 0; j < tds.length; j++) {
                    if (tds[j]) {
                        txtValue = tds[j].textContent || tds[j].innerText;
                        if (txtValue.toUpperCase().indexOf(filter) > -1) {
                            display = "";
                            break; // 일치하는 셀을 찾으면 루프 중단
                        }
                    }
                }
                tr[i].style.display = display;
            }
        }
    </script>
</body>
</html>