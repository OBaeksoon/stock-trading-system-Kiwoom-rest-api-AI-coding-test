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
        require_once 'db_connection.php';
        $pdo = get_db_connection();
        
        // 테이블 목록 조회
        $tables_result = $pdo->query("SHOW TABLES");
        $tables = $tables_result->fetchAll(PDO::FETCH_COLUMN);
        
        $selected_table = $_GET['table'] ?? 'technical_analysis';

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
            $stmt = $pdo->query("SELECT COUNT(*) as count FROM `$selected_table`");
            $count = $stmt->fetchColumn();
            
            // 컬럼 정보 조회
            $stmt = $pdo->query("SHOW COLUMNS FROM `$selected_table`");
            $columns = $stmt->fetchAll();
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
            $stmt = $pdo->query("SELECT * FROM `$selected_table` ORDER BY 1 DESC LIMIT 5000");
            if ($stmt->rowCount() > 0):
            ?>
                <table>
                    <tr>
                        <?php foreach ($columns as $col): ?>
                            <th><?= htmlspecialchars($col['Field']) ?></th>
                        <?php endforeach; ?>
                    </tr>
                    <?php while ($row = $stmt->fetch()): ?>
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
        
        <?php // PDO는 스크립트 종료 시 자동으로 연결을 닫습니다. ?>
    </div>
</body>
</html>