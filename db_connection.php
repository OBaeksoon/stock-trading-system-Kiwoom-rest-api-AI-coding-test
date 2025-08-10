<?php
// config.ini 파일에서 데이터베이스 설정을 읽어옵니다.
$config = parse_ini_file('config.ini', true);

// 데이터베이스 연결을 설정합니다.
$conn = new mysqli(
    $config['DB']['HOST'],
    $config['DB']['USER'],
    $config['DB']['PASSWORD'],
    $config['DB']['DATABASE'],
    $config['DB']['PORT']
);

// 연결 오류가 발생하면 스크립트 실행을 중단하고 오류 메시지를 출력합니다.
if ($conn->connect_error) {
    die("데이터베이스 연결 실패: " . $conn->connect_error);
}

// 문자 인코딩을 utf8mb4로 설정합니다.
$conn->set_charset("utf8mb4");
?>
