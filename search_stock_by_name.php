<?php
header('Content-Type: application/json; charset=utf-8');

// 입력 파라미터 검증
if (!isset($_GET['stock_name']) || empty($_GET['stock_name'])) {
    echo json_encode(['error' => '종목명을 입력해주세요.']);
    exit;
}

$stock_name = escapeshellarg($_GET['stock_name']);

// Python 스크립트 실행
$command = "python3 " . escapeshellcmd(__DIR__ . '/python_modules/get_stock_code_by_name.py') . " " . $stock_name;

// 스크립트 실행 및 결과 반환
$output = shell_exec($command);

// Python 스크립트에서 반환된 JSON을 그대로 출력
if ($output === null) {
    echo json_encode(['error' => '스크립트 실행에 실패했거나 결과가 없습니다.']);
} else {
    echo $output;
}
?>
