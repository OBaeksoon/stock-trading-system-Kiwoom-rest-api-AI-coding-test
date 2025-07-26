<?php
// --- 테마 이름 가져오기 ---
if (!isset($_GET['theme'])) {
    die("테마가 지정되지 않았습니다.");
}
$theme = urldecode($_GET['theme']);

// --- 데이터베이스 연결 설정 ---
$config = parse_ini_file('../config.ini');
$db_host = $config['HOST'];
$db_user = $config['USER'];
$db_pass = $config['PASSWORD'];
$db_name = $config['DATABASE'];
$db_port = $config['PORT'];

$conn = new mysqli($db_host, $db_user, $db_pass, $db_name, $db_port);

if ($conn->connect_error) {
    die("Connection failed: " . $conn->connect_error);
}

// --- 특정 테마의 뉴스 조회 (stock_details와 조인하여 종목명 가져오기) ---
$sql = "SELECT 
            n.title, 
            n.link, 
            n.description, 
            n.pub_date, 
            s.stock_name 
        FROM stock_news n
        JOIN stock_details s ON n.stock_code = s.stock_code
        WHERE n.theme = ? 
        ORDER BY n.pub_date DESC";

$stmt = $conn->prepare($sql);
$stmt->bind_param("s", $theme);
$stmt->execute();
$result = $stmt->get_result();

$news_list = [];
if ($result->num_rows > 0) {
    while($row = $result->fetch_assoc()) {
        $news_list[] = $row;
    }
}
$stmt->close();
$conn->close();
?>

<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?php echo htmlspecialchars($theme); ?> - 테마 뉴스 목록</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background-color: #f8f9fa;
            color: #212529;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
        }
        h1 {
            color: #007bff;
            border-bottom: 2px solid #007bff;
            padding-bottom: 10px;
            margin-bottom: 30px;
        }
        .news-table {
            width: 100%;
            border-collapse: collapse;
            background-color: #fff;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        .news-table th, .news-table td {
            padding: 12px 15px;
            border-bottom: 1px solid #dee2e6;
            text-align: left;
        }
        .news-table th {
            background-color: #e9ecef;
            font-weight: 600;
        }
        .news-table tr:hover {
            background-color: #f1f3f5;
        }
        .news-table a {
            color: #0056b3;
            text-decoration: none;
            font-weight: 500;
        }
        .news-table a:hover {
            text-decoration: underline;
        }
        .description {
            font-size: 0.9em;
            color: #6c757d;
        }
        .back-link {
            display: inline-block;
            margin-top: 30px;
            padding: 10px 15px;
            background-color: #007bff;
            color: #fff;
            text-decoration: none;
            border-radius: 5px;
            transition: background-color 0.2s;
        }
        .back-link:hover {
            background-color: #0056b3;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1><?php echo htmlspecialchars($theme); ?> 관련 뉴스</h1>
        
        <?php if (!empty($news_list)): ?>
            <table class="news-table">
                <thead>
                    <tr>
                        <th style="width: 15%;">종목명</th>
                        <th style="width: 55%;">뉴스 제목</th>
                        <th style="width: 15%;">게시일</th>
                    </tr>
                </thead>
                <tbody>
                    <?php foreach ($news_list as $news): ?>
                        <tr>
                            <td><?php echo htmlspecialchars($news['stock_name']); ?></td>
                            <td>
                                <a href="<?php echo htmlspecialchars($news['link']); ?>" target="_blank" title="<?php echo htmlspecialchars($news['description']); ?>">
                                    <?php echo htmlspecialchars($news['title']); ?>
                                </a>
                                <p class="description"><?php echo htmlspecialchars($news['description']); ?></p>
                            </td>
                            <td><?php echo date("Y-m-d", strtotime($news['pub_date'])); ?></td>
                        </tr>
                    <?php endforeach; ?>
                </tbody>
            </table>
        <?php else: ?>
            <p>해당 테마에 대한 뉴스가 없습니다.</p>
        <?php endif; ?>

        <a href="themed_news.php" class="back-link">테마 목록으로 돌아가기</a>
    </div>
</body>
</html>
