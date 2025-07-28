<?php
header('Content-Type: application/json');

// 입력 파라미터 검증
if (!isset($_GET['stock_code']) || empty($_GET['stock_code'])) {
    echo json_encode(['error' => '종목 코드를 입력해주세요.']);
    exit;
}

if (!isset($_GET['chart_type']) || !in_array($_GET['chart_type'], ['daily', 'weekly', 'minute'])) {
    echo json_encode(['error' => '차트 종류(daily, weekly, minute)를 정확히 입력해주세요.']);
    exit;
}

$stock_code = escapeshellarg($_GET['stock_code']);
$chart_type = escapeshellarg($_GET['chart_type']);

// Python 스크립트 실행
// 실제 운영 환경에서는 Python 경로를 확인해야 할 수 있습니다. (예: /usr/bin/python3)
$command = "python3 " . escapeshellcmd(__DIR__ . '/python_modules/get_stock_chart_data.py') . " " . $stock_code . " " . $chart_type;

// 스크립트 실행 및 결과 반환
$output = shell_exec($command);

// Python 스크립트에서 반환된 JSON을 그대로 출력
// 오류 발생 시 Python 스크립트가 생성한 JSON 오류 메시지가 출력됨
if ($output === null) {
    echo json_encode(['error' => '스크립트 실행에 실패했거나 결과가 없습니다.']);
} else {
    // Python 스크립트의 출력이 이미 JSON이므로 그대로 echo
    echo $output;
}
?>
