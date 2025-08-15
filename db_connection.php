<?php
// 데이터베이스 연결을 설정하고 PDO 객체를 반환하는 함수
function get_db_connection() {
    static $pdo = null;

    if ($pdo === null) {
        // config.ini 파일에서 데이터베이스 설정을 읽어옵니다.
        $config_file = __DIR__ . '/config.ini';
        
        if (!file_exists($config_file)) {
            // 설정 파일이 없으면 스크립트 실행을 중단합니다.
            error_log("Configuration file not found: " . $config_file);
            die("서버 설정 오류가 발생했습니다.");
        }
        
        $config = parse_ini_file($config_file, true);
        
        if (!$config || !isset($config['DB'])) {
            // [DB] 섹션이 없으면 스크립트 실행을 중단합니다.
            error_log("DB section is missing in the configuration file.");
            die("데이터베이스 설정이 올바르지 않습니다.");
        }

        // DSN (Data Source Name) 설정
        $dsn = sprintf(
            "mysql:host=%s;port=%d;dbname=%s;charset=utf8mb4",
            $config['DB']['HOST'],
            $config['DB']['PORT'],
            $config['DB']['DATABASE']
        );

        // PDO 옵션 설정
        $options = [
            PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_EMULATE_PREPARES   => false,
        ];

        try {
            // PDO 인스턴스 생성
            $pdo = new PDO($dsn, $config['DB']['USER'], $config['DB']['PASSWORD'], $options);
        } catch (\PDOException $e) {
            // 데이터베이스 연결 실패 시 오류를 로그에 기록하고 스크립트 실행을 중단합니다.
            error_log("Database connection failed: " . $e->getMessage());
            die("데이터베이스에 연결할 수 없습니다.");
        }
    }

    return $pdo;
}

// 이전 버전과의 호환성을 위해 전역 변수 생성 (점진적으로 제거 예정)
try {
    $conn = get_db_connection();
} catch (Exception $e) {
    // get_db_connection()에서 die()로 처리되므로 이 부분은 거의 실행되지 않음
    die($e->getMessage());
}
?>