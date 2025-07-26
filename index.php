<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>주식 자동매매 시스템 대시보드</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f0f2f5;
            color: #333;
            margin: 0;
            padding: 20px;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }
        .container {
            max-width: 900px;
            width: 100%;
            margin: 0 auto;
        }
        h1 {
            text-align: center;
            color: #1a2c4e;
            margin-bottom: 40px;
            font-size: 2.5em;
            font-weight: 600;
        }
        .menu-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 25px;
        }
        .menu-card {
            background: linear-gradient(145deg, #ffffff, #e6e9ee);
            border-radius: 15px;
            box-shadow: 8px 8px 16px #d1d9e6, -8px -8px 16px #ffffff;
            padding: 25px;
            text-align: center;
            transition: all 0.3s ease-in-out;
            text-decoration: none;
            color: inherit;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            min-height: 150px;
        }
        .menu-card:hover {
            transform: translateY(-10px);
            box-shadow: 12px 12px 24px #d1d9e6, -12px -12px 24px #ffffff;
        }
        .menu-card h2 {
            margin-top: 0;
            margin-bottom: 10px;
            color: #3498db;
            font-size: 1.6em;
        }
        .menu-card p {
            font-size: 1em;
            color: #555;
            margin-bottom: 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>주식 자동매매 대시보드</h1>
        <div class="menu-grid">
            <a href="display_all_stocks.php" class="menu-card">
                <h2>전체 종목 조회</h2>
                <p>코스피/코스닥 모든 종목의 현재가를 확인합니다.</p>
            </a>
            <a href="MD/themed_news.php" class="menu-card">
                <h2>테마별 뉴스</h2>
                <p>AI, 2차전지 등 주요 테마별 뉴스 현황을 봅니다.</p>
            </a>
            <a href="display_stock_news.php" class="menu-card">
                <h2>종목별 뉴스 검색</h2>
                <p>특정 주식 종목에 대한 최신 뉴스를 검색합니다.</p>
            </a>
            <a href="display_stock_details.php" class="menu-card">
                <h2>종목 상세 정보</h2>
                <p>종목 코드를 입력하여 상세 정보를 조회합니다.</p>
            </a>
        </div>
    </div>
</body>
</html>