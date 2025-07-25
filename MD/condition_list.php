<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>조건검색식 목록</title>
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
        <h1>모의투자 조건검색식 목록</h1>
        <?php
        $python_script = '/home/stock/public_html/python_modules/get_condition_list.py';
        $command = 'python3 ' . escapeshellarg($python_script) . ' 2>&1';

        // Execute the Python script
        $output = shell_exec($command);

        // Decode the JSON output
        $data = json_decode($output, true);

        if (json_last_error() === JSON_ERROR_NONE) {
            if (is_array($data) && !empty($data)) {
                echo "<p>성공적으로 조건검색식 목록을 불러왔습니다:</p>";
                echo "<table>";
                echo "<tr><th>인덱스</th><th>조건명</th></tr>";
                foreach ($data as $condition) {
                    // Check if $condition is an array with at least two elements
                    if (is_array($condition) && count($condition) >= 2) {
                        echo "<tr>";
                        echo "<td>" . htmlspecialchars($condition[0]) . "</td>"; // Index is the first element
                        echo "<td>" . htmlspecialchars($condition[1]) . "</td>"; // Name is the second element
                        echo "</tr>";
                    }
                }
                echo "</table>";
            } else if (isset($data["error"])) {
                echo "<p class=\"error\">오류 발생: " . htmlspecialchars($data["error"]) . "</p>";
                echo "<pre class=\"error\">" . htmlspecialchars(json_encode($data["response"], JSON_PRETTY_PRINT)) . "</pre>";
            } else {
                echo "<p>조건검색식 목록이 비어 있습니다.</p>";
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
