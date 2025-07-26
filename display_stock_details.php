<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>주식 상세 정보</title>
    <style>
        .search-container {
            margin-bottom: 20px;
            text-align: center;
        }
        .search-container input[type="text"] {
            width: 80%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
            font-size: 16px;
            transition: border-color 0.3s ease;
        }
        .search-container input[type="text"]:focus {
            outline: none;
            border-color: #007bff;
            box-shadow: 0 0 5px rgba(0, 123, 255, 0.3);
        }
        

        
        body { 
            font-family: Arial, sans-serif; 
            margin: 20px; 
            background-color: #f4f4f4; 
            color: #333; 
        }
        .container { 
            max-width: 1200px; 
            margin: auto; 
            background: #fff; 
            padding: 20px; 
            border-radius: 8px; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.1); 
        }
        h1 { 
            text-align: center; 
            color: #0056b3; 
            margin-bottom: 30px; 
        }
        table { 
            width: 100%; 
            border-collapse: collapse; 
            margin-top: 20px; 
        }
        th, td { 
            padding: 12px 15px; 
            border: 1px solid #ddd; 
            text-align: left; 
        }
        th { 
            background-color: #007bff; 
            color: white; 
        }
        tr:nth-child(even) { 
            background-color: #f9f9f9; 
        }
        tr:hover { 
            background-color: #f1f1f1; 
        }
        .no-data { 
            text-align: center; 
            padding: 20px; 
            color: #666; 
        }
        .search-result-info {
            text-align: center;
            margin: 10px 0;
            color: #666;
            font-size: 14px;
        }
        .highlight {
            background-color: #ffeb3b;
            font-weight: bold;
        }
        .positive {
            color: #dc3545;
        }
        .negative {
            color: #007bff;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>주식 상세 정보</h1>
        <div class="search-container">
            <input type="text" id="stockSearchInput" placeholder="종목 코드 또는 종목명으로 검색...">
        </div>
        <div id="searchResultInfo" class="search-result-info"></div>

        <?php
        $servername = "localhost";
        $username = "stock"; // Replace with your DB username
        $password = "01P16NYJ3jwcCl9"; // Replace with your DB password
        $dbname = "stock";   // Replace with your DB name

        // Create connection
        $conn = new mysqli($servername, $username, $password, $dbname);

        // Check connection
        if ($conn->connect_error) {
            die("<p class='no-data'>데이터베이스 연결 실패: " . $conn->connect_error . "</p>");
        }

        function formatNumber($value) {
            if (empty($value) || $value === '0') return $value;
            
            $sign = '';
            $class = '';
            $numValue = $value;
            
            if (substr($value, 0, 1) === '+') {
                $sign = '+';
                $class = 'positive';
                $numValue = substr($value, 1);
            } elseif (substr($value, 0, 1) === '-') {
                $sign = '-';
                $class = 'negative';
                $numValue = substr($value, 1);
            }
            
            if (is_numeric($numValue)) {
                $formatted = number_format($numValue);
                return "<span class='$class'>$sign$formatted</span>";
            }
            
            return $value;
        }

        $sql = "SELECT stock_code, stock_name, market, current_price, closing_price, previous_day_closing_price, circulating_shares, updated_at FROM stock_details WHERE circulating_shares IS NOT NULL AND circulating_shares != '' AND circulating_shares != '0' ORDER BY stock_name ASC";
        $result = $conn->query($sql);

        if ($result->num_rows > 0) {
            echo "<table id='stockTable'>";
            echo "<thead><tr><th>종목코드</th><th>종목명</th><th>시장</th><th>현재가</th><th>종가</th><th>전일종가</th><th>유통주식수</th><th>업데이트 시각</th></tr></thead>";
            echo "<tbody>";
            
            while($row = $result->fetch_assoc()) {
                echo "<tr>";
                echo "<td class='stock-code'>" . htmlspecialchars($row["stock_code"]) . "</td>";
                echo "<td class='stock-name'>" . htmlspecialchars($row["stock_name"]) . "</td>";
                echo "<td>" . htmlspecialchars($row["market"]) . "</td>";
                echo "<td>" . formatNumber($row["current_price"]) . "</td>";
                echo "<td>" . formatNumber($row["closing_price"]) . "</td>";
                echo "<td>" . formatNumber($row["previous_day_closing_price"]) . "</td>";
                echo "<td class='circulating-shares'>" . formatNumber($row["circulating_shares"]) . "</td>";
                echo "<td>" . htmlspecialchars($row["updated_at"]) . "</td>";
                echo "</tr>";
            }
            echo "</tbody>";
            echo "</table>";
        } else {
            echo "<p class='no-data'>유통주식수가 있는 데이터를 찾을 수 없습니다. Python 스크립트를 실행하여 데이터를 수집해주세요.</p>";
        }
        $conn->close();
        ?>
    </div>

    <script>
        function searchStockTable() {
            var input = document.getElementById("stockSearchInput");
            
            if (!input) return;
            
            var filter = input.value.toUpperCase();
            var table = document.getElementById("stockTable");
            
            if (!table) return;
            
            var tbody = table.getElementsByTagName("tbody")[0];
            if (!tbody) return;
            
            var tr = tbody.getElementsByTagName("tr");
            var visibleCount = 0;
            var totalCount = tr.length;

            // 기존 하이라이트 제거
            removeHighlights();

            // 각 행을 검사
            for (var i = 0; i < tr.length; i++) {
                var row = tr[i];
                var stockCode = row.getElementsByClassName("stock-code")[0];
                var stockName = row.getElementsByClassName("stock-name")[0];
                
                if (!stockCode || !stockName) continue;
                
                var codeText = (stockCode.textContent || stockCode.innerText || "").toUpperCase();
                var nameText = (stockName.textContent || stockName.innerText || "").toUpperCase();
                
                // 검색어 매칭
                var matchesSearch = filter === "" || 
                                  codeText.indexOf(filter) > -1 || 
                                  nameText.indexOf(filter) > -1;
                
                if (matchesSearch) {
                    row.style.display = "";
                    visibleCount++;
                    
                    // 검색어 하이라이트
                    if (filter.length > 0) {
                        highlightText(stockCode, filter);
                        highlightText(stockName, filter);
                    }
                } else {
                    row.style.display = "none";
                }
            }

            // 검색 결과 정보 업데이트
            updateSearchResultInfo(input.value, visibleCount, totalCount);
        }

        function highlightText(element, searchTerm) {
            var originalText = element.textContent || element.innerText;
            var regex = new RegExp('(' + searchTerm + ')', 'gi');
            var highlightedText = originalText.replace(regex, '<span class="highlight">$1</span>');
            element.innerHTML = highlightedText;
        }

        function removeHighlights() {
            var highlights = document.querySelectorAll('.highlight');
            highlights.forEach(function(highlight) {
                var parent = highlight.parentNode;
                parent.replaceChild(document.createTextNode(highlight.textContent), highlight);
                parent.normalize();
            });
        }

        function updateSearchResultInfo(searchTerm, visibleCount, totalCount) {
            var infoDiv = document.getElementById("searchResultInfo");
            if (!infoDiv) return;
            
            if (searchTerm.trim() === "") {
                infoDiv.textContent = "전체 " + totalCount + "개 종목";
            } else {
                infoDiv.textContent = "검색 결과: " + visibleCount + "개 / 전체 " + totalCount + "개";
            }
        }

        // 검색 입력 이벤트 리스너
        document.addEventListener("DOMContentLoaded", function() {
            var searchInput = document.getElementById("stockSearchInput");
            if (searchInput) {
                searchInput.addEventListener("keyup", searchStockTable);
                // 초기 정보 표시
                searchStockTable();
            }
        });
    </script>
</body>
</html>