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
    </style>
</head>
<body>
    <div class="container">
        <h1>전체 종목 조회</h1>
        <input type="text" id="searchInput" onkeyup="searchTable()" placeholder="종목 코드 또는 종목명 검색...">

        <?php
        $config_file = __DIR__ . '/config.ini';

        if (!file_exists($config_file)) {
            echo "<p class=\"error\">오류: config.ini 파일을 찾을 수 없습니다.</p>";
            exit();
        }

        $config = parse_ini_file($config_file, true);

        if ($config === false || !isset($config['DB'])) {
            echo "<p class=\"error\">오류: config.ini 파일에서 DB 설정을 읽을 수 없습니다.</p>";
            exit();
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

        $sql = "SELECT stock_code, stock_name, market FROM all_stocks ORDER BY market, stock_name";
        $result = $conn->query($sql);

        if ($result->num_rows > 0) {
            echo "<table id=\"stockTable\">";
            echo "<thead><tr><th>종목 코드</th><th>종목명</th><th>시장</th></tr></thead>";
            echo "<tbody>";
            while($row = $result->fetch_assoc()) {
                echo "<tr><td>" . $row["stock_code"]. "</td><td>" . $row["stock_name"]. "</td><td>" . $row["market"]. "</td></tr>";
            }
            echo "</tbody>";
            echo "</table>";
        } else {
            echo "<p style=\"text-align: center;\">데이터베이스에 종목 정보가 없습니다. Python 스크립트를 실행하여 데이터를 수집해주세요.</p>";
        }

        $conn->close();
        ?>
    </div>

    <script>
        function searchTable() {
            var input, filter, table, tr, td, i, txtValue1, txtValue2;
            input = document.getElementById("searchInput");
            filter = input.value.toUpperCase();
            table = document.getElementById("stockTable");
            tr = table.getElementsByTagName("tr");

            for (i = 1; i < tr.length; i++) { // Skip header row
                td1 = tr[i].getElementsByTagName("td")[0]; // Stock Code
                td2 = tr[i].getElementsByTagName("td")[1]; // Stock Name
                if (td1 || td2) {
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