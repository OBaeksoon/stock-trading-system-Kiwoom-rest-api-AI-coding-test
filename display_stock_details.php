<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>주식 상세 정보</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f4f4f4; color: #333; }
        .container { max-width: 1200px; margin: auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { text-align: center; color: #0056b3; margin-bottom: 30px; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 12px 15px; border: 1px solid #ddd; text-align: left; }
        th { background-color: #007bff; color: white; }
        tr:nth-child(even) { background-color: #f9f9f9; }
        tr:hover { background-color: #f1f1f1; }
        .no-data { text-align: center; padding: 20px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <h1>주식 상세 정보</h1>
        <?php
        $servername = "localhost";
        $username = "stock"; // Replace with your DB username
        $password = "stock"; // Replace with your DB password
        $dbname = "stock";   // Replace with your DB name

        // Create connection
        $conn = new mysqli($servername, $username, $password, $dbname);

        // Check connection
        if ($conn->connect_error) {
            die("<p class='no-data'>데이터베이스 연결 실패: " . $conn->connect_error . "</p>");
        }

        $sql = "SELECT stock_code, stock_name, market, current_price, closing_price, previous_day_closing_price, circulating_shares, updated_at FROM stock_details ORDER BY stock_name ASC";
        $result = $conn->query($sql);

        if ($result->num_rows > 0) {
            echo "<table>";
            echo "<thead><tr><th>종목코드</th><th>종목명</th><th>시장</th><th>현재가</th><th>종가</th><th>전일종가</th><th>유통주식수</th><th>업데이트 시각</th></tr></thead>";
            echo "<tbody>";
            // Output data of each row
            while($row = $result->fetch_assoc()) {
                echo "<tr>";
                echo "<td>" . htmlspecialchars($row["stock_code"]) . "</td>";
                echo "<td>" . htmlspecialchars($row["stock_name"]) . "</td>";
                echo "<td>" . htmlspecialchars($row["market"]) . "</td>";
                echo "<td>" . htmlspecialchars($row["current_price"]) . "</td>";
                echo "<td>" . htmlspecialchars($row["closing_price"]) . "</td>";
                echo "<td>" . htmlspecialchars($row["previous_day_closing_price"]) . "</td>";
                echo "<td>" . htmlspecialchars($row["circulating_shares"]) . "</td>";
                echo "<td>" . htmlspecialchars($row["updated_at"]) . "</td>";
                echo "</tr>";
            }
            echo "</tbody>";
            echo "</table>";
        } else {
            echo "<p class='no-data'>데이터를 찾을 수 없습니다. Python 스크립트를 실행하여 데이터를 수집해주세요.</p>";
        }
        $conn->close();
        ?>
    </div>
</body>
</html>
