<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>상승률 30위 종목</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f4f4f4; color: #333; }
        .container { background-color: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #0056b3; }
        pre { background-color: #eee; padding: 15px; border-radius: 5px; overflow-x: auto; }
        .error { color: red; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <div class="container">
        <h1>모의투자 상승률 30위 종목</h1>
        <?php
        $python_script = '/home/stock/public_html/python_modules/get_top_30_rising_stocks.py';
        $command = 'python3 ' . escapeshellarg($python_script) . ' 2>&1';

        // Execute the Python script
        $output = shell_exec($command);

        // Decode the JSON output
        $data = json_decode($output, true);

        if (json_last_error() === JSON_ERROR_NONE) {
            if (is_array($data) && !empty($data) && $data[0] !== None) {
                // Check if the first element is an error or actual data
                if (isset($data[0]["error"])) {
                    echo "<p class=\"error\">오류 발생: " . htmlspecialchars($data[0]["error"]) . "</p>";
                    if (isset($data[0]["return_msg"])) {
                        echo "<p class=\"error\">" . htmlspecialchars($data[0]["return_msg"]) . "</p>";
                    }
                    echo "<pre class=\"error\">" . htmlspecialchars($output) . "</pre>";
                } else {
                    echo "<p>성공적으로 상승률 30위 종목을 불러왔습니다:</p>";
                    echo "<table>";
                    echo "<tr><th>종목코드</th><th>종목명</th><th>현재가</th><th>등락률</th><th>거래량</th></tr>";
                    foreach ($data as $stock) {
                        if (is_array($stock) && isset($stock['stk_cd']) && isset($stock['stk_nm'])) {
                            echo "<tr>";
                            echo "<td>" . htmlspecialchars($stock['stk_cd']) . "</td>";
                            echo "<td>" . htmlspecialchars($stock['stk_nm']) . "</td>";
                            echo "<td>" . htmlspecialchars($stock['cur_prc']) . "</td>";
                            echo "<td>" . htmlspecialchars($stock['flu_rt']) . "</td>";
                            echo "<td>" . htmlspecialchars($stock['trde_qty']) . "</td>";
                            echo "</tr>";
                        }
                    }
                    echo "</table>";
                }
            } else if (is_array($data) && (empty($data) || $data[0] === None)) {
                echo "<p>상승률 30위 종목 목록이 비어 있거나 데이터를 가져오지 못했습니다. (API 제한 또는 데이터 없음)</p>";
                echo "<pre>" . htmlspecialchars($output) . "</pre>";
            } else if (isset($data["error"])) {
                echo "<p class=\"error\">오류 발생: " . htmlspecialchars($data["error"]) . "</p>";
                echo "<pre class=\"error\">" . htmlspecialchars($output) . "</pre>";
            } else {
                echo "<p>상승률 30위 종목 목록이 비어 있습니다.</p>";
                echo "<pre>" . htmlspecialchars($output) . "</pre>";
            }
        } else {
            echo "<p class=\"error\">Python 스크립트 실행 오류 또는 JSON 디코딩 실패:</p>";
            echo "<pre class=\"error\">" . htmlspecialchars($output) . "</pre>";
            echo "<p class=\"error\">JSON Error: " . json_last_error_msg() . "</p>";
        }
        ?>
    </div>
</body>
</html>