<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>전체 종목 조회</title>
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
        }
        th {
            background-color: #007bff;
            color: white;
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
    </style>
</head>
<body>
    <div class="container">
        <h1>전체 종목 조회</h1>
        <input type="text" id="searchInput" onkeyup="searchTable()" placeholder="종목 코드 또는 종목명 검색...">

        <?php
        // DB 연결 설정 로드 (config.ini 파일은 동일 디렉토리에 있다고 가정)
        $config_file = __DIR__ . '/config.ini';

        if (!file_exists($config_file)) {
            die("<p class=\"error\">오류: config.ini 파일을 찾을 수 없습니다.</p>");
        }

        $config = parse_ini_file($config_file, true);

        // config.ini 파일의 [DB] 섹션에 맞게 수정
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

        // SQL 쿼리 수정: Python 스크립트가 사용하는 컬럼명에 맞춤
        $sql = "SELECT code, name, marketName, current_price, fluctuation_rate, base_price FROM all_stocks ORDER BY name ASC";
        $result = $conn->query($sql);

        if ($result && $result->num_rows > 0) {
            echo "<table id='stockTable'>";
            echo "<thead><tr><th>종목코드</th><th>종목명</th><th>시장</th><th>현재가</th><th>등락률</th><th>기준가</th></tr></thead>";
            echo "<tbody>";
            while($row = $result->fetch_assoc()) {
                $fluctuation_rate = isset($row['fluctuation_rate']) ? number_format($row['fluctuation_rate'], 2) . '%' : 'N/A';
                
                echo "<tr>";
                echo "<td>" . htmlspecialchars($row["code"]) . "</td>";
                echo "<td>" . htmlspecialchars($row["name"]) . "</td>";
                echo "<td>" . htmlspecialchars($row["marketName"]) . "</td>";
                echo "<td>" . htmlspecialchars($row["current_price"]) . "</td>";
                echo "<td>" . htmlspecialchars($fluctuation_rate) . "</td>";
                echo "<td>" . htmlspecialchars($row["base_price"]) . "</td>";
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
            var input, filter, table, tr, td1, td2, i, txtValue1, txtValue2;
            input = document.getElementById("searchInput");
            filter = input.value.toUpperCase();
            table = document.getElementById("stockTable");
            if (!table) return;

            tr = table.getElementsByTagName("tr");

            for (i = 1; i < tr.length; i++) { // Skip header row
                td1 = tr[i].getElementsByTagName("td")[0]; // Stock Code
                td2 = tr[i].getElementsByTagName("td")[1]; // Stock Name
                if (td1 && td2) {
                    txtValue1 = td1.textContent || td1.innerText;
                    txtValue2 = td2.textContent || td2.innerText;
                    if (txtValue1.toUpperCase().indexOf(filter) > -1 || txtValue2.toUpperCase().indexOf(filter) > -1) {
                        tr[i].style.display = "";
                    } else {
                        tr[i].style.display = "none";
                    }
                }
            }
        }
    </script>
</body>
</html>