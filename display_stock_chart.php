<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>주식 차트</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f4f4f4; }
        .container { max-width: 1200px; margin: auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { text-align: center; color: #0056b3; margin-bottom: 30px; }
        .search-form { text-align: center; margin-bottom: 20px; }
        .search-form input, .search-form select, .search-form button { padding: 10px; margin: 5px; font-size: 16px; }
        .chart-container { position: relative; height: 400px; margin: 20px 0; }
        .stock-info { background: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .error { color: #dc3545; text-align: center; padding: 20px; }
        .loading { text-align: center; padding: 20px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <h1>주식 차트</h1>
        
        <div class="search-form">
            <input type="text" id="stockCode" placeholder="종목 코드 입력 (예: 005930)">
            <select id="chartType">
                <option value="daily">일봉</option>
                <option value="weekly">주봉</option>
                <option value="minute">분봉</option>
            </select>
            <button onclick="loadChart()">차트 보기</button>
        </div>
        
        <div id="stockInfo" class="stock-info" style="display: none;"></div>
        <div id="loading" class="loading" style="display: none;">차트를 불러오는 중...</div>
        <div id="error" class="error" style="display: none;"></div>
        
        <div class="chart-container">
            <canvas id="stockChart"></canvas>
        </div>
    </div>

    <script>
        let chart = null;

        async function loadChart() {
            const stockCode = document.getElementById('stockCode').value.trim();
            const chartType = document.getElementById('chartType').value;
            
            if (!stockCode) {
                showError('종목 코드를 입력해주세요.');
                return;
            }

            showLoading(true);
            hideError();
            hideStockInfo();

            try {
                // 종목 정보 가져오기
                const stockInfoResponse = await fetch(`get_stock_details.php?search=${stockCode}`);
                const stockInfo = await stockInfoResponse.json();
                
                if (stockInfo && !stockInfo.error) {
                    showStockInfo(stockInfo);
                }

                // 차트 데이터 가져오기
                const chartResponse = await fetch(`fetch_chart_data.php?stock_code=${stockCode}&chart_type=${chartType}`);
                const chartData = await chartResponse.json();
                
                if (chartData.error) {
                    showError(chartData.error);
                    return;
                }

                if (!chartData || chartData.length === 0) {
                    showError('차트 데이터가 없습니다.');
                    return;
                }

                // 차트 그리기
                drawChart(chartData, stockCode, chartType);
                
            } catch (error) {
                showError('데이터를 불러오는 중 오류가 발생했습니다: ' + error.message);
            } finally {
                showLoading(false);
            }
        }

        function drawChart(data, stockCode, chartType) {
            const ctx = document.getElementById('stockChart').getContext('2d');
            
            // 기존 차트 제거
            if (chart) {
                chart.destroy();
            }

            // 데이터 정렬 (날짜순)
            data.sort((a, b) => a.date.localeCompare(b.date));
            
            // 차트 데이터 준비
            const labels = data.map(item => {
                const date = item.date;
                return date.substring(4, 6) + '/' + date.substring(6, 8);
            });
            
            const prices = data.map(item => item.close);
            const volumes = data.map(item => item.volume);

            chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: '종가',
                        data: prices,
                        borderColor: '#007bff',
                        backgroundColor: 'rgba(0, 123, 255, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: {
                            display: true,
                            text: `${stockCode} ${getChartTypeText(chartType)} 차트`
                        },
                        legend: {
                            display: true
                        }
                    },
                    scales: {
                        x: {
                            display: true,
                            title: {
                                display: true,
                                text: '날짜'
                            }
                        },
                        y: {
                            display: true,
                            title: {
                                display: true,
                                text: '가격 (원)'
                            }
                        }
                    },
                    interaction: {
                        intersect: false,
                        mode: 'index'
                    }
                }
            });
        }

        function getChartTypeText(chartType) {
            switch(chartType) {
                case 'daily': return '일봉';
                case 'weekly': return '주봉';
                case 'minute': return '분봉';
                default: return '';
            }
        }

        function showStockInfo(info) {
            const stockInfoDiv = document.getElementById('stockInfo');
            stockInfoDiv.innerHTML = `
                <h3>${info.stock_name} (${info.stock_code})</h3>
                <p><strong>시장:</strong> ${info.market}</p>
                <p><strong>현재가:</strong> ${info.current_price}</p>
                <p><strong>종가:</strong> ${info.closing_price}</p>
                <p><strong>전일종가:</strong> ${info.previous_day_closing_price}</p>
                <p><strong>유통주식수:</strong> ${info.circulating_shares}</p>
            `;
            stockInfoDiv.style.display = 'block';
        }

        function hideStockInfo() {
            document.getElementById('stockInfo').style.display = 'none';
        }

        function showError(message) {
            const errorDiv = document.getElementById('error');
            errorDiv.textContent = message;
            errorDiv.style.display = 'block';
        }

        function hideError() {
            document.getElementById('error').style.display = 'none';
        }

        function showLoading(show) {
            document.getElementById('loading').style.display = show ? 'block' : 'none';
        }

        // 엔터키로 검색
        document.getElementById('stockCode').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                loadChart();
            }
        });
    </script>
</body>
</html>