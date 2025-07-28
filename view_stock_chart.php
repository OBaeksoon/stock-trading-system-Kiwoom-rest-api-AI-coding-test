<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HTS 스타일 주식 차트</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@2.0.0/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-chart-financial@0.1.0/dist/chartjs-chart-financial.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-crosshair@1.2.0/dist/chartjs-plugin-crosshair.min.js"></script>
    <style>
        :root {
            --bg-color: #ffffff;
            --text-color: #212529;
            --border-color: #dee2e6;
            --container-bg: #ffffff;
            --header-bg: #f8f9fa;
            --btn-bg: #f8f9fa;
            --btn-bg-active: #e2e6ea;
            --red-color: #d84033;
            --blue-color: #1260cc;
        }
        html.dark-mode {
            --bg-color: #1c1c1e;
            --text-color: #e2e2e2;
            --border-color: #38383a;
            --container-bg: #2a2a2c;
            --header-bg: #1c1c1e;
            --btn-bg: #3a3a3c;
            --btn-bg-active: #505052;
        }
        body { font-family: 'Malgun Gothic', '맑은 고딕', dotum, '돋움', sans-serif; margin: 0; padding: 15px; background-color: var(--bg-color); color: var(--text-color); font-size: 14px; }
        .container { max-width: 1400px; margin: auto; background: var(--container-bg); padding: 15px; border: 1px solid var(--border-color); }
        .controls-wrapper, .chart-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; flex-wrap: wrap; gap: 10px; padding: 8px; border-bottom: 1px solid var(--border-color); }
        .chart-header { background-color: var(--header-bg); }
        .stock-info { display: flex; align-items: baseline; gap: 15px; }
        .stock-info .name { font-size: 20px; font-weight: bold; }
        .stock-info .code { font-size: 14px; color: #888; }
        .stock-info .price { font-size: 20px; font-weight: bold; }
        .stock-info .change { font-size: 14px; }
        .stock-info .volume-info { font-size: 14px; }
        .price.up, .change.up { color: var(--red-color); }
        .price.down, .change.down { color: var(--blue-color); }
        .search-controls { display: flex; align-items: center; gap: 5px; }
        .search-controls input { padding: 8px; border: 1px solid #ccc; background-color: var(--bg-color); color: var(--text-color); }
        .search-controls button, .chart-type-controls button { padding: 8px 15px; border: 1px solid var(--border-color); background-color: var(--btn-bg); color: var(--text-color); cursor: pointer; }
        .chart-type-controls button.active { background-color: var(--btn-bg-active); font-weight: bold; }
        .chart-options { display: flex; align-items: center; gap: 15px; flex-wrap: wrap; }
        .ma-toggles { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 10px; padding-left: 8px; }
        .ma-toggles label { font-size: 13px; user-select: none; white-space: nowrap; cursor: pointer; }
        .price-chart-container { position: relative; height: 45vh; width: 100%; }
        .volume-chart-container { position: relative; height: 18vh; width: 100%; margin-top: 0; }
        #loading, #error { text-align: center; font-size: 16px; color: #888; display: none; padding: 20px; }
        #error { color: #d9534f; }
    </style>
</head>
<body>

<div class="container">
    <div class="chart-header" style="display: none;">
        <div class="stock-info">
            <span id="stockName" class="name"></span>
            <span id="stockCode" class="code"></span>
            <span id="stockPrice" class="price"></span>
            <span id="stockChange" class="change"></span>
            <span id="stockVolume" class="volume-info"></span>
        </div>
        <div>
            <label><input type="checkbox" id="darkModeToggle" onchange="toggleDarkMode(this.checked)"> 다크모드</label>
        </div>
    </div>
    <div class="controls-wrapper">
        <div class="search-controls">
            <input type="text" id="searchInput" placeholder="종목명 또는 코드 입력" onkeyup="if(event.keyCode===13) document.getElementById('searchButton').click()">
            <button id="searchButton" onclick="searchStock()">조회</button>
        </div>
        <div class="chart-options" style="display: none;">
             <div class="chart-type-controls">
                <button id="btn-daily" onclick="loadChartData('daily')">일봉</button>
                <button id="btn-weekly" onclick="loadChartData('weekly')">주봉</button>
                <button id="btn-minute" onclick="loadChartData('minute')">분봉</button>
            </div>
            <label><input type="checkbox" id="autoRefreshToggle" onchange="toggleAutoRefresh(this.checked)"> 자동갱신</label>
        </div>
    </div>
    <div class="ma-toggles" style="display: none;"></div>

    <div class="price-chart-container">
        <canvas id="priceChartCanvas"></canvas>
    </div>
    <div class="volume-chart-container">
        <canvas id="volumeChartCanvas"></canvas>
    </div>
    <p id="loading">로딩 중...</p>
    <p id="error"></p>
</div>

<script>
    const priceCtx = document.getElementById('priceChartCanvas').getContext('2d');
    const volumeCtx = document.getElementById('volumeChartCanvas').getContext('2d');
    const [searchInput, loadingEl, errorEl] = [document.getElementById('searchInput'), document.getElementById('loading'), document.getElementById('error')];
    const [chartHeaderEl, chartOptionsEl, maTogglesEl] = [document.querySelector('.chart-header'), document.querySelector('.chart-options'), document.querySelector('.ma-toggles')];

    let priceChart = null, volumeChart = null;
    let currentStockCode = '', currentStockName = '', currentChartType = 'daily';
    let autoRefreshInterval = null;

    // HTS 스타일 이동평균선 설정
    const MA_CONFIG = [
        { period: 5, color: '#ff9800', width: 1, checked: true },   // 주황
        { period: 10, color: '#ffeb3b', width: 1, checked: false },  // 노랑
        { period: 20, color: '#4caf50', width: 1, checked: true },  // 초록
        { period: 60, color: '#2196f3', width: 1.5, checked: true },  // 파랑
        { period: 120, color: '#9c27b0', width: 1.5, checked: false }, // 보라
        { period: 240, color: '#795548', width: 2, checked: false }, // 갈색
    ];

    document.addEventListener('DOMContentLoaded', () => {
        searchInput.value = "웅진";
        searchStock();
    });

    async function searchStock() {
        const query = searchInput.value.trim();
        if (!query) { alert('종목명 또는 종목 코드를 입력해주세요.'); return; }
        clearState();
        const isCode = !isNaN(query) && query.length === 6;
        if (isCode) {
            currentStockCode = query;
            currentStockName = `종목코드: ${query}`;
            await loadChartData(currentChartType);
        } else {
            loadingEl.style.display = 'block';
            try {
                const response = await fetch(`search_stock_by_name.php?stock_name=${encodeURIComponent(query)}`);
                const data = await response.json();
                if (data.error) throw new Error(data.error);
                currentStockCode = data.stock_code;
                currentStockName = data.found_name || query;
                await loadChartData(currentChartType);
            } catch (error) {
                showError(error.message);
            } finally {
                loadingEl.style.display = 'none';
            }
        }
    }

    async function loadChartData(chartType) {
        currentChartType = chartType;
        if (!currentStockCode) { alert('먼저 종목을 조회해주세요.'); return; }
        loadingEl.style.display = 'block';
        errorEl.style.display = 'none';
        try {
            const response = await fetch(`fetch_chart_data.php?stock_code=${currentStockCode}&chart_type=${chartType}`);
            if (!response.ok) throw new Error(`서버 응답 오류: ${response.status}`);
            const data = await response.json();
            if (data.error) throw new Error(data.error);
            if (!Array.isArray(data) || data.length === 0) throw new Error('차트 데이터가 없습니다.');
            
            updateHeaderInfo(data[data.length - 1]);
            renderCharts(data, chartType);
            updateControlsUI(chartType);

        } catch (error) {
            showError(error.message);
        } finally {
            loadingEl.style.display = 'none';
        }
    }

    function renderCharts(data, chartType) {
        if (priceChart) priceChart.destroy();
        if (volumeChart) volumeChart.destroy();

        // 날짜 오름차순 정렬
        const sortedData = data.slice().sort((a, b) => {
            // 분봉 데이터는 시간까지 고려
            if (chartType === 'minute') {
                return a.date.localeCompare(b.date);
            }
            // 일/주봉은 날짜만 비교
            return a.date.substring(0, 8).localeCompare(b.date.substring(0, 8));
        });

        // 날짜 파싱 함수
        const parseDate = (dateStr) => {
            const year = parseInt(dateStr.substring(0, 4));
            const month = parseInt(dateStr.substring(4, 6)) - 1;
            const day = parseInt(dateStr.substring(6, 8));
            const hour = dateStr.length >= 10 ? parseInt(dateStr.substring(8, 10)) : 0;
            const min = dateStr.length >= 12 ? parseInt(dateStr.substring(10, 12)) : 0;
            return new Date(year, month, day, hour, min).getTime();
        };

        // 캔들 데이터 생성
        const priceData = sortedData.map(d => ({ x: parseDate(d.date), o: d.open, h: d.high, l: d.low, c: d.close }));

        // --- Price Chart ---
        const priceDatasets = [{
            label: '가격',
            data: priceData,
            upColor: var_('--red-color'),
            downColor: var_('--blue-color'),
            borderColor: function(ctx) {
                // 캔들 테두리도 본체와 동일하게
                const o = ctx.raw.o, c = ctx.raw.c;
                return c > o ? var_('--red-color') : var_('--blue-color');
            },
            borderWidth: 1,
            color: function(ctx) {
                // 캔들 본체 색상 지정 (Chart.js 3.x에서는 upColor/downColor로 충분하지만, 혹시 적용 안될 경우 대비)
                const o = ctx.raw.o, c = ctx.raw.c;
                return c > o ? var_('--red-color') : var_('--blue-color');
            }
        }];

        if (chartType !== 'minute') {
            MA_CONFIG.forEach(ma => {
                priceDatasets.push({
                    label: `MA ${ma.period}`,
                    data: sortedData.map(d => ({ x: parseDate(d.date), y: d[`ma${ma.period}`] })),
                    type: 'line',
                    borderColor: ma.color,
                    borderWidth: ma.width,
                    pointRadius: 0,
                    hidden: !ma.checked
                });
            });
        }

        priceChart = new Chart(priceCtx, {
            type: 'candlestick',
            data: { datasets: priceDatasets },
            options: {
                responsive: true, maintainAspectRatio: false,
                scales: {
                    x: { type: 'time', time: { unit: chartType === 'minute' ? 'hour' : 'day' }, grid: { color: var_('--border-color') }, ticks: { display: false } },
                    y: { position: 'right', grid: { color: var_('--border-color') }, ticks: { color: var_('--text-color') } }
                },
                plugins: {
                    legend: { display: false },
                    crosshair: {
                        line: { color: '#888', width: 0.5 },
                        sync: { enabled: true, group: 1, suppressTooltips: false },
                        zoom: { enabled: false },
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const d = context.dataset;
                                const isNumeric = (val) => typeof val === 'number';
                                if (d.type === 'line') {
                                    const val = context.raw.y;
                                    return `${d.label}: ${isNumeric(val) ? val.toFixed(2) : 'N/A'}`;
                                }
                                const raw = context.raw;
                                const o = isNumeric(raw.o) ? raw.o.toLocaleString() : 'N/A';
                                const h = isNumeric(raw.h) ? raw.h.toLocaleString() : 'N/A';
                                const l = isNumeric(raw.l) ? raw.l.toLocaleString() : 'N/A';
                                const c = isNumeric(raw.c) ? raw.c.toLocaleString() : 'N/A';
                                return [`시가: ${o}`,`고가: ${h}`,`저가: ${l}`,`종가: ${c}`];
                            }
                        }
                    },
                    financial: {
                        upColor: var_('--red-color'),
                        downColor: var_('--blue-color'),
                        borderColor: '#888',
                        borderWidth: 1
                    }
                }
            }
        });

        // --- Volume Chart ---
        // 거래량 색상을 캔들 색상과 동일하게 지정
        const volumeData = sortedData.map(d => {
            const isUp = d.close > d.open;
            return {
                x: parseDate(d.date),
                y: d.volume,
                backgroundColor: isUp ? var_('--red-color') : var_('--blue-color')
            };
        });

        volumeChart = new Chart(volumeCtx, {
            type: 'bar',
            data: { datasets: [{ label: '거래량', data: volumeData, backgroundColor: volumeData.map(d => d.backgroundColor) }] },
            options: {
                responsive: true, maintainAspectRatio: false,
                scales: {
                    x: { type: 'time', time: { unit: chartType === 'minute' ? 'hour' : 'day' }, grid: { color: var_('--border-color') }, ticks: { color: var_('--text-color'), maxRotation: 0, minRotation: 0, autoSkip: true, maxTicksLimit: 10 } },
                    y: { position: 'right', grid: { color: var_('--border-color') }, ticks: { color: var_('--text-color'), callback: v => v >= 1e6 ? `${v/1e6}M` : (v >= 1e3 ? `${v/1e3}K` : v) } }
                },
                plugins: {
                    legend: { display: false },
                    crosshair: {
                        line: { color: '#888', width: 0.5 },
                        sync: { enabled: true, group: 1, suppressTooltips: false },
                    },
                    tooltip: { callbacks: { 
                        label: (context) => {
                            const val = context.raw.y;
                            const isNumeric = (v) => typeof v === 'number';
                            return `거래량: ${isNumeric(val) ? val.toLocaleString() : 'N/A'}`;
                        } 
                    } }
                }
            }
        });
    }

    function var_(variable) {
        return getComputedStyle(document.documentElement).getPropertyValue(variable).trim();
    }
    
    function clearState() {
        if (priceChart) priceChart.destroy();
        if (volumeChart) volumeChart.destroy();
        if (autoRefreshInterval) clearInterval(autoRefreshInterval);
        errorEl.style.display = 'none';
        chartHeaderEl.style.display = 'none';
        chartOptionsEl.style.display = 'none';
        maTogglesEl.style.display = 'none';
        document.getElementById('autoRefreshToggle').checked = false;
    }

    function showError(message) {
        clearState();
        errorEl.textContent = `오류: ${message}`;
        errorEl.style.display = 'block';
    }

    function updateHeaderInfo(latestData) {
        if (!latestData) return;

        const price = latestData.close;
        const change = latestData.change;
        const volume = latestData.volume;
        const prevClose = latestData.prev_close || (price - change);
        
        const isNumeric = (val) => typeof val === 'number';

        const changeRate = isNumeric(change) && prevClose ? (change / prevClose * 100).toFixed(2) : '0.00';

        document.getElementById('stockName').textContent = currentStockName;
        document.getElementById('stockCode').textContent = currentStockCode;
        const priceEl = document.getElementById('stockPrice');
        const changeEl = document.getElementById('stockChange');
        
        priceEl.textContent = isNumeric(price) ? price.toLocaleString() : 'N/A';
        priceEl.className = `price ${change > 0 ? 'up' : (change < 0 ? 'down' : '')}`;
        
        let changeSymbol = change > 0 ? '▲' : (change < 0 ? '▼' : '');
        changeEl.textContent = `${changeSymbol} ${isNumeric(change) ? change.toLocaleString() : 'N/A'} (${changeRate}%)`;
        changeEl.className = `change ${change > 0 ? 'up' : (change < 0 ? 'down' : '')}`;

        document.getElementById('stockVolume').textContent = `거래량: ${isNumeric(volume) ? volume.toLocaleString() : 'N/A'}`;
        chartHeaderEl.style.display = 'flex';
    }

    function updateControlsUI(chartType) {
        chartOptionsEl.style.display = 'flex';
        
        document.querySelectorAll('.chart-type-controls button').forEach(btn => btn.classList.remove('active'));
        document.getElementById(`btn-${chartType}`).classList.add('active');

        const isMinuteChart = chartType === 'minute';
        maTogglesEl.innerHTML = '';
        if (!isMinuteChart) {
            MA_CONFIG.forEach(ma => {
                const label = document.createElement('label');
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.checked = ma.checked;
                checkbox.onchange = () => toggleMA(ma.period);
                label.appendChild(checkbox);
                label.append(` ${ma.period}MA`);
                label.style.color = ma.color;
                maTogglesEl.appendChild(label);
            });
        }
        maTogglesEl.style.display = isMinuteChart ? 'none' : 'flex';
    }

    function toggleMA(period) {
        const maDataset = priceChart.data.datasets.find(d => d.label === `MA ${period}`);
        if (maDataset) {
            maDataset.hidden = !maDataset.hidden;
            priceChart.update();
        }
    }

    function toggleAutoRefresh(checked) {
        if (checked) {
            autoRefreshInterval = setInterval(() => loadChartData(currentChartType), 60000);
        } else {
            clearInterval(autoRefreshInterval);
            autoRefreshInterval = null;
        }
    }

    function toggleDarkMode(checked) {
        document.documentElement.classList.toggle('dark-mode', checked);
        // 차트가 이미 그려진 경우 다시 그려서 색상 반영
        if(currentStockCode) {
            loadChartData(currentChartType);
        }
    }
</script>

</body>
</html>