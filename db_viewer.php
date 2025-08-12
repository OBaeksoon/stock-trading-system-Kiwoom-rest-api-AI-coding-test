<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>데이터베이스 뷰어</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f4f4f4; }
        .container { background-color: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #0056b3; text-align: center; }
        .table-selector { margin: 20px 0; }
        select { padding: 10px; margin: 10px; border: 1px solid #ddd; border-radius: 4px; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 8px; border: 1px solid #ddd; text-align: left; font-size: 12px; }
        th { background-color: #007bff; color: white; }
        tr:nth-child(even) { background-color: #f2f2f2; }
        .error { color: red; text-align: center; }
        .info { background-color: #e7f3ff; padding: 10px; border-radius: 4px; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>데이터베이스 뷰어</h1>
        
        <?php
        $config_file = __DIR__ . '/config.ini';
        
        if (!file_exists($config_file)) {
            die("<p class='error'>config.ini 파일을 찾을 수 없습니다.</p>");
        }
        
        $config = parse_ini_file($config_file, true);
        
        if (!$config || !isset($config['DB'])) {
            die("<p class='error'>config.ini 파일에 [DB] 섹션이 없습니다.</p>");
        }
        
        $conn = new mysqli(
            $config['DB']['HOST'],
            $config['DB']['USER'],
            $config['DB']['PASSWORD'],
            $config['DB']['DATABASE'],
            $config['DB']['PORT']
        );
        
        if ($conn->connect_error) {
            die("<p class='error'>데이터베이스 연결 실패: " . $conn->connect_error . "</p>");
        }
        
        // 테이블 목록 조회
        $tables_result = $conn->query("SHOW TABLES");
        $tables = [];
        while ($row = $tables_result->fetch_array()) {
            $tables[] = $row[0];
        }
        
        $selected_table = $_GET['table'] ?? $tables[0] ?? '';

        // 선택된 테이블이 실제 테이블 목록에 있는지 확인 (보안 강화)
        if (!in_array($selected_table, $tables)) {
            $selected_table = $tables[0] ?? '';
        }
        ?>
        
        <div class="table-selector">
            <form method="GET">
                <label for="table">테이블 선택:</label>
                <select name="table" id="table" onchange="this.form.submit()">
                    <?php foreach ($tables as $table): ?>
                        <option value="<?= htmlspecialchars($table) ?>" <?= $table === $selected_table ? 'selected' : '' ?>>
                            <?= htmlspecialchars($table) ?>
                        </option>
                    <?php endforeach; ?>
                </select>
            </form>
        </div>
        
        <?php if ($selected_table): ?>
            <?php
            // 테이블 정보 조회
            $count_result = $conn->query("SELECT COUNT(*) as count FROM `$selected_table`");
            $count = $count_result->fetch_assoc()['count'];
            
            // 컬럼 정보 조회
            $columns_result = $conn->query("SHOW COLUMNS FROM `$selected_table`");
            $columns = [];
            while ($col = $columns_result->fetch_assoc()) {
                $columns[] = $col;
            }
            ?>
            
            <div class="info">
                <strong>테이블:</strong> <?= htmlspecialchars($selected_table) ?> 
                <strong>총 레코드 수:</strong> <?= number_format($count) ?>개
            </div>
            
            <h3>컬럼 정보</h3>
            <table>
                <tr><th>컬럼명</th><th>타입</th><th>NULL</th><th>키</th><th>기본값</th></tr>
                <?php foreach ($columns as $col): ?>
                    <tr>
                        <td><?= htmlspecialchars($col['Field']) ?></td>
                        <td><?= htmlspecialchars($col['Type']) ?></td>
                        <td><?= htmlspecialchars($col['Null']) ?></td>
                        <td><?= htmlspecialchars($col['Key']) ?></td>
                        <td><?= htmlspecialchars($col['Default']) ?></td>
                    </tr>
                <?php endforeach; ?>
            </table>
            
            <h3>데이터 (최근 5000개)</h3>
            <?php
            $data_result = $conn->query("SELECT * FROM `$selected_table` ORDER BY 1 DESC LIMIT 5000");
            if ($data_result && $data_result->num_rows > 0):
            ?>
                <table>
                    <tr>
                        <?php foreach ($columns as $col): ?>
                            <th><?= htmlspecialchars($col['Field']) ?></th>
                        <?php endforeach; ?>
                    </tr>
                    <?php while ($row = $data_result->fetch_assoc()): ?>
                        <tr>
                            <?php foreach ($columns as $col): ?>
                                <td><?= htmlspecialchars($row[$col['Field']] ?? '') ?></td>
                            <?php endforeach; ?>
                        </tr>
                    <?php endwhile; ?>
                </table>
            <?php else: ?>
                <p>데이터가 없습니다.</p>
            <?php endif; ?>
        <?php endif; ?>
        
        <?php $conn->close(); ?>
    </div>
</body>
</html>