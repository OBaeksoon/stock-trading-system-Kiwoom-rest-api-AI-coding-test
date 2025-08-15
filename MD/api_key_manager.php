/ㅡㅇ<?php
session_start();

// Database connection settings from config.ini
$host = 'localhost';
$dbname = 'stock';
$username = 'stock';
$password = '01P16NYJ3jwcCl9';

try {
    // Create PDO connection
    $pdo = new PDO("mysql:host=$host;dbname=$dbname;charset=utf8", $username, $password);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

    // Get current API keys
    $stmt = $pdo->prepare("SELECT setting_key, setting_value FROM settings WHERE setting_key IN ('APP_KEY', 'APP_SECRET')");
    $stmt->execute();
    $dbKeys = $stmt->fetchAll(PDO::FETCH_KEY_PAIR);

    $message = '';

    if ($_SERVER['REQUEST_METHOD'] === 'POST') {
        // CSRF token verification
        if (!isset($_POST['csrf_token']) || $_POST['csrf_token'] !== $_SESSION['csrf_token']) {
            die("CSRF attack detected.");
        }

        // Get and sanitize input values
        $newApiKey = htmlspecialchars(trim($_POST['api_key']), ENT_QUOTES, 'UTF-8');
        $newSecretKey = htmlspecialchars(trim($_POST['secret_key']), ENT_QUOTES, 'UTF-8');

        if (!empty($newApiKey) && !empty($newSecretKey)) {
            // Update APP_KEY
            $updateStmt = $pdo->prepare("INSERT INTO settings (setting_key, setting_value) 
                                          VALUES ('APP_KEY', ?) 
                                          ON DUPLICATE KEY UPDATE setting_value = ?");
            $updateStmt->execute([$newApiKey, $newApiKey]);

            // Update APP_SECRET
            $updateStmt = $pdo->prepare("INSERT INTO settings (setting_key, setting_value) 
                                          VALUES ('APP_SECRET', ?) 
                                          ON DUPLICATE KEY UPDATE setting_value = ?");
            $updateStmt->execute([$newSecretKey, $newSecretKey]);

            $message = "API keys successfully updated.";

            // Refresh keys after update
            $stmt->execute();
            $dbKeys = $stmt->fetchAll(PDO::FETCH_KEY_PAIR);
        } else {
            $message = "Please fill in all fields.";
        }
    }
} catch (PDOException $e) {
    die("Database connection failed: " . $e->getMessage());
}

// Generate CSRF token
if (empty($_SESSION['csrf_token'])) {
    $_SESSION['csrf_token'] = bin2hex(random_bytes(50));
}
?>
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>API 키 관리</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { padding: 40px; background-color: #f8f9fa; }
        .container { max-width: 600px; }
        .key-input { font-family: monospace; }
    </style>
</head>
<body>
<div class="container">
    <h2 class="mb-4">🔑 API 키 관리</h2>

    <?php if (!empty($message)): ?>
        <div class="alert <?= strpos($message, '성공') !== false ? 'alert-success' : 'alert-danger' ?>">
            <?= $message ?>
        </div>
    <?php endif; ?>

    <form method="post">
        <input type="hidden" name="csrf_token" value="<?= $_SESSION['csrf_token'] ?>">

        <div class="mb-3">
            <label for="api_key" class="form-label">API Key</label>
            <input type="text" name="api_key" id="api_key" class="form-control key-input"
                   value="<?= htmlspecialchars($dbKeys['APP_KEY'] ?? '') ?>" required>
        </div>

        <div class="mb-3">
            <label for="secret_key" class="form-label">Secret Key</label>
            <input type="text" name="secret_key" id="secret_key" class="form-control key-input"
                   value="<?= htmlspecialchars($dbKeys['APP_SECRET'] ?? '') ?>" required>
        </div>

        <button type="submit" class="btn btn-primary">업데이트</button>
    </form>
</div>
</body>
</html>