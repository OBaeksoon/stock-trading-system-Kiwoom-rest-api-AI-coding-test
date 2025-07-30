<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>상승률 상위 30위 종목 테마 및 뉴스</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 20px;
            background-color: #f8f9fa;
            color: #212529;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background-color: #ffffff;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        }
        h1 {
            color: #0056b3;
            text-align: center;
            margin-bottom: 30px;
        }
        #searchInput {
            width: 100%;
            padding: 12px;
            margin-bottom: 25px;
            border: 1px solid #ced4da;
            border-radius: 5px;
            box-sizing: border-box;
            font-size: 16px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            padding: 15px;
            border-bottom: 1px solid #dee2e6;
            text-align: left;
            vertical-align: middle;
        }
        th {
            background-color: #007bff;
            color: white;
            position: sticky;
            top: 0;
            font-weight: 600;
        }
        tr:nth-child(even) {
            background-color: #f8f9fa;
        }
        tr:hover {
            background-color: #e9ecef;
        }
        .error, .no-data {
            color: #dc3545;
            text-align: center;
            margin-top: 20px;
            font-size: 18px;
        }
        .news-link {
            color: #0056b3;
            text-decoration: none;
            font-weight: 500;
        }
        .news-link:hover {
            text-decoration: underline;
        }
        .positive { color: #dc3545; font-weight: bold; }
        .negative { color: #007bff; font-weight: bold; }
        .theme-badge {
            display: inline-block;
            padding: 5px 10px;
            border-radius: 15px;
            background-color: #6c757d;
            color: white;
            font-size: 12px;
        }
        .rank {
            font-weight: bold;
            text-align: center;
        }
        .home-link {
            display: block;
            text-align: center;
            margin-top: 40px;
            text-decoration: none;
            color: #007bff;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>상승률 상위 30위 종목 테마 & 뉴스</h1>
        <input type="text" id="searchInput" onkeyup="searchTable()" placeholder="종목명, 테마, 또는 뉴스 내용으로 검색...">

        <?php
        // DB 연결 설정 로드
        $config = parse_ini_file(__DIR__ . '/config.ini');
        if (!$config) {
            die("<p class=\"error\">오류: config.ini 파일을 찾을 수 없습니다.</p>");
        }

        $conn = new mysqli($config['HOST'], $config['USER'], $config['PASSWORD'], $config['DATABASE'], $config['PORT']);
        if ($conn->connect_error) {
            die("<p class=\"error\">데이터베이스 연결 실패: " . $conn->connect_error . "</p>");
        }
        $conn->set_charset("utf8mb4");

        // SQL 쿼리: 상위 30위 종목 정보와 각 종목의 최신 뉴스 3개를 가져옵니다.
        $sql = "
            SELECT
                t.rank,
                t.stock_code,
                t.stock_name,
                t.current_price,
                t.change_rate,
                n.title AS news_title,
                n.link AS news_link,
                n.theme,
                n.pub_date
            FROM
                top_30_rising_stocks t
            LEFT JOIN (
                SELECT
                    *,
                    ROW_NUMBER() OVER(PARTITION BY stock_code ORDER BY pub_date DESC) as rn
                FROM stock_news
            ) n ON t.stock_code = n.stock_code AND n.rn <= 3
            ORDER BY
                t.rank ASC, n.pub_date DESC;
        ";
        
        $result = $conn->query($sql);

        if ($result && $result->num_rows > 0) {
            echo "<table id='stockTable'>";
            echo "<thead><tr><th>순위</th><th>종목명 (코드)</th><th>현재가</th><th>등락률</th><th>테마</th><th>최신 뉴스</th></tr></thead>";
            echo "<tbody>";
            
            $current_stock_code = null;
            while($row = $result->fetch_assoc()) {
                if ($row['stock_code'] !== $current_stock_code) {
                    if ($current_stock_code !== null) echo "</td></tr>"; // 이전 행 닫기
                    $current_stock_code = $row['stock_code'];
                    
                    echo "<tr>";
                    echo "<td class='rank'>" . htmlspecialchars($row["rank"]) . "</td>";
                    echo "<td>" . htmlspecialchars($row["stock_name"]) . "<br><small>(" . htmlspecialchars($row["stock_code"]) . ")</small></td>";
                    echo "<td>" . number_format($row["current_price"]) . "</td>";
                    
                    $rate_class = $row["change_rate"] > 0 ? 'positive' : ($row["change_rate"] < 0 ? 'negative' : '');
                    echo "<td class='" . $rate_class . "'>" . htmlspecialchars($row["change_rate"]) . "%</td>";
                    
                    echo "<td>";
                    if (!empty($row["theme"])) {
                        echo "<span class='theme-badge'>" . htmlspecialchars($row["theme"]) . "</span>";
                    } else {
                        echo "N/A";
                    }
                    echo "</td>";
                    
                    echo "<td>"; // 뉴스 셀 시작
                }
                
                // 뉴스 목록
                if (!empty($row['news_title'])) {
                    echo "<div style='margin-bottom: 8px;'>";
                    echo "<a href='" . htmlspecialchars($row["news_link"]) . "' target='_blank' class='news-link'>" . htmlspecialchars($row["news_title"]) . "</a>";
                    echo "<br><small style='color:#6c757d;'>" . htmlspecialchars($row["pub_date"]) . "</small>";
                    echo "</div>";
                } else {
                     if ($current_stock_code === $row['stock_code'] && !isset($news_printed[$row['stock_code']])) {
                        echo "뉴스가 없습니다.";
                        $news_printed[$row['stock_code']] = true;
                    }
                }
            }
            echo "</td></tr>"; // 마지막 행 닫기
            
            echo "</tbody>";
            echo "</table>";
        } else {
            echo "<p class='no-data'>데이터를 찾을 수 없습니다. <br>먼저 'get_top_30_rising_stocks.py'를 실행한 후, 'get_top_30_themes_news.py'를 실행하여 데이터를 수집하세요.</p>";
        }

        $conn->close();
        ?>
        <a href="index.php" class="home-link">메인으로 돌아가기</a>
    </div>

    <script>
        function searchTable() {
            const input = document.getElementById("searchInput");
            const filter = input.value.toUpperCase();
            const table = document.getElementById("stockTable");
            if (!table) return;
            const tr = table.getElementsByTagName("tr");

            for (let i = 1; i < tr.length; i++) {
                let display = "none";
                const tds = tr[i].getElementsByTagName("td");
                for (let j = 0; j < tds.length; j++) {
                    if (tds[j]) {
                        const txtValue = tds[j].textContent || tds[j].innerText;
                        if (txtValue.toUpperCase().indexOf(filter) > -1) {
                            display = "";
                            break;
                        }
                    }
                }
                tr[i].style.display = display;
            }
        }
    </script>
</body>
</html>
