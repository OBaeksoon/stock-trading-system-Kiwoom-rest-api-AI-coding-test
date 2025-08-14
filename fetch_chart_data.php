<?php
header('Content-Type: application/json');

// 에러 리포팅 활성화 (개발용)
ini_set('display_errors', 1);
error_reporting(E_ALL);

// 로그 파일 경로 설정
define('LOG_FILE', __DIR__ . '/../logs/fetch_chart_data.log');

function write_log($message) {
    error_log(date('[Y-m-d H:i:s]') . ' ' . $message . PHP_EOL, 3, LOG_FILE);
}

write_log("fetch_chart_data.php 스크립트 시작");

// 입력 파라미터 검증
if (!isset($_GET['stock_code']) || empty($_GET['stock_code'])) {
    write_log("오류: 종목 코드가 입력되지 않았습니다.");
    echo json_encode(['error' => '종목 코드를 입력해주세요.']);
    exit;
}

if (!isset($_GET['chart_type']) || !in_array($_GET['chart_type'], ['daily', 'weekly', 'minute'])) {
    write_log("오류: 유효하지 않은 차트 종류가 입력되었습니다: " . ($_GET['chart_type'] ?? 'NULL'));
    echo json_encode(['error' => '차트 종류(daily, weekly, minute)를 정확히 입력해주세요.']);
    exit;
}

$stock_code = $_GET['stock_code'];
$chart_type = $_GET['chart_type'];
write_log("요청 파라미터: stock_code=" . $stock_code . ", chart_type=" . $chart_type);

// Python 스크립트 실행 명령어
$venv_python = escapeshellcmd(__DIR__ . '/.venv/bin/python');
$script_path = escapeshellcmd(__DIR__ . '/python_modules/get_stock_chart_data.py');
$command = $venv_python . " " . $script_path . " " . escapeshellarg($stock_code) . " " . escapeshellarg($chart_type);
write_log("Python 스크립트 실행 명령: " . $command);

// proc_open을 사용하여 stdout과 stderr를 분리
$descriptorspec = [
   0 => ["pipe", "r"],  // stdin
   1 => ["pipe", "w"],  // stdout
   2 => ["pipe", "w"]   // stderr
];

$process = proc_open($command, $descriptorspec, $pipes);

$json_output = null;
$error_output = null;
$return_var = null;

if (is_resource($process)) {
    // stdout (JSON 결과)과 stderr (오류/로그)의 내용을 읽음
    $json_output = stream_get_contents($pipes[1]);
    fclose($pipes[1]);

    $error_output = stream_get_contents($pipes[2]);
    fclose($pipes[2]);

    // stdin 파이프를 닫음
    fclose($pipes[0]);

    // 프로세스가 종료될 때까지 기다리고 종료 코드를 받음
    $return_var = proc_close($process);

    write_log("Python 스크립트 종료 코드: " . $return_var);
    write_log("Python 스크립트 STDOUT: " . $json_output);
    write_log("Python 스크립트 STDERR: " . $error_output);

    // 스크립트 실행 실패 시
    if ($return_var !== 0) {
        write_log("오류: 차트 데이터 조회 스크립트 실행 실패. 상세: " . $error_output);
        echo json_encode([
            'error' => '차트 데이터 조회 스크립트 실행에 실패했습니다.',
            'details' => $error_output // stderr에 출력된 오류 메시지를 포함
        ]);
        exit;
    }

    // 스크립트 실행은 성공했지만 결과가 없는 경우
    if (empty($json_output)) {
        write_log("오류: 스크립트에서 결과 데이터를 반환하지 않았습니다. 상세: " . $error_output);
        echo json_encode([
            'error' => '스크립트에서 결과 데이터를 반환하지 않았습니다.',
            'details' => $error_output // stderr에 정보가 있을 수 있음
        ]);
        exit;
    }

    // JSON 파싱 시도
    $data = json_decode($json_output);

    if (json_last_error() !== JSON_ERROR_NONE) {
        // JSON 파싱 실패 시
        write_log("오류: 스크립트 결과가 유효한 JSON 형식이 아닙니다. JSON 오류: " . json_last_error_msg() . ", 원본 출력: " . $json_output);
        echo json_encode([
            'error' => '스크립트 결과가 유효한 JSON 형식이 아닙니다.',
            'details' => $json_output // 원본 출력을 포함하여 디버깅 지원
        ]);
    } else {
        // 성공적으로 파싱된 경우, 데이터를 클라이언트에 전송
        write_log("차트 데이터 성공적으로 파싱 및 전송.");
        echo json_encode($data);
    }

} else {
    // 프로세스 생성 실패 시
    write_log("오류: 데이터 조회 프로세스를 시작할 수 없습니다.");
    echo json_encode(['error' => '데이터 조회 프로세스를 시작할 수 없습니다.']);
}

write_log("fetch_chart_data.php 스크립트 종료");
?>