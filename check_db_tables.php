<?php
// 데이터베이스 테이블 구조 확인 스크립트

$config_file = __DIR__ . '/config.ini';
$config = parse_ini_file($config_file, true);

$db_host = $config['DB']['HOST'];
$db_user = $config['DB']['USER'];
$db_password = $config['DB']['PASSWORD'];
$db_name = $config['DB']['DATABASE'];
$db_port = $config['DB']['PORT'];

$conn = new mysqli($db_host, $db_user, $db_password, $db_name, $db_port);

if ($conn->connect_error) {
    die("데이터베이스 연결 실패: " . $conn->connect_error);
}

$conn->set_charset("utf8mb4");

echo "<h2>데이터베이스 테이블 구조 확인</h2>";

// 1. stock_details 테이블 구조 확인
echo "<h3>1. stock_details 테이블 구조:</h3>";
$result = $conn->query("DESCRIBE stock_details");
if ($result) {
    echo "<table border='1'><tr><th>Field</th><th>Type</th><th>Null</th><th>Key</th><th>Default</th><th>Extra</th></tr>";
    while($row = $result->fetch_assoc()) {
        echo "<tr>";
        echo "<td>" . $row['Field'] . "</td>";
        echo "<td>" . $row['Type'] . "</td>";
        echo "<td>" . $row['Null'] . "</td>";
        echo "<td>" . $row['Key'] . "</td>";
        echo "<td>" . $row['Default'] . "</td>";
        echo "<td>" . $row['Extra'] . "</td>";
        echo "</tr>";
    }
    echo "</table>";
} else {
    echo "stock_details 테이블이 존재하지 않습니다.<br>";
}

// 2. stock_news 테이블 구조 확인
echo "<h3>2. stock_news 테이블 구조:</h3>";
$result = $conn->query("DESCRIBE stock_news");
if ($result) {
    echo "<table border='1'><tr><th>Field</th><th>Type</th><th>Null</th><th>Key</th><th>Default</th><th>Extra</th></tr>";
    while($row = $result->fetch_assoc()) {
        echo "<tr>";
        echo "<td>" . $row['Field'] . "</td>";
        echo "<td>" . $row['Type'] . "</td>";
        echo "<td>" . $row['Null'] . "</td>";
        echo "<td>" . $row['Key'] . "</td>";
        echo "<td>" . $row['Default'] . "</td>";
        echo "<td>" . $row['Extra'] . "</td>";
        echo "</tr>";
    }
    echo "</table>";
} else {
    echo "stock_news 테이블이 존재하지 않습니다.<br>";
}

// 3. 데이터 샘플 확인
echo "<h3>3. stock_details 데이터 샘플 (5개):</h3>";
$result = $conn->query("SELECT * FROM stock_details LIMIT 5");
if ($result && $result->num_rows > 0) {
    echo "<table border='1'>";
    $first = true;
    while($row = $result->fetch_assoc()) {
        if ($first) {
            echo "<tr>";
            foreach(array_keys($row) as $key) {
                echo "<th>" . $key . "</th>";
            }
            echo "</tr>";
            $first = false;
        }
        echo "<tr>";
        foreach($row as $value) {
            echo "<td>" . htmlspecialchars($value) . "</td>";
        }
        echo "</tr>";
    }
    echo "</table>";
} else {
    echo "stock_details 테이블에 데이터가 없습니다.<br>";
}

echo "<h3>4. stock_news 데이터 샘플 (5개):</h3>";
$result = $conn->query("SELECT * FROM stock_news LIMIT 5");
if ($result && $result->num_rows > 0) {
    echo "<table border='1'>";
    $first = true;
    while($row = $result->fetch_assoc()) {
        if ($first) {
            echo "<tr>";
            foreach(array_keys($row) as $key) {
                echo "<th>" . $key . "</th>";
            }
            echo "</tr>";
            $first = false;
        }
        echo "<tr>";
        foreach($row as $value) {
            echo "<td>" . htmlspecialchars($value) . "</td>";
        }
        echo "</tr>";
    }
    echo "</table>";
} else {
    echo "stock_news 테이블에 데이터가 없습니다.<br>";
}

$conn->close();
?>