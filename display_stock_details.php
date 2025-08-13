<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>주식 상세 정보 및 차트</title>
    <style>
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
        .stock-info-card {
            border: 1px solid #eee;
            border-radius: 8px;
            padding: 15px;
            margin-top: 20px;
            background-color: #f9f9f9;
            display: none; /* Initially hidden */
        }
        .stock-info-card h2 {
            color: #0056b3;
            margin-top: 0;
        }
        .stock-info-card p {
            margin: 5px 0;
        }
        .chart-selection {
            margin-top: 20px;
            text-align: center;
        }
        .chart-selection label {
            margin: 0 10px;
            font-weight: bold;
        }
        .chart-data-container {
            margin-top: 20px;
            overflow-x: auto;
        }
        .chart-data-container table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }
        .chart-data-container th, .chart-data-container td {
            padding: 8px 12px;
            border: 1px solid #ddd;
            text-align: left;
            white-space: nowrap; /* Prevent wrapping for chart data */
        }
        .chart-data-container th {
            background-color: #007bff;
            color: white;
        }
        .chart-data-container tr:nth-child(even) {
            background-color: #f9f9f9;
        }
        .chart-data-container tr:hover {
            background-color: #f1f1f1;
        }
        .no-data {
            text-align: center;
            padding: 20px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>주식 상세 정보 및 차트</h1>

        <div class="search-container">
            <input type="text" id="stockSearchInput" placeholder="종목 코드 또는 종목명 입력 (예: 005930, 삼성전자)">
            <button id="searchButton">검색</button>
        </div>

        <div id="stockInfoCard" class="stock-info-card">
            <h2 id="stockNameDisplay"></h2>
            <p><strong>종목코드:</strong> <span id="stockCodeDisplay"></span></p>
            <p><strong>총 주식수:</strong> <span id="totalSharesDisplay"></span></p>
            <p><strong>업종:</strong> <span id="industryDisplay"></span></p>
            <p><strong>업태:</strong> <span id="businessTypeDisplay"></span></p>

            <div class="chart-selection">
                <label><input type="radio" name="chartType" value="daily" checked> 일봉 (53주)</label>
                <label><input type="radio" name="chartType" value="weekly"> 주봉 (3년)</label>
                <label><input type="radio" name="chartType" value="minute"> 분봉 (3일)</label>
            </div>
        </div>

        <div id="chartDataContainer" class="chart-data-container">
            <!-- Chart data will be loaded here by JavaScript -->
            <p class="no-data" id="chartNoDataMessage">차트 데이터를 불러오려면 종목을 검색하고 차트 유형을 선택하세요.</p>
        </div>
    </div>

    <script>
        const stockSearchInput = document.getElementById('stockSearchInput');
        const searchButton = document.getElementById('searchButton');
        const stockInfoCard = document.getElementById('stockInfoCard');
        const stockNameDisplay = document.getElementById('stockNameDisplay');
        const stockCodeDisplay = document.getElementById('stockCodeDisplay');
        const totalSharesDisplay = document.getElementById('totalSharesDisplay');
        const industryDisplay = document.getElementById('industryDisplay');
        const businessTypeDisplay = document.getElementById('businessTypeDisplay');
        const chartTypeRadios = document.querySelectorAll('input[name="chartType"]');
        const chartDataContainer = document.getElementById('chartDataContainer');
        const chartNoDataMessage = document.getElementById('chartNoDataMessage');

        let currentStockCode = '';

        searchButton.addEventListener('click', fetchStockDetails);
        stockSearchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                fetchStockDetails();
            }
        });

        chartTypeRadios.forEach(radio => {
            radio.addEventListener('change', function() {
                if (currentStockCode) {
                    console.log(`[display_stock_details] 차트 유형 변경: ${this.value}`);
                    fetchChartData(currentStockCode, this.value);
                }
            });
        });

        function formatNumber(value) {
            if (value === null || value === undefined || value === '') return '-';
            return new Intl.NumberFormat().format(value);
        }

        async function fetchStockDetails() {
            const searchTerm = stockSearchInput.value.trim();
            if (!searchTerm) {
                alert('종목 코드 또는 종목명을 입력해주세요.');
                return;
            }
            console.log(`[display_stock_details] 종목 상세 정보 요청: ${searchTerm}`);

            // Clear previous data
            stockInfoCard.style.display = 'none';
            chartDataContainer.innerHTML = '<p class="no-data" id="chartNoDataMessage">차트 데이터를 불러오려면 종목을 검색하고 차트 유형을 선택하세요.</p>';
            chartNoDataMessage.style.display = 'block';
            currentStockCode = '';

            try {
                const response = await fetch(`get_stock_details.php?search=${encodeURIComponent(searchTerm)}`);
                const data = await response.json();
                console.log(`[display_stock_details] 종목 상세 정보 응답:`, data);

                if (data && data.stock_code) {
                    currentStockCode = data.stock_code;
                    stockNameDisplay.textContent = data.stock_name || 'N/A'; // Assuming stock_name is returned
                    stockCodeDisplay.textContent = data.stock_code;
                    totalSharesDisplay.textContent = formatNumber(data.total_shares);
                    industryDisplay.textContent = data.industry || 'N/A';
                    businessTypeDisplay.textContent = data.business_type || 'N/A';
                    stockInfoCard.style.display = 'block';
                    console.log(`[display_stock_details] 종목 정보 업데이트: ${data.stock_name} (${data.stock_code})`);

                    // Automatically load the default chart type (daily)
                    const selectedChartType = document.querySelector('input[name="chartType"]:checked').value;
                    console.log(`[display_stock_details] 기본 차트 유형 로드: ${selectedChartType}`);
                    fetchChartData(currentStockCode, selectedChartType);

                } else {
                    alert('해당 종목을 찾을 수 없습니다.');
                    stockInfoCard.style.display = 'none';
                    console.warn(`[display_stock_details] 종목을 찾을 수 없음: ${searchTerm}`);
                }
            } catch (error) {
                console.error('[display_stock_details] Error fetching stock details:', error);
                alert('종목 정보를 가져오는 중 오류가 발생했습니다.');
                stockInfoCard.style.display = 'none';
            }
        }

        async function fetchChartData(stockCode, chartType) {
            console.log(`[display_stock_details] 차트 데이터 요청: 종목코드=${stockCode}, 차트유형=${chartType}`);
            chartDataContainer.innerHTML = '<p class="no-data">차트 데이터를 불러오는 중...</p>';
            chartNoDataMessage.style.display = 'none';

            try {
                const response = await fetch(`fetch_chart_data.php?stock_code=${encodeURIComponent(stockCode)}&chart_type=${encodeURIComponent(chartType)}`);
                const chartData = await response.json();
                console.log(`[display_stock_details] 차트 데이터 응답:`, chartData);

                if (chartData && chartData.length > 0) {
                    renderChartTable(chartData, chartType);
                    console.log(`[display_stock_details] 차트 데이터 테이블 렌더링 완료.`);
                } else {
                    chartDataContainer.innerHTML = '<p class="no-data">선택된 차트 유형의 데이터가 없습니다.</p>';
                    console.warn(`[display_stock_details] 차트 데이터 없음: 종목코드=${stockCode}, 차트유형=${chartType}`);
                }
            } catch (error) {
                console.error('[display_stock_details] Error fetching chart data:', error);
                chartDataContainer.innerHTML = '<p class="no-data">차트 데이터를 가져오는 중 오류가 발생했습니다.</p>';
            }
        }

        function renderChartTable(data, chartType) {
            console.log(`[display_stock_details] 차트 테이블 렌더링 시작. 데이터 길이: ${data.length}, 차트 유형: ${chartType}`, data);
            let tableHtml = '<table><thead><tr>';
            let headers = [];

            // Determine headers based on chart type and data structure
            if (data.length > 0) {
                // Assuming chart data objects have consistent keys
                headers = Object.keys(data[0]);
                // Filter out unwanted keys if any, or reorder
                // Example: if 'stk_cd' is always present and not needed in table
                headers = headers.filter(header => header !== 'stk_cd');
            }

            // Map internal API field names to user-friendly names
            const headerMap = {
                "stk_date": "날짜",
                "stk_prc": "현재가",
                "stk_oprc": "시가",
                "stk_hprc": "고가",
                "stk_lprc": "저가",
                "stk_clprc": "종가",
                "stk_vol": "거래량",
                "stk_chgrt": "등락률",
                "stk_chg": "대비",
                "stk_sign": "부호",
                "stk_adj_prc": "수정주가",
                "stk_adj_rate": "수정비율",
                "stk_adj_date": "수정일",
                "stk_adj_type": "수정구분", // Add more mappings as needed based on actual API response
                // get_stock_chart_data.py에서 반환하는 필드명에 맞게 추가
                "date": "날짜",
                "open_pric": "시가",
                "high_pric": "고가",
                "low_pric": "저가",
                "close": "종가",
                "volume": "거래량",
                "cur_prc": "현재가",
                "trde_qty": "거래량",
                "trde_prica": "거래대금",
                "dt": "날짜",
                "upd_stkpc_tp": "등락구분",
                "upd_rt": "등락률",
                "bic_inds_tp": "업종구분",
                "sm_inds_tp": "소업종구분",
                "stk_infr": "종목정보",
                "upd_stkpc_event": "수정주가이벤트",
                "pred_close_pric": "예상체결가",
                "SMA_5": "SMA_5",
                "SMA_10": "SMA_10",
                "SMA_20": "SMA_20",
                "SMA_60": "SMA_60",
                "SMA_120": "SMA_120",
                "SMA_240": "SMA_240",
            };

            headers.forEach(header => {
                tableHtml += `<th>${headerMap[header] || header}</th>`;
            });
            tableHtml += '</tr></thead><tbody>';

            data.forEach(row => {
                tableHtml += '<tr>';
                headers.forEach(header => {
                    let displayValue = row[header];
                    // Format numbers for price/volume, etc.
                    if (['stk_prc', 'stk_oprc', 'stk_hprc', 'stk_lprc', 'stk_clprc', 'stk_vol', 'open_pric', 'high_pric', 'low_pric', 'close', 'volume', 'cur_prc', 'trde_qty', 'trde_prica'].includes(header)) {
                        displayValue = formatNumber(displayValue);
                    }
                    // Format percentage for 등락률
                    if (header === 'stk_chgrt' || header === 'upd_rt') {
                        displayValue = parseFloat(displayValue).toFixed(2) + '%';
                    }
                    tableHtml += `<td>${displayValue}</td>`;
                });
                tableHtml += '</tr>';
            });

            tableHtml += '</tbody></table>';
            chartDataContainer.innerHTML = tableHtml;
        }
    </script>
</body>
</html>