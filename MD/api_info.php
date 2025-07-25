<?php
// Function to read API info from SQLite DB
function getApiInfoFromDb() {
    $db_file = __DIR__ . '/stock_data.db';
    try {
        $pdo = new PDO('sqlite:' . $db_file);
        $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

        $stmt = $pdo->query("SELECT access_token, account_number, account_name, balance FROM api_info LIMIT 1");
        $info = $stmt->fetch(PDO::FETCH_ASSOC);
        return $info;
    } catch (PDOException $e) {
        error_log("Database error: " . $e->getMessage());
        return null;
    }
}

// Execute the Python script to ensure data is generated/updated
// This path assumes python_modules/kiwoom_api.py is executable and in the correct location
$python_script_path = escapeshellarg(__DIR__ . '/python_modules/kiwoom_api.py');
$command = "python3 " . $python_script_path; // Use python3 for execution
exec($command . ' 2>&1', $output_array, $return_var);
$output = implode("\n", $output_array);

// Get API info from DB
$api_info = getApiInfoFromDb();

$token_display = "정보 없음";
$account_number_display = "정보 없음";
$account_name_display = "정보 없음";
$balance_display = "정보 없음";

if ($api_info) {
    $token = $api_info['access_token'];
    $token_display = substr($token, 0, 5) . str_repeat('*', strlen($token) - 5);
    $account_number_display = htmlspecialchars($api_info['account_number']);
    $account_name_display = htmlspecialchars($api_info['account_name']);
    $balance_display = number_format($api_info['balance']) . '원';
}

$page_title = 'API 정보';
?>
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?php echo htmlspecialchars($page_title); ?></title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.7;
            color: #34495e;
            background-color: #f8f9fa;
            margin: 0;
            padding: 0;
        }
        .navbar {
            background-color: #2c3e50;
            padding: 15px 20px;
            color: white;
            text-align: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .navbar a {
            color: white;
            text-decoration: none;
            margin: 0 15px;
            font-weight: 500;
            transition: color 0.3s ease;
        }
        .navbar a:hover {
            color: #3498db;
        }
        .container {
            max-width: 900px;
            margin: 20px auto;
            background-color: #ffffff;
            padding: 30px 50px;
            border-radius: 10px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            border: 1px solid #e9ecef;
        }
        h1 {
            font-size: 2.2em;
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 15px;
            border-bottom: 3px solid #3498db;
            color: #2c3e50;
        }
        .info-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 30px;
        }
        .info-table th, .info-table td {
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }
        .info-table th {
            background-color: #f2f2f2;
            color: #555;
            font-weight: 600;
            width: 30%;
        }
        .info-table td {
            background-color: #fff;
            font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, Courier, monospace;
        }
        .error-message {
            color: #e74c3c;
            text-align: center;
            margin-top: 20px;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="navbar">
        <a href="index.php">프로젝트 개요</a>
        <a href="api_info.php">API 정보</a>
        <a href="all_stocks.php">코스피 및 코스닥 종목</a>
        <a href="updates.php">업데이트중</a>
    </div>
    <div class="container">
        <h1><?php echo htmlspecialchars($page_title); ?></h1>

        <?php if (!$api_info): ?>
            <p class="error-message">API 정보를 불러오는 데 실패했습니다. Python 스크립트 실행 결과를 확인하세요.</p>
            <pre><?php echo htmlspecialchars($output); ?></pre>
        <?php else: ?>
            <table class="info-table">
                <tr>
                    <th>접근 토큰</th>
                    <td><?php echo $token_display; ?></td>
                </tr>
                <tr>
                    <th>계좌 번호</th>
                    <td><?php echo $account_number_display; ?></td>
                </tr>
                <tr>
                    <th>계좌명</th>
                    <td><?php echo $account_name_display; ?></td>
                </tr>
                <tr>
                    <th>잔고</th>
                    <td><?php echo $balance_display; ?></td>
                </tr>
            </table>
        <?php endif; ?>

        <h2>보유 종목 데이터 설명</h2>
            <p>The following data represents the user's current stock holdings. Here's a breakdown of each column:</p>
            <ul>
                <li><b>종목코드 (Jongmok Code):</b> 주식 종목을 식별하는 코드입니다. (Stock Code: Code to identify the stock.)</li>
                <li><b>종목명 (Jongmokmyeong):</b> 주식의 이름입니다. (Stock Name: Name of the stock.)</li>
                <li><b>평가손익 (Pyeongga Sonik):</b> 현재 주식의 평가 손익입니다. (Valuation Profit/Loss: The current profit or loss on the stock.)</li>
                <li><b>수익률 (Suiknyul):</b> 수익률입니다. (Return Rate: Profit rate.)</li>
                <li><b>매입가 (Maeipga):</b> 주식의 매입 가격입니다. (Purchase Price: The price at which the stock was bought.)</li>
                <li><b>보유수량 (Boyu Suryang):</b> 보유한 주식 수량입니다. (Quantity Held: The number of shares held.)</li>
                <li><b>가능수량 (Ganeung Suryang):</b> 판매 가능한 주식 수량입니다. (Available Quantity: The number of shares available for sale.)</li>
                <li><b>현재가 (Hyeonjaega):</b> 현재 주식 가격입니다. (Current Price: The current price of the stock.)</li>
                <li><b>전일 (Jeonil):</b> 전일 가격입니다. (Previous Day: Previous day price.)</li>
                <li><b>금일 (Geumil):</b> 금일 가격입니다. (Today: Today price.)</li>
                <li><b>매입금액 (Maeip Geumaek):</b> 총 매입 금액입니다. (Total Purchase Amount: The total purchase amount.)</li>
                <li><b>평가금액 (Pyeongga Geumaek):</b> 총 평가 금액입니다. (Total Valuation Amount: The total valuation amount.)</li>
                <li><b>수수료 (Susuryo):</b> 지불한 수수료입니다. (Commission: The commission paid.)</li>
                <li><b>세금 (Segeum):</b> 지불한 세금입니다. (Tax: The tax paid.)</li>
                <li><b>보유비중 (Boyu Bijeung):</b> 포트폴리오에서 주식의 비중입니다. (Holding Ratio: The proportion of the stock in the portfolio.)</li>
                <li><b>신용구분 (Sinyong Gubeun):</b> 신용 거래 여부입니다. (Credit Classification: Whether it is a credit transaction.)</li>
                <li><b>대출일 (Daechulil):</b> 대출일입니다. (Loan Date: Loan date.)</li>
                <li><b>만기일 (Mangigil):</b> 만기일입니다. (Expiration Date: Expiration date.)</li>
                <li><b>신용금액 (Sinyong Geumaek):</b> 신용 금액입니다. (Credit Amount: Credit amount.)</li>
                <li><b>신용이자 (Sinyong Ija):</b> 신용 이자입니다. (Credit Interest: Credit interest.)</li>
                <li><b>대출수량 (Daechul Suryang):</b> 대출 수량입니다. (Loan Quantity: Loan quantity.)</li>
                <li><b>손익분기매입가 (Sonik Bunki Maeipga):</b> 손익분기점 매입가입니다. (Break-Even Purchase Price: Break-even point purchase price.)</li>
            </ul>

            <h2>조건검색식 목록</h2>
            <?php include 'condition_list.php'; ?>

            <h2>실시간 상승률 상위 30위 종목 (모의투자)</h2>
            <p>
                아래 목록은 키움증권 모의투자 서버로부터 실시간으로 수신한 데이터입니다.
                시스템은 WebSocket을 이용하여 '상승률 30위(UPRATE30)' 데이터를 요청하고, 그 결과를 테이블 형태로 표시합니다.
                이 기능은 <code>python_modules/get_top_30_rising_stocks.py</code> 스크립트를 통해 구현되었습니다.
            </p>
            <?php include 'top_30_rising_stocks.php'; ?>
    </div>
</body>
</html>